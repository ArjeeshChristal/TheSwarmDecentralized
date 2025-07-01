import socket
import json

# Configuration
DRONE_ID = 1  # <-- Changed for second drone
DRONE_IP = "100.85.57.105"  # Set this to the drone's local IP or use socket.gethostbyname(socket.gethostname())
CONTROLLER_IP = "100.94.138.35"
CONTROLLER_PORT = 6000  # Use a different port for this signal if needed

from typing import Dict, Any

# Prepare the signal data
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
