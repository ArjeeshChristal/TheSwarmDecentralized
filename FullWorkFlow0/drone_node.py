import socket, threading, logging, json
from drone_common import arm_and_takeoff, split_polygon_by_index, upload_and_execute
from dronekit import connect
from shapely.geometry import Polygon
from test_workflow import QuadplaneSurvey
from shared_config import ALTITUDE_M, KML_PATH

DRONE_ID = 0
PORT = 12345 + DRONE_ID
VEHICLE_CONN = f'udp:127.0.0.1:{14550 + DRONE_ID}'
CONTROLLER_IP = "100.94.138.35"
CONTROLLER_PORT = 5000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"Drone-{DRONE_ID}")

def listener(conn, vehicle):
    """Listen for mission start commands."""
    while True:
        data = conn.recv(1024)
        if not data:
            break
        try:
            msg = json.loads(data.decode())
            if msg.get("command") == "start mission":
                total = msg.get("total_drones", 1)
                logger.info(f"🚀 Mission trigger (drones: {total})")
                threading.Thread(target=start_mission, args=(vehicle, total), daemon=True).start()
        except Exception as e:
            logger.error(f"Invalid message: {e}")

def gps_sender(conn, vehicle):
    """Continuously send GPS coordinates."""
    while True:
        loc = vehicle.location.global_frame
        if loc.lat is not None:
            payload = json.dumps({
                "id": DRONE_ID,
                "lat": loc.lat,
                "lon": loc.lon,
                "alt": loc.alt
            })
            try:
                conn.sendall((payload + "\n").encode())
            except Exception as e:
                logger.error(f"👎 Failed to send GPS: {e}")
                break
        time.sleep(1)

def start_mission(vehicle, total_drones):
    """Arm, take off, split area, execute survey."""
    arm_and_takeoff(vehicle, ALTITUDE_M)
    survey = QuadplaneSurvey()
    survey.KML_PATH = KML_PATH
    poly = survey.read_polygon()
    sub = split_polygon_by_index(poly, total_drones, DRONE_ID).geoms[0]
    wps, _ = survey.generate_lawnmower(sub)
    upload_and_execute(vehicle, wps)
    logger.info("🚁 Mission complete.")

def main():
    vehicle = connect(VEHICLE_CONN, wait_ready=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((CONTROLLER_IP, CONTROLLER_PORT))
    s.sendall(json.dumps({"id": DRONE_ID, "port": PORT}).encode())
    logger.info("✅ Registered with controller")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(1)
    logger.info(f"Listening on port {PORT}...")

    conn, addr = server.accept()
    logger.info(f"Connected controller: {addr}")

    threading.Thread(target=listener, args=(conn, vehicle), daemon=True).start()
    threading.Thread(target=gps_sender, args=(conn, vehicle), daemon=True).start()

    # Keep the main thread alive
    while True:
        time.sleep(10)

if __name__ == '__main__':
    main()

