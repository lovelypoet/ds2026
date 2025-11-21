#!/usr/bin/env python3
# client.py 

import socket
import struct
import sys
import os

CHUNK = 4096

def send_file(server_host, server_port, filepath):
    if not os.path.isfile(filepath):
        print("File not found:", filepath); return
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_host, server_port))
        # send filename length and filename
        name_bytes = filename.encode('utf-8')
        s.sendall(struct.pack('!Q', len(name_bytes)))
        s.sendall(name_bytes)
        # send filesize
        s.sendall(struct.pack('!Q', filesize))
        # wait for server ACK
        ack = s.recv(1)
        if ack != b'\x01':
            print("No ACK from server, aborting")
            return
        sent = 0
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                s.sendall(chunk)
                sent += len(chunk)
                print(f"\rSent {sent}/{filesize} bytes", end='', flush=True)
        print()
        # wait for EOF ack
        eof = s.recv(1)
        if eof == b'\x02':
            print("Server confirmed receipt")
        else:
            print(" No EOF confirmation")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python client.py <server_ip> <server_port> <file_path>")
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    path = sys.argv[3]
    send_file(host, port, path)
