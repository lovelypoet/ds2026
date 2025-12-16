import time
from .transport import MPITransport, TAG_MSG, TAG_CMD, TAG_FILE_META, TAG_FILE_CHUNK, TAG_FILE_REQ, TAG_FILE_ACK, TAG_FILE_DENY
from .models import Message, MessageType, User

class Server:
    def __init__(self, transport: MPITransport):
        self.transport = transport
        self.users: dict[int, User] = {}
        self.start_time = time.time()
        self.users[0] = {
            'user_id': 'server',
            'display_name': 'System',
            'rank': 0
        }

    def start(self):
        print(f"[Server] Started on Rank 0. Waiting for clients...")
        while True:
            if self.transport.check_msg():
                data, source, tag = self.transport.receive()
                should_continue = self.handle_message(data, source, tag)
                if should_continue is False:
                    break
            else:
                time.sleep(0.01)

    def handle_message(self, data, source: int, tag: int):
        if tag == TAG_CMD:
            return self.handle_command(data, source)
        elif tag in [TAG_MSG, TAG_FILE_META, TAG_FILE_CHUNK, TAG_FILE_REQ, TAG_FILE_ACK, TAG_FILE_DENY]:
            self.route_message(data, source, tag)
        else:
            print(f"[Server] Unknown tag {tag} from {source}")
        return True

    def handle_command(self, cmd: dict, source: int):
        type = cmd.get('type')
        if type == 'JOIN':
            user_info = cmd.get('user')
            user_info['rank'] = source
            self.users[source] = user_info
            print(f"[Server] User joined: {user_info['display_name']} (Rank {source})")
            self.broadcast_system_msg(f"{user_info['display_name']} has joined the chat.")
            self.broadcast_user_list()
        elif type == 'LEAVE':
            if source in self.users:
                name = self.users[source]['display_name']
                del self.users[source]
                print(f"[Server] User left: {name} (Rank {source})")
                self.broadcast_system_msg(f"{name} has left the chat.")
                self.broadcast_user_list()
        elif type == 'SHUTDOWN':
            print("[Server] Shutdown command received. Stopping.")
            return False
        return True

    def route_message(self, msg: dict, source: int, tag: int):
        if source not in self.users:
            print(f"[Server] Dropping message from unknown rank {source}")
            return

        if tag == TAG_MSG and not msg.get('timestamp'):
            msg['timestamp'] = time.time()

        dest_id = msg.get('to_user') 
        
        if dest_id and dest_id != 'all':
            target_rank = self.get_rank_by_id(dest_id)
            if target_rank:
                print(f"[Server] Routing tag {tag} from {source} to {target_rank}")
                self.transport.send(msg, target_rank, tag)
            else:
                print(f"[Server] User {dest_id} not found")
        else:
            for rank in self.users:
                if rank != 0 and rank != source:
                    self.transport.send(msg, rank, tag)

    def broadcast_system_msg(self, text: str):
        msg: Message = {
            'message_id': f'sys_{time.time()}',
            'from_user': 'server',
            'content': text,
            'message_type': MessageType.SYSTEM.value,
            'timestamp': time.time()
        }
        for rank in self.users:
            if rank != 0:
                self.transport.send(msg, rank, TAG_MSG)

    def broadcast_user_list(self):
        user_list = list(self.users.values())
        update_cmd = {
            'type': 'USER_LIST_UPDATE',
            'users': user_list
        }
        for rank in self.users:
            if rank != 0:
                self.transport.send(update_cmd, rank, TAG_CMD)

    def get_rank_by_id(self, user_id: str) -> int:
        for r, u in self.users.items():
            if u['user_id'] == user_id:
                return r
        return None
