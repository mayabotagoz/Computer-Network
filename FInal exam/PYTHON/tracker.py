import socket
import threading
import sys
import time

class Tracker:

    def __init__(self, host, port):
        # Initialize Tracker instance with host, port, peers set, and a lock for thread safety
        self.host = host
        self.port = port
        self.peers = set()
        self.lock = threading.Lock()

    def start(self):
        # Start the tracker by creating a listening socket
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((self.host, self.port))
        self.tracker_socket.listen(5)

        # Start a background thread for periodic peer cleanup
        threading.Thread(target=self.cleanup_peers, daemon=True).start()

        print(f"Tracker is listening on {self.host}:{self.port}")

        # Accept incoming connections and handle them in separate threads
        while True:
            peer, addr = self.tracker_socket.accept()
            threading.Thread(target=self.handle_peer_registration,
                             args=(peer,)).start()

    def cleanup_peers(self):
        # Periodically check and remove unresponsive peers
        while True:
            time.sleep(20)
            with self.lock:
                for peer in list(self.peers):
                    host, port = peer.split(':')
                    try:
                        # Attempt to connect to the peer and check responsiveness
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.settimeout(10)
                            sock.connect((host, int(port)))
                            sock.sendall(b'PING')
                            if sock.recv(1024) != b'PONG':
                                raise Exception(
                                    "Peer unresponsive during cleanup check")
                    except:
                        # Remove unresponsive peer and notify others
                        self.peers.remove(peer)
                        print(f"Removed unresponsive peer: {peer}")
                        self.broadcast_to_peers(f"\nPeer left: {peer}")

    def broadcast_to_peers(self, message):
        # Broadcast a message to all connected peers
        with self.lock:
            for peer in list(self.peers):
                try:
                    host, port = peer.split(':')

                    # Connect to each peer and send the broadcast message
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.connect((host, int(port)))
                        sock.sendall(message.encode('utf-8'))
                except Exception as e:
                    print(f"Error sending to {peer}: {e}")

    def handle_peer_registration(self, peer_socket):
        # Handle communication with a connected peer
        with peer_socket:
            try:
                while True:
                    data = peer_socket.recv(1024)

                    if data:
                        message = data.decode('utf-8')

                        if message.startswith('REGISTER'):
                            # Process peer registration
                            peer_info = message.split()[1]
                            with self.lock:
                                self.peers.add(peer_info)
                            print(f"New peer connected: {peer_info}")
                            self.broadcast_to_peers(
                                f"\nNew peer joined: {peer_info}")
                            peer_socket.sendall(b"OK")
                        elif message.startswith('UNREGISTER'):
                            # Process peer unregistration
                            peer_info = message.split()[1]
                            if peer_info in self.peers:
                                with self.lock:
                                    self.peers.remove(peer_info)
                            print(f"Peer disconnected: {peer_info}")
                            self.broadcast_to_peers(
                                f"\nPeer left: {peer_info}")
                            peer_socket.sendall(b"OK")
                        elif message == 'GETPEERS':
                            # Respond to a request for the list of peers
                            with self.lock:
                                peers_list = ','.join(self.peers)
                            peer_socket.sendall(peers_list.encode('utf-8'))
                    else:
                        break
            except ConnectionAbortedError as e:
                print(f"Connection aborted: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    host = 'localhost'
    port = 5000

    try:
        tracker = Tracker(host, port)
        tracker.start()
    except Exception as e:
        print(f"Failed to start the tracker on {host}:{port}: {e}")
        sys.exit(1)


