import socket
import json
from typing import Dict, Any
import threading
import os
import time
from config import CONTROLLER_IP, CONTROLLER_PORT, STATUS_UPDATE_INTERVAL, DRONE_ID, DRONE_IP

PEERS_FILE = "peers.json"  # File to store all known drone IPs and ports

# --- Registration Function ---
def register_with_controller():
    # Use the DRONE_IP from config.py
    registration = {"id": DRONE_ID, "ip": DRONE_IP}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((CONTROLLER_IP, CONTROLLER_PORT))
        s.sendall(json.dumps(registration).encode())
        s.close()
        print(f"Registered with controller: {registration}")
    except Exception as e:
        print(f"Failed to register with controller: {e}")

# --- Drone Status Function (simulate GPS, Baro, etc.) ---
def get_status():
    # Replace with real sensor readings in actual drone
    return {
        "id": DRONE_ID,
        "gps": {"lat": 12.34 + DRONE_ID, "lon": 56.78 + DRONE_ID},
        "baro": 1000 + DRONE_ID,
        "velocity": [DRONE_ID, DRONE_ID, DRONE_ID],
        "heartbeat": time.time()
    }

# --- Continuous Info Sharing Function ---
def share_info_continuously():
    while True:
        # Load latest peers.json each time (it may change)
        if os.path.exists(PEERS_FILE):
            with open(PEERS_FILE, "r") as f:
                try:
                    peers = json.load(f)
                except Exception:
                    peers = []
        else:
            peers = []
        status = get_status()
        for peer in peers:
            if peer.get("id") == DRONE_ID:
                continue  # Don't send to self
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect((peer["ip"], peer.get("port", 5000)))
                s.sendall(json.dumps(status).encode())
                s.close()
            except Exception as e:
                print(f"Failed to send status to {peer.get('ip', 'unknown')}: {e}")
        # Also send to controller
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((CONTROLLER_IP, CONTROLLER_PORT))
            s.sendall(json.dumps(status).encode())
            s.close()
        except Exception as e:
            print(f"Failed to send status to controller: {e}")
        time.sleep(STATUS_UPDATE_INTERVAL)

# --- Receiver Function ---
def start_receiver():
    RECEIVER_IP = "0.0.0.0"
    RECEIVER_PORT = 5000
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((RECEIVER_IP, RECEIVER_PORT))
    server.listen()
    print(f"Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}...")
    try:
        while True:
            conn, addr = server.accept()
            data = conn.recv(4096)
            if data:
                try:
                    msg = json.loads(data.decode())
                    # If we receive a list, it's a new peers list, save it
                    if isinstance(msg, list):
                        print(f"Received full peers list update: {msg}")
                        with open(PEERS_FILE, "w") as f:
                            json.dump(msg, f, indent=2)
                    elif isinstance(msg, dict) and "command" in msg and msg["command"] == "delete_peers_file":
                        print("Received delete_peers_file command. Deleting peers.json...")
                        try:
                            os.remove(PEERS_FILE)
                            print("peers.json deleted.")
                        except Exception as e:
                            print(f"Failed to delete peers.json: {e}")
                    elif isinstance(msg, dict) and "gps" in msg:
                        print(f"Received status from drone {msg.get('id', 'unknown')}: {msg}")
                    else:
                        print(f"Received: {msg}")
                except Exception as e:
                    print(f"Invalid data received: {e}")
            conn.close()
    except KeyboardInterrupt:
        print("\nReceiver shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    # Register with controller at startup
    register_with_controller()
    # Start receiver in a separate thread
    threading.Thread(target=start_receiver, daemon=True).start()
    # Start continuous info sharing
    share_info_continuously()