import socket
import threading
import time
import sys
import os
import json
import hashlib


class Peer:

    # Class variables shared among all instances of Peer
    tracker_host = 'localhost'
    tracker_port = 5000
    script_dir = os.path.dirname(__file__)

    def __init__(self, host, port):
        # Initialize Peer instance with host, port, and sockets
        self.host = host
        self.port = port
        self.listening_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)

        # File paths for data files
        self.csv_file_path = os.path.join(os.path.dirname(
            Peer.script_dir), 'data', 'wr_sensor_data.csv')
        self.img_file_path = os.path.join(os.path.dirname(
            Peer.script_dir), 'data', 'network.png')
        self.json_file_path = os.path.join(os.path.dirname(
            Peer.script_dir), 'data', 'data.json')

        # Set to store peers and lock for thread safety
        self.peers = set()
        self.lock = threading.Lock()
        self.is_active = True
        self.initial_connection = True

    def register_with_tracker(self):
        # Register with the tracker to announce the presence of the peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect((Peer.tracker_host, Peer.tracker_port))
            tracker_socket.sendall(
                f"REGISTER {self.host}:{self.port}".encode('utf-8'))
            response = tracker_socket.recv(1024)
            print(
                f"Registered with tracker. Response: {response.decode('utf-8')}")

            if response.decode('utf-8') == 'OK':
                self.update_peers_list()

    def unregister_from_tracker(self):
        # Unregister from the tracker when the peer is shutting down
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect((Peer.tracker_host, Peer.tracker_port))
            tracker_socket.sendall(
                f"UNREGISTER {self.host}:{self.port}".encode('utf-8'))
            response = tracker_socket.recv(1024)
            print(
                f"Unregistered from tracker. Response: {response.decode('utf-8')}")

    def update_peers_list(self):
        # Retrieve the list of peers from the tracker
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_socket:
            tracker_socket.connect((Peer.tracker_host, Peer.tracker_port))
            tracker_socket.sendall(b"GETPEERS")
            response = tracker_socket.recv(1024)
            peers = response.decode('utf-8').split(',')

            with self.lock:
                self.peers.clear()
                for peer in peers:
                    if peer:
                        host_port = tuple(peer.split(':'))
                        if len(host_port) == 2:
                            self.peers.add(host_port)

    def start_listening(self):
        # Start listening for incoming connections
        try:
            self.listening_socket.bind((self.host, self.port))
            self.listening_socket.listen()
            print(
                f"Peer {self.host}:{self.port} is now listening for connections.")
            while self.is_active:
                peer_socket, addr = self.listening_socket.accept()
                if self.initial_connection and addr[0] == Peer.tracker_host:
                    print(f"Initial connection from Tracker {addr}")
                    self.initial_connection = False

                peer_socket.settimeout(10)
                threading.Thread(target=self.handle_peer,
                                 args=(peer_socket,)).start()
        except Exception as e:
            print(f"Failed to listen on {self.host}:{self.port}: {e}")
            sys.exit(1)
        finally:
            self.listening_socket.close()

    def handle_peer(self, peer_socket):
        # Handle communication with a connected peer
        with peer_socket:
            while True:
                try:
                    data = peer_socket.recv(1024)

                    if data:
                        message = data.decode('utf-8')

                        if message == "PING":
                            peer_socket.sendall(b"PONG")
                        elif message.startswith("SEND_FILE"):
                            self.receive_file(peer_socket)
                        else:
                            message = data.decode('utf-8')
                            print(
                                f"Received from {peer_socket.getpeername()}: '{message}'")
                    else:
                        break
                except socket.timeout:
                    print(
                        f"Connection to {peer_socket.getpeername()} timed out.")
                    break

    def send_broadcast_message(self, message):
        # Send a broadcast message to all connected peers
        complete_message = f"Broadcast message: '{message}' from {self.host}:{self.port}"
        with self.lock:
            peers_to_notify = set(
                peer for peer in self.peers if peer != (self.host, str(self.port)))
            for host, port in peers_to_notify:
                try:
                    with socket.socket(socket.AF_INET,
                                       socket.SOCK_STREAM) as peer_socket:
                        peer_socket.settimeout(5)
                        peer_socket.connect((host, int(port)))
                        peer_socket.sendall(complete_message.encode('utf-8'))
                        print(f"Message sent to peer {host}:{port}")
                except Exception as e:
                    print(
                        f"Failed to send message to peer {host}:{port} due to: {e}")

    def recv_ack(self, peer_socket, timeout=10, retry=3):
       # Receive acknowledgment from the peer_socket, retrying up to 'retry' times
        for attempt in range(retry):
            try:
                peer_socket.settimeout(timeout)
                ack = peer_socket.recv(1024).strip()
                if ack == b"ACK":
                    return True
                else:
                    raise ValueError(f"Received incorrect ACK: {ack}")
            except socket.timeout as e:
                if attempt < retry - 1:
                    print(f"ACK not received. Retrying {attempt + 1}/{retry}")
                else:
                    raise TimeoutError(
                        f"ACK not received after {retry} retries")
            except Exception as e:
                raise e
        return False

    def send_file(self, peer_socket, file_path):
        # ensure the socket is valid and open
        if not peer_socket or peer_socket.fileno() == -1:
            print("Can't send file, the socket is closed or invalid.")
            return

        try:
            # Open the file to be sent in binary read mode
            with open(file_path, 'rb') as file_to_send:
                # Get the file's name and size to send to the peer
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)

                # Calculate checksum for file integrity verification
                # Ensure reading the file from the beginning
                file_to_send.seek(0)
                file_checksum = hashlib.sha256(file_to_send.read()).hexdigest()

                # Gather the file metadata
                file_info = {'name': file_name,
                             'size': file_size, 'checksum': file_checksum}
                # Reset file pointer after checksum calculation
                file_to_send.seek(0)
                # Send the file metadata to the peer
                peer_socket.sendall(json.dumps(file_info).encode('utf-8'))

                # Wait for an acknowledgment from the peer before sending the file data
                if not self.recv_ack(peer_socket):
                    raise Exception("Did not receive ACK for file info")

                # Send the file data in chunks of 4096 bytes
                l = file_to_send.read(4096)
                while l:
                    peer_socket.sendall(l)  # Send a chunk of the file
                    l = file_to_send.read(4096)  # Read the next chunk

                # Wait for final acknowledgment from the peer after file data transfer
                if not self.recv_ack(peer_socket):
                    raise Exception(
                        "Did not receive final ACK after file send")

                print(f"File {file_name} sent successfully.")
        except Exception as e:
            print(f"Failed to send file {file_path}: {e}")

    def receive_file(self, peer_socket):
     # Receive a file from the connected peer_socket
        try:
            # First, receive the file info as a JSON object and send an ACK to confirm receipt.
            file_info = json.loads(peer_socket.recv(4096).decode('utf-8'))
            peer_socket.sendall(b"ACK")

            # Extract the necessary file metadata.
            file_name = file_info['name']
            file_size = file_info['size']
            expected_checksum = file_info['checksum']

            # Prepare the directory for storing the received files.
            upper_dir = os.path.dirname(self.script_dir)
            new_file_dir = os.path.join(upper_dir, 'received_files')
            os.makedirs(new_file_dir, exist_ok=True)
            file_path = os.path.join(new_file_dir, file_name)

            # If the file already exists, create a new file path to avoid overwriting.
            if os.path.exists(file_path):
                base, extension = os.path.splitext(file_path)
                i = 1
                while os.path.exists(f"{base}_{i}{extension}"):
                    i += 1
                file_path = f"{base}_{i}{extension}"

            # Receive the file in chunks and write it to the file system.
            with open(file_path, 'wb') as file_to_receive:
                received_size = 0
                while received_size < file_size:
                    chunk = peer_socket.recv(4096)
                    if not chunk:
                        break
                    file_to_receive.write(chunk)
                    received_size += len(chunk)

            # After receiving the file, calculate and verify the validity of the file using checksum.
            with open(file_path, 'rb') as file_to_verify:
                file_checksum = hashlib.sha256(
                    file_to_verify.read()).hexdigest()

            # If checksums don't match, delete the corrupted file.
            if expected_checksum != file_checksum:
                os.remove(file_path)
                raise ValueError("Checksum mismatch. File may be corrupted.")

            # Send final ACK
            peer_socket.sendall(b"ACK")
            print(f"File {file_name} received successfully.")
        except Exception as e:
            print(f"Error receiving file: {e}")

    def send_ping(self, target_peer, timeout=5):
        # Send a ping message to a specified peer
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
            try:
                peer_socket.settimeout(timeout)
                peer_socket.connect(target_peer)
                peer_socket.sendall(b"PING")
                response = peer_socket.recv(1024)

                if response == b"PONG":
                    print(f"{target_peer}: 'PONG'")
                else:
                    print(
                        f"Unexpected response from {target_peer}: {response}")
            except socket.timeout:
                print(f"Ping to {target_peer} timed out.")
            except Exception as e:
                print(f"Failed to send ping to peer {target_peer}: {e}")

    def handle_user_input(self):
        # Handle user input for commands (ping, broadcast, sendfile, exit)
        # As long as the peer is active, it will keep listening for user commands.
        while self.is_active:
            message = input(
                "Enter command (ping, broadcast <message>, sendfile <filename>, exit): ")

            # Handle the 'exit' command, which stops the peer's operations by setting the active flag to False, unregistering from the tracker, and terminating the peer's process.
            if message == 'exit':
                self.is_active = False
                self.unregister_from_tracker()
                print("Shutting down the peer.")
                self.stop()
            # If the command is 'ping', request details of the target peer and send a ping message to that peer.
            elif message.lower() == 'ping':
                target_host = input("Enter target host: ")
                target_port = input("Enter target port: ")
                target_peer = (target_host, int(target_port))
                self.send_ping(target_peer)
            # If the command starts with 'broadcast', split to get the message part, then send this message to all connected peers.
            elif message.startswith('broadcast'):
                if message and len(message.split()) > 1:
                    _, message = message.split(" ", 1)
                    print(f"Broadcasting message to all peers: {message}")
                    self.send_broadcast_message(message)
                # If the broadcast command does not include a message, prompt the user to enter one.
                else:
                    print("Please specify a message to broadcast.")
            # If the command is 'sendfile', identify the file and send it to all connected peers.
            elif message.startswith('sendfile'):
                if message and len(message.split()) > 1:
                    _, filename = message.split(" ", 1)

                    # Match the input filename to one of the files associated with the class, and set the file path.
                    if filename == 'wr_sensor_data.csv':
                        filepath = self.csv_file_path
                    elif filename == 'network.png':
                        filepath = self.img_file_path
                    elif filename == 'data.json':
                        filepath = self.json_file_path
                    else:
                        # If the input filename does not match any of the known files, notify the user.
                        print("File not found.")
                        continue

                    # Access the peer list, omitting own address and sending the file to every other peer.
                    with self.lock:
                        peers_to_notify = set(
                            peer for peer in self.peers if peer != (self.host, str(self.port)))
                        for host, port in peers_to_notify:
                            if peer != (self.host, str(self.port)):

                                try:
                                    port = int(port)
                                    peer_addr = (host, port)

                                    # Establish a connection to the peer and send the file.
                                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer_socket:
                                        peer_socket.connect(peer_addr)
                                        peer_socket.sendall(
                                            b'SEND_FILE ' + filename.encode('utf-8'))
                                        self.send_file(peer_socket, filepath)
                                        print(
                                            f"Sent {filename} to {peer_addr}.")
                                except Exception as e:
                                    print(
                                        f"Failed to send file to peer {peer_addr}: {e}")
                else:
                    # If the sendfile command does not include a filename, prompt the user to enter one.
                    print("Please specify a filename to send.")
            else:
                print(f"Unknown command: {message}")

    def start(self):
        # Start listening thread, register with tracker, and handle user input
        listener_thread = threading.Thread(target=self.start_listening)
        listener_thread.start()

        time.sleep(1)
        self.register_with_tracker()

        input_listener_thread = threading.Thread(target=self.handle_user_input)
        input_listener_thread.start()
        print(
            f"Peer started on {self.host}:{self.port}. Waiting for commands...")

        try:
            while self.is_active:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Shutting down due to KeyboardInterrupt.")
        finally:
            self.stop()
            listener_thread.join()
            input_listener_thread.join()

    def stop(self):
        # Stop the peer and exit
        self.is_active = False
        sys.exit(0)


if __name__ == "__main__":
    # Get user input for peer host and port
    host = 'localhost'  # input("Enter peer host: ")
    port = int(input("Enter peer port: "))

    try:
        # Create and start the Peer instance
        peer = Peer(host, port)
        peer.start()
    # Exceptions that can occur trying to start & connect the Client
    except ConnectionResetError:
        print("Connection to the tracker was closed.")
    except ConnectionRefusedError:
        print("Connection to the tracker failed. Retrying in 5 seconds...")
        time.sleep(5)
    except KeyboardInterrupt:
        print("Peer start interrupted by user.")
    except Exception as e:
        print(e)
