import socket
import time

# Define the server's IP address and port
server_ip = '127.0.0.1'  # Use the server's IP address
server_port = 12345  # Use the same port as in the server

# Create a socket object
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to the server
client_socket.connect((server_ip, server_port))

while True:
    # Get the current time before sending the message
    start_time = time.time()

    # Send a "ping" message to the server
    message = 'ping'
    client_socket.send(message.encode('utf-8'))

    # Receive the response from the server
    response = client_socket.recv(1024).decode('utf-8')

    # Get the current time after receiving the response
    end_time = time.time()

    # Calculate the Round-Trip Time (RTT) in milliseconds
    rtt = (end_time - start_time) * 1000

    print(f'Server response: {response}, RTT: {rtt:.2f} ms')

    if response == 'pong':
        break  # Exit the loop

# Close the socket
client_socket.close()

