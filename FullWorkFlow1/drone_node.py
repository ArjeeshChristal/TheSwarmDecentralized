import socket
import threading
import logging
from drone_common import arm_and_takeoff, split_polygon_by_index, upload_and_execute
from dronekit import connect
from test_workflow import QuadplaneSurvey
from shapely.geometry import Polygon
from shared_config import ALTITUDE_M, KML_PATH
import time
import json


# Settings for this drone
DRONE_ID = 1           # Change this for each drone (e.g., 0, 1, 2...)
TOTAL_DRONES = 2       # Optional if controller sends it
PORT = 12345 + DRONE_ID
VEHICLE_CONN = f'udp:127.0.0.1:{14550 + DRONE_ID}'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"Drone-{DRONE_ID}")

def register_with_controller():
    REG_CONTROLLER_IP = "100.94.138.35"  # Controller Tailscale IP
    REG_CONTROLLER_PORT = 5000
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((REG_CONTROLLER_IP, REG_CONTROLLER_PORT))
        data = json.dumps({
            "id": DRONE_ID,
            "port": PORT
        })
        sock.sendall(data.encode())
        sock.close()
        print(f"[Drone {DRONE_ID}] ✅ Registered with controller.")
    except Exception as e:
        print(f"[Drone {DRONE_ID}] ❌ Failed to register: {e}")


def start_mission(total_drones):
    vehicle = connect(VEHICLE_CONN, wait_ready=True)
    arm_and_takeoff(vehicle, ALTITUDE_M)

    survey = QuadplaneSurvey()
    survey.KML_PATH = KML_PATH
    poly = survey.read_polygon()
    parts = split_polygon_by_index(poly, total_drones, DRONE_ID)

    sub_poly = None
    for p in parts.geoms:
        if isinstance(p, Polygon):
            sub_poly = p
            break

    wps, _ = survey.generate_lawnmower(sub_poly)
    upload_and_execute(vehicle, wps)

    vehicle.close()
    logger.info("🚁 Mission complete.")


def listener():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # ✅ Add this line
    server_socket.bind(('0.0.0.0', PORT))
    server_socket.listen(1)
    print(f"[Drone {DRONE_ID}] Listening on port {PORT}...")

    while True:
        conn, addr = server_socket.accept()
        data = conn.recv(1024).decode().strip()
        conn.close()

        try:
            msg = json.loads(data)
            if msg.get("command") == "start mission":
                total_drones = msg.get("total_drones", 1)
                print(f"[Drone {DRONE_ID}] 🚀 Mission trigger received (Total drones: {total_drones})")

                # Launch with dynamic count
                threading.Thread(target=start_mission, args=(total_drones,)).start()
        except Exception as e:
            print(f"[Drone {DRONE_ID}] ❌ Invalid message received: {e}")


if __name__ == '__main__':
    register_with_controller()
    listener()


