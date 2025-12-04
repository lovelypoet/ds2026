#!/usr/bin/env python3
# rpc_client.py
import xmlrpc.client
import base64
import sys
import os

CHUNK_SIZE = 64 * 1024  # 64KB chunks

def send_file(server_url, filepath):
    """Send a file to the RPC server"""
    
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}")
        return False
    
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    
    print(f"[+] Connecting to {server_url}")
    proxy = xmlrpc.client.ServerProxy(server_url)
    
    try:
        # Test connection
        proxy.ping()
        print("[+] Server is reachable")
    except Exception as e:
        print(f"[-] Cannot connect to server: {e}")
        return False
    
    try:
        # Start transfer
        print(f"[+] Initiating transfer: {filename} ({filesize} bytes)")
        transfer_id = proxy.start_transfer(filename, filesize)
        print(f"[+] Transfer ID: {transfer_id}")
        
        # Send file in chunks
        sent = 0
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                # Encode chunk as base64 for XML-RPC
                encoded_chunk = base64.b64encode(chunk).decode('ascii')
                
                result = proxy.upload_chunk(transfer_id, encoded_chunk)
                
                if not result['success']:
                    print(f"\n[-] Upload failed: {result.get('error', 'Unknown error')}")
                    proxy.cancel_transfer(transfer_id)
                    return False
                
                sent += len(chunk)
                progress = (sent / filesize) * 100
                print(f"\rProgress: {progress:.1f}% ({sent}/{filesize} bytes)", end='', flush=True)
        
        print()
        
        # Finalize transfer
        result = proxy.finish_transfer(transfer_id)
        
        if result['success']:
            print(f"[+] Transfer completed successfully!")
            print(f"[+] File saved on server: {result['filepath']}")
            return True
        else:
            print(f"[-] Transfer failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n[-] Error during transfer: {e}")
        try:
            proxy.cancel_transfer(transfer_id)
        except:
            pass
        return False

def list_files(server_url):
    """List files on the server"""
    proxy = xmlrpc.client.ServerProxy(server_url)
    
    try:
        files = proxy.list_files()
        print(f"\n[+] Files on server ({len(files)} total):")
        for f in files:
            print(f"  - {f['name']} ({f['size']} bytes)")
    except Exception as e:
        print(f"[-] Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Upload:   python rpc_client.py <server_url> <file_path>")
        print("  List:     python rpc_client.py <server_url> --list")
        print("\nExample:")
        print("  python rpc_client.py http://localhost:9000 document.pdf")
        sys.exit(1)
    
    server_url = sys.argv[1]
    
    if len(sys.argv) == 3 and sys.argv[2] == '--list':
        list_files(server_url)
    else:
        filepath = sys.argv[2]
        send_file(server_url, filepath)
