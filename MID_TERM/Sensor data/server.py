from socket import *

serverHost = '127.0.0.1' # localhost
serverPort = 12000 # port number
bufferSize = 2048 # buffer size

serverSocket = socket(AF_INET, SOCK_DGRAM) # create socket
print('SERVER has created a socket')
serverSocket.bind((serverHost, serverPort)) # bind socket to port
print('SERVER is listening on address', serverHost, 'and port', serverPort)

while True: # infinite loop
    message, clientAddress = serverSocket.recvfrom(bufferSize) # receive message and address from client
    print('SERVER received message from client and sending it back ...')
    serverSocket.sendto(message, clientAddress) # send message back to client