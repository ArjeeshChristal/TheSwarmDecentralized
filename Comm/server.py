import socket
import threading
import json
import time                # ← add this import

HOST = '0.0.0.0'
PORT = 12345

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)
print(f"Listening on {HOST}:{PORT}…")

conn, addr = server.accept()
conn.settimeout(10.0)      # detect broken connections
print(f"Connected: {addr}")

def receiver():
    buffer = b""
    while True:
        try:
            chunk = conn.recv(1024)
            if not chunk:
                print("⚠️ Drone disconnected")
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                try:
                    msg = json.loads(line.decode())
                    # differentiate commands vs GPS
                    if 'command' in msg:
                        print("📩 Command received:", msg)
                    elif {'id','lat','lon','alt'}.issubset(msg):
                        print(f"📍 Drone {msg['id']} @ "
                              f"lat={msg['lat']:.6f}, lon={msg['lon']:.6f}, alt={msg['alt']:.1f}")
                    else:
                        print("❓ Unknown message:", msg)
                except json.JSONDecodeError as e:
                    print("❌ JSON parse error:", e)
        except socket.timeout:
            continue
        except Exception as e:
            print("❌ Receiver error:", e)
            break

def printer():
    """Optional: if you really want to send heartbeats back."""
    while True:
        time.sleep(1)
        try:
            conn.sendall(b'PING\n')
        except Exception as e:
            print("❌ Send error:", e)
            break

# start threads
threading.Thread(target=receiver, daemon=True).start()
threading.Thread(target=printer, daemon=True).start()

# keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nShutting down…")

conn.close()
server.close()
