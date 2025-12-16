import threading
import time
import sys
import uuid
from .transport import MPITransport, TAG_MSG, TAG_CMD
from .models import Message, MessageType, User

class ChatClient:
    def __init__(self, transport: MPITransport, user_id: str):
        self.transport = transport
        self.user_id = user_id
        self.rank = transport.get_rank()
        self.params = {'display_name': f'User_{self.rank}'}
        self.running = False
        self.online_users = []
        self.recv_thread = threading.Thread(target=self.listen_loop, daemon=True)
        
        # Handshake State
        self.active_transfers = {} # file_id -> {filepath, to_rank, use_p2p, ...}
        self.pending_offers = {}   # from_rank -> {file_id, filename, size, ...}

    def login(self):
        join_cmd = {
            'type': 'JOIN',
            'user': {
                'user_id': self.user_id,
                'display_name': self.params['display_name']
            }
        }
        self.transport.send(join_cmd, 0, TAG_CMD)
        self.running = True
        self.recv_thread.start()
        print(f"[Client] Logged in as {self.params['display_name']} (Rank {self.rank})")

    def send_message(self, content: str, to_user: str = 'all', use_p2p: bool = False):
        msg: Message = {
            'message_id': str(uuid.uuid4()),
            'from_user': self.user_id,
            'to_user': to_user,
            'content': content,
            'message_type': MessageType.TEXT.value,
            'timestamp': time.time()
        }
        
        # P2P Logic for DMs
        if use_p2p and to_user != 'all':
            target_rank = next((u['rank'] for u in self.online_users if u['user_id'] == to_user), None)
            if target_rank:
                try:
                    self.transport.send(msg, target_rank, TAG_MSG)
                    return
                except Exception as e:
                    self._safe_print(f"[P2P Failed]: {e}")
        
        self.transport.send(msg, 0, TAG_MSG)

    def listen_loop(self):
        while self.running:
            try:
                if self.transport.check_msg():
                    data, source, tag = self.transport.receive()
                    self.handle_incoming(data, source, tag)
                else:
                    time.sleep(0.01)
            except Exception as e:
                print(f"[Client Error] {e}")
                break

    def _safe_print(self, msg):
        sys.stdout.write('\r' + msg + '\n')
        sys.stdout.write('You: ')
        sys.stdout.flush()

    def send_file(self, filepath: str, to_rank: int, use_p2p: bool = False):
        """Initiates file transfer by sending a Request (REQ)"""
        import os
        if not os.path.exists(filepath):
            self._safe_print(f"File not found: {filepath}")
            return

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        target_id = next((u['user_id'] for u in self.online_users if u['rank'] == to_rank), None)
        
        if not target_id:
            self._safe_print(f"Rank {to_rank} not found online.")
            return

        file_id = str(uuid.uuid4())
        
        # Store state for when ACK comes back
        self.active_transfers[file_id] = {
            'filepath': filepath,
            'to_rank': to_rank,
            'use_p2p': use_p2p,
            'target_id': target_id,
            'filename': filename,
            'filesize': file_size
        }

        # Determine Routing for REQ
        dest_rank = to_rank if use_p2p else 0
        tag_req = 4 # TAG_FILE_REQ

        meta = {
            'file_id': file_id,
            'filename': filename,
            'size': file_size,
            'from_user': self.user_id,
            'to_user': target_id,
            'from_rank': self.rank # Helpful for receiver
        }
        
        try:
            self.transport.send(meta, dest_rank, tag_req)
            self._safe_print(f"Sent request for '{filename}' to Rank {to_rank}. Waiting for approval...")
        except Exception as e:
            self._safe_print(f"Failed to send request: {e}")
            del self.active_transfers[file_id]

    def _perform_upload(self, transfer_info):
        """Actually sends the file chunks (Called after ACK)"""
        import os
        file_id = "unknown"
        try:
            filepath = transfer_info['filepath']
            to_rank = transfer_info['to_rank']
            use_p2p = transfer_info['use_p2p']
            target_id = transfer_info['target_id']
            filename = transfer_info['filename']
            file_size = transfer_info['filesize']
            
            dest_rank = to_rank if use_p2p else 0
            tag_meta = 2   # TAG_FILE_META (Still needed for legacy/setup or just skipped?)
            # Actually, we can skip META if the receiver already has it from REQ, 
            # BUT the receiver logic (handle_incoming) currently expects META + CHUNKS.
            # To be safe and compatible with existing receive logic, we send META then CHUNKS.
            
            tag_chunk = 3 
            mode_str = "P2P" if use_p2p else "Server Relay"

            # 1. Send Metadata (The "Official" Start)
            meta = {
                'file_id': file_id,
                'filename': filename,
                'size': file_size,
                'from_user': self.user_id,
                'to_user': target_id
            }
            self.transport.send(meta, dest_rank, tag_meta)
            self._safe_print(f"[{mode_str}] Uploading {filename} to Rank {to_rank}...")

            # 2. Send Chunks
            CHUNK_SIZE = 1024 * 1024 
            chunk_idx = 0
            total_chunks = (file_size // CHUNK_SIZE) + 1
            
            with open(filepath, 'rb') as f:
                while True:
                    data = f.read(CHUNK_SIZE)
                    if not data:
                        break
                    
                    chunk = {
                        'file_id': file_id,
                        'filename': filename,
                        'chunk_index': chunk_idx,
                        'total_chunks': total_chunks,
                        'data': data,
                        'to_user': target_id 
                    }
                    self.transport.send(chunk, dest_rank, tag_chunk)
                    chunk_idx += 1
                    time.sleep(0.001)
                    
            self._safe_print(f"File {filename} sent.")
            
        except Exception as e:
            if use_p2p:
                self._safe_print(f"[P2P Failed]: {e}. Falling back to Server Relay.")
                transfer_info['use_p2p'] = False
                self._perform_upload(transfer_info)
            else:
                self._safe_print(f"Upload failed: {e}")

    def handle_incoming(self, data, source, tag):
        if tag == TAG_MSG:
            msg: Message = data
            sender = msg['from_user']
            content = msg['content']
            type = msg['message_type']
            timestamp = time.strftime('%H:%M:%S', time.localtime(msg['timestamp']))
            
            text_to_print = ""
            if type == MessageType.SYSTEM.value:
                text_to_print = f"[SYSTEM {timestamp}] {content}"
            else:
                prefix = ""
                if msg.get('to_user') and msg['to_user'] != 'all':
                    prefix = "(Private) "
                text_to_print = f"{prefix}[{sender} {timestamp}]: {content}"
            
            self._safe_print(text_to_print)
                
        elif tag == TAG_CMD:
            cmd = data
            if cmd['type'] == 'USER_LIST_UPDATE':
                self.online_users = cmd['users']
        
        elif tag == 4: # TAG_FILE_REQ
            meta = data
            from_rank = meta.get('from_rank', source) # Fallback to source if not in meta
            filename = meta['filename']
            size_mb = meta['size'] / (1024*1024)
            
            self.pending_offers[from_rank] = meta
            self._safe_print(f"\n[Request] Rank {from_rank} wants to send '{filename}' ({size_mb:.2f} MB).")
            self._safe_print(f"Type '/accept {from_rank}' to receive or '/deny {from_rank}' to reject.")

        elif tag == 5: # TAG_FILE_ACK
            ack = data
            file_id = ack['file_id']
            if file_id in self.active_transfers:
                transfer_info = self.active_transfers.pop(file_id)
                self._safe_print(f"Request accepted by receiver. Starting upload...")
                threading.Thread(target=self._perform_upload, args=(transfer_info,)).start()

        elif tag == 6: # TAG_FILE_DENY
            deny = data
            file_id = deny['file_id']
            if file_id in self.active_transfers:
                info = self.active_transfers.pop(file_id)
                self._safe_print(f"Request for '{info['filename']}' was DENIED by receiver.")

        elif tag == 2: 
            meta = data
            filename = meta['filename']
            sender = meta['from_user']
            self._safe_print(f"Incoming file '{filename}' from {sender}...")
            
        elif tag == 3: 
            import os
            chunk = data
            filename = chunk['filename']
            file_data = chunk['data']
            
            os.makedirs("downloads", exist_ok=True)
            path = os.path.join("downloads", filename)
            
            with open(path, 'ab') as f:
                f.write(file_data)
                
            if chunk['chunk_index'] == chunk['total_chunks'] - 1:
                self._safe_print(f"File '{filename}' download complete (saved to downloads/).")

    def start_input_loop(self):
        print("Type a message and press Enter. Type '/quit' to exit.")
        print("Type '/users' to list online users.")
        print("Type '/dm <rank> <msg>' to send a direct message.")
        print("Type '/send <path> <rank>' to send a file.")
        
        sys.stdout.write("You: ")
        sys.stdout.flush()

        while self.running:
            try:
                inp = input() 
                sys.stdout.write("You: ")
                sys.stdout.flush()

                if inp.strip() == '/quit':
                    self.running = False
                    self.transport.send({'type': 'LEAVE'}, 0, TAG_CMD)
                    break
                
                if inp.strip() == '/users':
                    print("\n--- Online Users ---")
                    for u in self.online_users:
                        print(f"Rank {u['rank']}: {u['display_name']}")
                    sys.stdout.write("You: ")
                    sys.stdout.flush()
                    continue
                    
                    continue
                    
                if inp.startswith('/accept '):
                    try:
                        rank = int(inp.split(' ')[1])
                        if rank in self.pending_offers:
                            meta = self.pending_offers.pop(rank)
                            ack_msg = {'file_id': meta['file_id']}
                            # ACK goes back to sender. Logic: Sender sent REQ via (P2P or Server).
                            # We can reply via Server (SAFE) or P2P. Let's reply via Server to be safe,
                            # OR just reply to 'from_rank' via Server.
                            # Actually, simplest is send to Rank 0 routed to target, or direct if we prefer.
                            # Let's use Server Relay for Control Signals (Reliable).
                            ack_msg['to_user'] = meta['from_user'] # Needed for Server routing
                            self.transport.send(ack_msg, 0, 5) # TAG_FILE_ACK
                            self._safe_print(f"Accepted file from Rank {rank}.")
                        else:
                            print("No pending offer from that rank.")
                    except:
                        print("Usage: /accept <rank>")
                    continue

                if inp.startswith('/deny '):
                    try:
                        rank = int(inp.split(' ')[1])
                        if rank in self.pending_offers:
                            meta = self.pending_offers.pop(rank)
                            deny_msg = {'file_id': meta['file_id'], 'to_user': meta['from_user']}
                            self.transport.send(deny_msg, 0, 6) # TAG_FILE_DENY
                            self._safe_print(f"Denied file from Rank {rank}.")
                        else:
                            print("No pending offer from that rank.")
                    except:
                        print("Usage: /deny <rank>")
                    continue

                if inp.startswith('/dm '):
                    parts = inp.split(' ')
                    if len(parts) >= 3:
                        try:
                            target_rank = int(parts[1])
                            
                            use_p2p = False
                            content_parts = parts[2:]
                            if "--mode" in content_parts:
                                idx = content_parts.index("--mode")
                                if idx + 1 < len(content_parts) and content_parts[idx+1].lower() == 'p2p':
                                    use_p2p = True
                                    del content_parts[idx:idx+2]
                            
                            text = " ".join(content_parts)
                            
                            target_id = next((u['user_id'] for u in self.online_users if u['rank'] == target_rank), None)
                            if target_id:
                                self.send_message(text, to_user=target_id, use_p2p=use_p2p)
                            else:
                                print("User not found.")
                        except ValueError:
                             print("Invalid rank.")
                    else:
                        print("Usage: /dm <rank> <msg> [--mode p2p]")
                    
                    continue
                
                if inp.startswith('/send '):
                    parts = inp.split(' ')
                    if len(parts) >= 3:
                        filepath = parts[1]
                        try:
                            rank = int(parts[2])
                            use_p2p = False
                            if "--mode" in parts and "p2p" in parts:
                                use_p2p = True
                            
                            threading.Thread(target=self.send_file, args=(filepath, rank, use_p2p)).start()
                        except ValueError:
                             print("Invalid rank.")
                    else:
                        print("Usage: /send <filepath> <rank> [--mode p2p]")
                    continue

                self.send_message(inp)
            except EOFError:
                break
            except Exception as e:
                print(f"Input Error: {e}")
        self.transport.close()
