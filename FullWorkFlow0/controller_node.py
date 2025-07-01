import socket
import threading
import json
import traceback
from typing import Tuple

HOST = '0.0.0.0'  # Listen on all interfaces (use Tailscale IP if needed)
PORT = 5000       # Must match DRONE's CONTROLLER_PORT

def handle_drone(conn: socket.socket, addr: Tuple[str, int]):
    print(f"🔗 Drone connected from {addr}")
    buf = b""
    def send_start_mission():
        try:
            total_drones = int(input("Enter total number of drones for mission and press Enter to start mission: "))
        except ValueError:
            print("Invalid input. Defaulting to 1 drone.")
            total_drones = 1
        cmd = json.dumps({"command": "start mission", "total_drones": total_drones}) + "\n"
        try:
            conn.sendall(cmd.encode())
            print(f"🚀 Sent start mission command: {cmd.strip()}")
        except Exception as e:
            print(f"❌ Failed to send start mission command: {e}")

    def gps_printer():
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break  # Properly handle client disconnect
                nonlocal buf
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode())
                        if 'lat' in msg:
                            print(f"📍 GPS: {msg}")
                        elif 'id' in msg and 'port' in msg:
                            print(f"✅ Registered: {msg}")
                        elif 'command' in msg:
                            print(f"📨 Command received: {msg}")
                        else:
                            print(f"📦 Unrecognized: {msg}")
                    except json.JSONDecodeError:
                        print(f"❌ Invalid JSON: {line}")
            except Exception as e:
                print(f"⚠️ Drone connection error from {addr}: {e}")
                traceback.print_exc()
                break
        conn.close()
        print(f"❌ Disconnected: {addr}")

    # Start GPS printer in a thread
    threading.Thread(target=gps_printer, daemon=True).start()
    # Wait for user to press enter to send start mission
    send_start_mission()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"🛰️ Controller listening on {HOST}:{PORT}...")
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=handle_drone,
                args=(conn, addr),
                daemon=True,
                name=f"DroneHandler-{addr}"
            ).start()
    except KeyboardInterrupt:
        print("\n🛑 Controller shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    main()