import socket
import threading
import json

REG_PORT = 5000  # Registration port
registered_drones = {}

def handle_registration(conn, addr):
    try:
        data = conn.recv(1024).decode()
        reg = json.loads(data)
        drone_id = reg["id"]
        port = reg["port"]
        registered_drones[drone_id] = (addr[0], port)
        print(f"✅ Drone {drone_id} registered from {addr[0]}:{port}")
    except Exception as e:
        print(f"❌ Registration failed from {addr}: {e}")
    finally:
        conn.close()

def registration_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", REG_PORT))
    sock.listen(5)
    print(f"📡 Controller listening for drone registrations on port {REG_PORT}")

    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_registration, args=(conn, addr)).start()

def send_mission_start():
    message = "start mission"
    threads = []
    for drone_id, (host, port) in registered_drones.items():
        def send(host, port):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((host, port))
                s.sendall(message.encode())
                s.close()
                print(f"🚀 Sent to Drone {drone_id} at {host}:{port}")
            except Exception as e:
                print(f"❌ Failed to send to Drone {drone_id}: {e}")
        t = threading.Thread(target=send, args=(host, port))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    print("✅ Mission start command sent to all registered drones.")

if __name__ == "__main__":
    threading.Thread(target=registration_server, daemon=True).start()
    input("Press Enter to launch mission to all registered drones...\n")
    send_mission_start()

