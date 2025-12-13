#!/usr/bin/env python3
# mpi_client.py
from mpi4py import MPI
import os
import sys
import json

CHUNK_SIZE = 64 * 1024  # 64KB

def send_file(comm, rank, filepath, server_rank):
    """Send a file to a specific server rank"""
    
    if not os.path.isfile(filepath):
        print(f"[Rank {rank}] Error: File not found: {filepath}")
        return False
    
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    
    print(f"[Rank {rank}] Sending {filename} ({filesize} bytes) to server rank {server_rank}")
    
    # Send metadata
    metadata = {
        'filename': filename,
        'filesize': filesize
    }
    comm.send(metadata, dest=server_rank, tag=1)
    
    # Wait for server ready signal
    response = comm.recv(source=server_rank, tag=2)
    if response['status'] != 'ready':
        print(f"[Rank {rank}] Server not ready")
        return False
    
    # Send file in chunks
    sent = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            
            comm.send(chunk, dest=server_rank, tag=3)
            
            # Wait for chunk acknowledgment
            ack = comm.recv(source=server_rank, tag=4)
            sent += len(chunk)
            
            progress = (sent / filesize) * 100
            print(f"\r[Rank {rank}] Progress: {progress:.1f}% ({sent}/{filesize} bytes)", 
                  end='', flush=True)
    
    print()
    
    # Wait for final confirmation
    result = comm.recv(source=server_rank, tag=5)
    
    if result['status'] == 'complete':
        print(f"[Rank {rank}] Transfer complete! File saved: {result['filepath']}")
        return True
    else:
        print(f"[Rank {rank}] Transfer failed")
        return False

def list_files(comm, rank, server_rank):
    """Request file list from server"""
    print(f"[Rank {rank}] Requesting file list from server rank {server_rank}")
    
    comm.send({'command': 'list'}, dest=server_rank, tag=7)
    
    response = comm.recv(source=server_rank, tag=6)
    files = response['files']
    
    print(f"\n[Rank {rank}] Files on server rank {server_rank} ({len(files)} total):")
    for f in files:
        print(f"  - {f['name']} ({f['size']} bytes)")

def client_process(comm, rank, filepath, command='send'):
    """Main client process"""
    size = comm.Get_size()
    
    if size < 2:
        print(f"[Rank {rank}] Error: Need at least 2 processes (1 client + 1 server)")
        return
    
    # Use round-robin to select server (skip rank 0 if it's master-only)
    # For simplicity, send to rank 1
    server_rank = 1
    
    if command == 'list':
        list_files(comm, rank, server_rank)
    elif command == 'send':
        send_file(comm, rank, filepath, server_rank)
    else:
        print(f"[Rank {rank}] Unknown command: {command}")

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    if len(sys.argv) < 2:
        if rank == 0:
            print("Usage:")
            print("  Send file:  mpiexec -n <num_procs> python mpi_client.py <file_path>")
            print("  List files: mpiexec -n <num_procs> python mpi_client.py --list")
            print("\nExample:")
            print("  mpiexec -n 4 python mpi_client.py document.pdf")
            print("  (1 client process + 3 server processes)")
        sys.exit(1)
    
    # Only rank 0 acts as client in this simple setup
    if rank == 0:
        if sys.argv[1] == '--list':
            client_process(comm, rank, None, command='list')
        else:
            filepath = sys.argv[1]
            client_process(comm, rank, filepath, command='send')
    else:
        # Other ranks wait (server will be running separately)
        print(f"[Rank {rank}] Waiting as potential server (run mpi_server.py separately)")

if __name__ == '__main__':
    main()
