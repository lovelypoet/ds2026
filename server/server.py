#!/usr/bin/env python3
# server.py
import socket
import struct
import os

HOST = '0.0.0.0'
PORT = 9000
CHUNK = 4096

def recv_all(conn, n):
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(conn, addr, save_dir='received'):
    print(f"[+] Connection from {addr}")
    # read name length (8 bytes)
    raw = recv_all(conn, 8)
    if not raw:
        print(" Failed to read filename length")
        return
    (name_len,) = struct.unpack('!Q', raw) #!Q is network order unsigned long long for 8-byte metadata
    name_bytes = recv_all(conn, name_len)
    if name_bytes is None:
        print(" Failed to read filename")
        return
    filename = name_bytes.decode('utf-8')

    raw = recv_all(conn, 8)
    if not raw:
        print(" Failed to read filesize")
        return
    (filesize,) = struct.unpack('!Q', raw)
    print(f" Receiving file: {filename} ({filesize} bytes)")

    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, os.path.basename(filename))
    # send ACK
    conn.sendall(b'\x01')

    received = 0
    with open(path, 'wb') as f:
        while received < filesize:
            to_read = min(CHUNK, filesize - received)
            chunk = conn.recv(to_read)
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
            # optional: print progress
            print(f"\rReceived {received}/{filesize} bytes", end='', flush=True)
    print()

    if received == filesize:
        print(f"[+] File saved to {path}")
        conn.sendall(b'\x02')  # EOF-ACK
    else:
        print(" Connection closed before full file received")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"[+] Listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            with conn:
                try:
                    handle_client(conn, addr)
                except Exception as e:
                    print("[-] Error handling client:", e)

if __name__ == '__main__':
    main()

