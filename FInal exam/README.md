# P2P File Sharing System

# Overview
Python 3 based P2P file system using TCP protocol
This project consists of two main components: a P2P Tracker('tracker.py') and a P2P peer ('peer.py'). The system enables peers to register with the tracker, exchange messages, and share files in a decentralized network.

# Table of Contents
1. [How to Run the P2P system](#How-to-Run-the-P2P-system)
2. [Usage](#Usage)
3. [Implementation Details](#Implementation-Details)

## How to Run the P2P system
1. Clone the repository:
```bash
https://github.com/Anni-065/p2p-system
```
2. Navigate to the project directory:
```bash
cd p2p-system
```
3. Naviagte to the src folder and Run the tracker.py script to start the tracker on a specified host and port (default is 'localhost:5000')
```bash
python tracker.py
```
2. Run the peer.py script to start a peer on a specified host and port. Follow the prompts to interact with the peer and the P2P network.
```bash
python peer.py
```

# Usage
The peer source code provides menu form with four options.
```bash
 Enter command (ping, broadcast <message>, sendfile <filename>, exit)
```
- Pinging other peers. Make sure to input the right IP address and the port number of the other peer.
- Broadcasting messages
- Sharing files with the network (e.g. network.png)
- To exit a peer, use the 'exit' command. The peer will unregister from the tracker and shut down.

# Implementation Details
## Tracker('tracker.py')
a Tracker class that represents a central server for maintaining a list of peer entities (such as computers) participating in a network, often used in peer-to-peer communication systems. Let's break down the methods inside the Tracker class:

- ```__init__```: This is the initializer method that gets called when a new Tracker object is created. It sets up the tracker with its network address information, a set to keep track of the peers, and a threading lock for coordinating access to this set across multiple threads.

- ```start```: This method sets the tracker in motion. It begins by creating a socket, binding it to the specified host and port, and starting to listen for incoming connections. It also spins off a background thread that periodically runs the cleanup_peers method. For each incoming connection, it starts a new thread that will use the handle_peer_registration method.

- ```cleanup_peers```: This method loops indefinitely, waking up every 20 seconds to check that each peer listed is still responsive. It does this by trying to send a 'PING' message using a temporary socket. If it doesn't get a 'PONG' response, or if there's a problem connecting to the peer, it determines that the peer is unresponsive and removes it from the set of known peers.

- ```broadcast_to_peers```: This method is used to send a message to all the peers currently known to the tracker. It goes through the list of peers, tries to establish a connection, and sends the message. If there's an error during this process, it prints an error message.

- ```handle_peer_registration```: This method is used to handle the initial connection from a peer. It reads data from the connected peer's socket. If the received data starts with the text 'REGISTER', it denotes that a peer is trying to register itself with the tracker. The method processes the registration by recording the information of the peer. However, the code snippet for what happens upon 'REGISTER' is complete and doesn't show the actual registration handling.

## Peer ('peer.py')
- ```__init__```: This is the constructor of the Peer class. When you create a new Peer object, this method initializes it with a host address and port number. It sets up file paths for various data files and creates a socket for listening to incoming connections. It also initializes a set to store known peer addresses and a lock for thread safety.

- ```register_with_tracker```: This method allows the peer to register itself with a tracker server. The peer sends a "REGISTER" message to the tracker, along with its address. If the registration is successful, it updates its list of known peers by requesting the current list from the tracker.

- ```unregister_from_tracker```: This method is used to unregister the peer from the tracker server before shutting down. It sends an "UNREGISTER" message to the tracker and waits for a confirmation response.

- ```update_peers_list```: This method requests the current list of active peers from the tracker and updates the peer’s local list.

- ```start_listening```: In this method, the peer starts listening for incoming connections on its host and port. It sets up a loop to accept any incoming connections and spawns a new thread to handle each connection with the handle_peer method.

- ```handle_peer```: When a connection is accepted, this method handles the communication with the connected peer. It waits for messages such as "PING" or "SEND_FILE" and responds or takes action accordingly.

- ```send_broadcast_message```: This method is used to send a message to all known peers except itself. It goes through its list of peers and sends the message over a new socket connection.

- ```recv_ack```: It waits to receive an "ACK" (acknowledgment) after sending some data. If it doesn't receive "ACK" within a specified time or after several retries, it either keeps trying or raises an error.

- ```send_file```: The method opens the specified file_path in binary read mode. It reads the entire file to compute a SHA256 checksum, which will be used for integrity verification by the recipient. Before attempting to send the file, the method verifies that the provided peer_socket is open and valid. Then the method prepares a JSON object containing the file's metadata, including the file name, size, and computed checksum. This JSON object is then sent over to the receiving peer. Following the transmission of the metadata, the method waits for an acknowledgment ('ACK') from the peer. If it doesn't receive it, or if the acknowledgment is incorrect, it raises an exception. The method reads the file data in chunks and sends each chunk to the receiving peer until the entire file is sent. Once the whole file has been transmitted, the method waits for an acknowledgment from the peer again to confirm that the file was received and that the transmitted checksum matches the one computed on the receiving end.

- ```receive_file```: This method receives a chunk of data from a peer, which is expected to contain JSON-formatted metadata about the file, including the file's name, size, and a checksum value (SHA256) for verifying the integrity of the file. After successfully receiving and parsing the metadata, the method sends an acknowledgment ('ACK') back to the sending peer to indicate it's ready to receive the file data. The method prepares a file path where the incoming file will be saved. If a file with the same name already exists, it generates a new name to prevent overwriting. Afterwards it enters a loop to receive the actual file data. It reads chunks of data and writes them to the file being created on disk, until it has received the total number of bytes specified in the metadata. Once all data has been received, it computes a checksum (SHA256) of the file and compares it with the checksum in the metadata, to ensure that the file wasn't corrupted during the transmission. If the verification is successful, it sends a final acknowledgment ('ACK') to the sending peer to confirm that the file was received. If there's an issue with the checksum, it will delete the received file to prevent keeping corrupted data.

## File Structure
- The data directory contains sample files (wr_sensor_data.csv, network.png, and data.json) that can be shared among peers.
- The received_files directory is used by peers to store files received from other peers.



