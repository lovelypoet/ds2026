#!/usr/bin/env python3
# rpc_server.py
from xmlrpc.server import SimpleXMLRPCServer
import base64
import os
import hashlib

HOST = '0.0.0.0'
PORT = 9000
SAVE_DIR = 'received'

class FileTransferService:
    def __init__(self, save_dir):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
        self.active_transfers = {}
    
    def ping(self):
        """Health check endpoint"""
        return "pong"
    
    def start_transfer(self, filename, filesize):
        """Initialize a file transfer session"""
        transfer_id = hashlib.md5(f"{filename}{filesize}".encode()).hexdigest()
        filepath = os.path.join(self.save_dir, os.path.basename(filename))
        
        self.active_transfers[transfer_id] = {
            'filename': filename,
            'filepath': filepath,
            'filesize': filesize,
            'received': 0,
            'file_handle': open(filepath, 'wb')
        }
        
        print(f"[+] Started transfer {transfer_id}: {filename} ({filesize} bytes)")
        return transfer_id
    
    def upload_chunk(self, transfer_id, chunk_data):
        """Receive a file chunk (base64 encoded)"""
        if transfer_id not in self.active_transfers:
            return {'success': False, 'error': 'Invalid transfer ID'}
        
        transfer = self.active_transfers[transfer_id]
        
        try:
            # Decode base64 chunk
            chunk = base64.b64decode(chunk_data)
            transfer['file_handle'].write(chunk)
            transfer['received'] += len(chunk)
            
            progress = (transfer['received'] / transfer['filesize']) * 100
            print(f"\r[{transfer_id[:8]}] Progress: {progress:.1f}%", end='', flush=True)
            
            return {
                'success': True,
                'received': transfer['received'],
                'expected': transfer['filesize']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def finish_transfer(self, transfer_id):
        """Finalize the transfer"""
        if transfer_id not in self.active_transfers:
            return {'success': False, 'error': 'Invalid transfer ID'}
        
        transfer = self.active_transfers[transfer_id]
        transfer['file_handle'].close()
        
        success = transfer['received'] == transfer['filesize']
        
        print(f"\n[+] Transfer {transfer_id[:8]} completed: {transfer['filepath']}")
        
        del self.active_transfers[transfer_id]
        
        return {
            'success': success,
            'filepath': transfer['filepath'],
            'received': transfer['received'],
            'expected': transfer['filesize']
        }
    
    def cancel_transfer(self, transfer_id):
        """Cancel an ongoing transfer"""
        if transfer_id in self.active_transfers:
            transfer = self.active_transfers[transfer_id]
            transfer['file_handle'].close()
            os.remove(transfer['filepath'])
            del self.active_transfers[transfer_id]
            return {'success': True}
        return {'success': False, 'error': 'Transfer not found'}
    
    def list_files(self):
        """List received files"""
        files = []
        for f in os.listdir(self.save_dir):
            path = os.path.join(self.save_dir, f)
            if os.path.isfile(path):
                files.append({
                    'name': f,
                    'size': os.path.getsize(path)
                })
        return files

def main():
    service = FileTransferService(SAVE_DIR)
    
    server = SimpleXMLRPCServer((HOST, PORT), allow_none=True)
    server.register_instance(service)
    
    print(f"[+] RPC File Transfer Server listening on {HOST}:{PORT}")
    print(f"[+] Files will be saved to: {SAVE_DIR}/")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[-] Server shutting down")

if __name__ == '__main__':
    main()

