import socket

# Use Tailscale IP of the server
HOST = '100.85.57.104'  # Replace this with your server's Tailscale IP
PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

message = "Hello from client over Tailscale!"
client_socket.sendall(message.encode())

print("Sent:", message)
client_socket.close()
