import socket
import json

RECEIVER_IP = "0.0.0.0"  # Listen on all interfaces
RECEIVER_PORT = 6000     # Must match the port used by the drone signal sender

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((RECEIVER_IP, RECEIVER_PORT))
server.listen()
print(f"Receiver listening on {RECEIVER_IP}:{RECEIVER_PORT}...")

try:
    while True:
        conn, addr = server.accept()
        data = conn.recv(1024)
        if data:
            try:
                msg = json.loads(data.decode())
                print(f"Received signal from drone: {msg}")
            except Exception as e:
                print(f"Invalid data received: {e}")
        conn.close()
except KeyboardInterrupt:
    print("\nReceiver shutting down...")
finally:
    server.close()
