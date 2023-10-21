import json
import time
from socket import *

serverHost = '127.0.0.1' # localhost
serverPort = 12000 # port number
bufferSize = 2048 # buffer size
json_filename = "wheel_rotation_sensor_data.json" # json file name
 

with open(json_filename) as json_file: # open json file
    data = json.load(json_file) # load json file
 print('CLIENT has loaded the data from JSON file')

clientSocket = socket(AF_INET, SOCK_DGRAM) # create socket
clientSocket.settimeout(1) # set timeout 1 second
print('CLIENT has created a socket\n')

for batch in data: # for each batch in a data
    outMessage = json.dumps(batch) # encode any Python object into JSON formatted String

    print('CLIENT is sending the message to the server ...')
    start = time.time() # start to measure time
    clientSocket.sendto(outMessage.encode(), (serverHost, serverPort)) # send message to server
    try:
        inMessage, serverAddress = clientSocket.recvfrom(bufferSize) # receive message from server
    except: # If the client did not receive packet in 1 second, it will timeout
        print('CLIENT has timed out')
        continue
    end = time.time() # end to measure time
    print('CLIENT received the message from the server')
    print('CLIENT Round Trip Time:', end - start, 'seconds')
    print()

clientSocket.close() # close socket