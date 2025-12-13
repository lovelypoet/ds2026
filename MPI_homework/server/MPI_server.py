#!/usr/bin/env python3
# mpi_server.py
from mpi4py import MPI
import os
import json
import time

SAVE_DIR = 'received'
CHUNK_SIZE = 64 * 1024  # 64KB

def handle_file_transfer(comm, status):
    """Handle incoming file transfer from a client"""
    source = status.Get_source()
    
    # Receive metadata
    metadata = comm.recv(source=source, tag=1)
    filename = metadata['filename']
    filesize = metadata['filesize']
    
    filepath = os.path.join(SAVE_DIR, os.path.basename(filename))
    
    print(f"[Rank {comm.Get_rank()}] Receiving {filename} ({filesize} bytes) from rank {source}")
    
    # Send acknowledgment
    comm.send({'status': 'ready'}, dest=source, tag=2)
    
    # Receive file data in chunks
    received = 0
    with open(filepath, 'wb') as f:
        while received < filesize:
            chunk = comm.recv(source=source, tag=3)
            f.write(chunk)
            received += len(chunk)
            
            # Send chunk acknowledgment
            progress = (received / filesize) * 100
            comm.send({'received': received, 'progress': progress}, dest=source, tag=4)
            
            print(f"\r[Rank {comm.Get_rank()}] Progress: {progress:.1f}%", end='', flush=True)
    
    print(f"\n[Rank {comm.Get_rank()}] File saved: {filepath}")
    
    # Send final confirmation
    comm.send({'status': 'complete', 'filepath': filepath}, dest=source, tag=5)

def list_files(comm, source):
    """Send list of files to requesting client"""
    files = []
    if os.path.exists(SAVE_DIR):
        for f in os.listdir(SAVE_DIR):
            path = os.path.join(SAVE_DIR, f)
            if os.path.isfile(path):
                files.append({
                    'name': f,
                    'size': os.path.getsize(path)
                })
    
    comm.send({'files': files}, dest=source, tag=6)

def server_process(comm, rank):
    """Main server process loop"""
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    print(f"[Server Rank {rank}] Ready to receive files")
    print(f"[Server Rank {rank}] Files will be saved to: {SAVE_DIR}/")
    
    while True:
        # Probe for incoming messages
        status = MPI.Status()
        if comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status):
            tag = status.Get_tag()
            source = status.Get_source()
            
            if tag == 1:  # File transfer request
                handle_file_transfer(comm, status)
            elif tag == 7:  # List files request
                list_files(comm, source)
            elif tag == 99:  # Shutdown signal
                print(f"[Server Rank {rank}] Shutting down")
                break
        
        time.sleep(0.01)  # Small delay to prevent busy waiting

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    if rank == 0:
        print(f"[Master] MPI File Transfer Server initialized")
        print(f"[Master] Total processes: {size}")
        print(f"[Master] Server processes: {size - 1}")
        print("=" * 60)
    
    # All processes except rank 0 act as servers
    if rank > 0:
        server_process(comm, rank)
    else:
        # Rank 0 can coordinate or also act as a server
        print("[Master] Press Ctrl+C to shutdown all servers")
        try:
            server_process(comm, rank)
        except KeyboardInterrupt:
            print("\n[Master] Broadcasting shutdown signal")
            for i in range(1, size):
                comm.send(None, dest=i, tag=99)

if __name__ == '__main__':
    main()
