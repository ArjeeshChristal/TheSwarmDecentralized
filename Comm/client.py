import socket
import threading

# Drone connection details
drones = [
    ("100.85.57.104", 12345),  # Drone 1
    ("100.85.57.104", 22222),  # Drone 2
]

message = "start mission"

def send_to_drone(host, port, msg):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.sendall(msg.encode())
        print(f"✅ Sent to {host}:{port}")
        sock.close()
    except Exception as e:
        print(f"❌ Error sending to {host}:{port} — {e}")

# Create and start threads
threads = []
for host, port in drones:
    thread = threading.Thread(target=send_to_drone, args=(host, port, message))
    thread.start()
    threads.append(thread)

# Wait for all threads to finish
for thread in threads:
    thread.join()

print("📡 Mission start signal sent to all drones.")

