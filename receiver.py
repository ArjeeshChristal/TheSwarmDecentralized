import socket
import json
import threading
import os
from typing import Any

RECEIVER_IP = "0.0.0.0"  # Listen on all interfaces
RECEIVER_PORT = 6000     # Must match the port used by the drone signal sender
PEERS_FILE = "peers.json"  # File to store all known drone IPs and ports


# Store latest status for each drone
peers: list[dict[str, Any]] = []
drone_status = {}  # {drone_id: status_dict}
if os.path.exists(PEERS_FILE):
    with open(PEERS_FILE, "r") as f:
        try:
            peers = json.load(f)
        except Exception:
            peers = []

def save_drone_status():
    with open("drone_status.json", "w") as f:
        json.dump(drone_status, f, indent=2)

def save_peers():
    with open(PEERS_FILE, "w") as f:
        json.dump(peers, f, indent=2)

def broadcast_to_peers():
    # Send both peers list and all drone statuses to each drone
    for peer in peers:
        try:
            print(f"Sending peers and status to {peer['ip']}...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer["ip"], 5000))  # 5000 is the receiver port on the drone
            # Send a dict with both peer list and all drone statuses
            payload = {
                "peers": peers,
                "drones": drone_status
            }
            s.sendall(json.dumps(payload).encode())
            s.close()
        except Exception as e:
            print(f"Failed to send peers/status to {peer['ip']}: {e}")

def handle_connection(conn: socket.socket, addr: tuple[str, int]):
    data = conn.recv(4096)
    if data:
        try:
            msg = json.loads(data.decode())
            print(f"Received signal from drone: {msg}")
            # Registration message
            if isinstance(msg, dict) and "ip" in msg:
                if not any(p["id"] == msg["id"] and p["ip"] == msg["ip"] for p in peers):
                    peers.append(msg)
                    save_peers()
                    print(f"Broadcasting peers list: {peers}")
                    # Immediately broadcast updated peers list to all drones
                    for peer in peers:
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(2)
                            s.connect((peer["ip"], 5000))
                            s.sendall(json.dumps(peers).encode())
                            s.close()
                        except Exception as e:
                            print(f"Failed to send updated peers to {peer['ip']}: {e}")
            # Status message (must have id, gps, baro, velocity, heartbeat)
            if isinstance(msg, dict) and "gps" in msg and "id" in msg:
                drone_id = str(msg["id"])
                drone_status[drone_id] = msg
                save_drone_status()
            # Always broadcast latest status to all peers after any update
            broadcast_to_peers()
        except Exception as e:
            print(f"Invalid data received: {e}")
    conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((RECEIVER_IP, RECEIVER_PORT))
    server.listen()
    print(f"Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}...")
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nReceiver shutting down...")
        # On shutdown, send a message to all peers to delete their peers.json
        for peer in peers:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect((peer["ip"], 5000))
                # Send a special command to delete the peers.json file
                s.sendall(json.dumps({"command": "delete_peers_file"}).encode())
                s.close()
                print(f"Sent delete_peers_file command to {peer['ip']}")
            except Exception as e:
                print(f"Failed to send delete command to {peer['ip']}: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
