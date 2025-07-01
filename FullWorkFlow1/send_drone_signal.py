import socket
import json
from typing import Dict, Any
import threading
import os

# Configuration
DRONE_ID = 1  # <-- Changed for second drone
DRONE_IP = "100.85.57.105"  # Set this to the drone's local IP or use socket.gethostbyname(socket.gethostname())
CONTROLLER_IP = "100.94.138.35"
CONTROLLER_PORT = 6000  # Use a different port for this signal if needed
PEERS_FILE = "peers.json"  # File to store all known drone IPs and ports

# --- Sender Function ---
def send_signal():
    signal: Dict[str, Any] = {
        "id": DRONE_ID,
        "ip": DRONE_IP
    }
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((CONTROLLER_IP, CONTROLLER_PORT))
        s.sendall(json.dumps(signal).encode())
        print(f"Signal sent: {signal}")
        s.close()
    except Exception as e:
        print(f"Failed to send signal: {e}")

# --- Receiver Function ---
def start_receiver():
    RECEIVER_IP = "0.0.0.0"  # Listen on all interfaces
    RECEIVER_PORT = 5000     # Must match the port used by the sender
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((RECEIVER_IP, RECEIVER_PORT))
    server.listen()
    print(f"Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}...")
    # Load existing peers if available
    peers: list[dict[str, Any]] = []
    if os.path.exists(PEERS_FILE):
        with open(PEERS_FILE, "r") as f:
            try:
                peers = json.load(f)
            except Exception:
                peers = []
    try:
        while True:
            conn, addr = server.accept() # type: ignore
            data = conn.recv(4096)
            if data:
                try:
                    msg = json.loads(data.decode())
                    # If we receive a list, treat it as a full peers.json update
                    if isinstance(msg, list):
                        print(f"Received full peers list update: {msg}")
                        peers = list(msg)  # type: ignore
                        with open(PEERS_FILE, "w") as f:
                            json.dump(peers, f, indent=2)
                    else:
                        print(f"Received signal from drone: {msg}")
                        # Add to peers if not already present
                        if not any(p["id"] == msg["id"] and p["ip"] == msg["ip"] for p in peers):
                            peers.append(msg)
                            with open(PEERS_FILE, "w") as f:
                                json.dump(peers, f, indent=2)
                        response: Dict[str, Any] = {"status": "received", "drone_id": msg.get("id")}
                        conn.sendall(json.dumps(response).encode())
                except Exception as e:
                    print(f"Invalid data received: {e}")
            conn.close()
    except KeyboardInterrupt:
        print("\nReceiver shutting down...")
    finally:
        server.close()

if __name__ == "__main__":
    # Start receiver in a separate thread
    threading.Thread(target=start_receiver, daemon=True).start()
    # Send signal as a client
    send_signal()
    # Keep the main thread alive to allow receiver to run
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nProgram exiting...")