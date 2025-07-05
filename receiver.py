import socket
import json
import threading
import os
from typing import Any

RECEIVER_IP = "0.0.0.0"  # Listen on all interfaces
RECEIVER_PORT = 6000     # Must match the port used by the drone signal sender
PEERS_FILE = "peers.json"  # File to store all known drone IPs and ports

peers: list[dict[str, Any]] = []
if os.path.exists(PEERS_FILE):
    with open(PEERS_FILE, "r") as f:
        try:
            peers = json.load(f)
        except Exception:
            peers = []

def save_peers():
    with open(PEERS_FILE, "w") as f:
        json.dump(peers, f, indent=2)

def broadcast_to_peers():
    for peer in peers:
        try:
            print(f"Sending peers list to {peer['ip']}...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((peer["ip"], 5000))  # 5000 is the receiver port on the drone
            s.sendall(json.dumps(peers).encode())
            s.close()
        except Exception as e:
            print(f"Failed to send peers to {peer['ip']}: {e}")

def handle_connection(conn: socket.socket, addr: tuple[str, int]):
    data = conn.recv(1024)
    if data:
        try:
            msg = json.loads(data.decode())
            print(f"Received signal from drone: {msg}")
            # Add to peers if not already present
            if not any(p["id"] == msg["id"] and p["ip"] == msg["ip"] for p in peers):
                peers.append(msg)
                save_peers()
                print(f"Broadcasting peers list: {peers}")
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
    finally:
        server.close()

if __name__ == "__main__":
    start_server()
