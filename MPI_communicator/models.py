from typing import TypedDict, NotRequired, Any, List, Union
from datetime import datetime
from enum import Enum

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class Message(TypedDict):
    message_id: str
    from_user: str
    to_user: NotRequired[str]
    channel: NotRequired[str]
    content: str
    message_type: str
    timestamp: float
    metadata: NotRequired[dict[str, Any]]

class User(TypedDict):
    user_id: str
    display_name: str
    rank: int
    public_key: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]

class FileChunk(TypedDict):
    file_id: str
    filename: str
    chunk_index: int
    total_chunks: int
    data: bytes

class ConnectionInfo(TypedDict):
    connection_id: str
    user: User
    connected_at: float
    is_online: bool
    metadata: NotRequired[dict[str, Any]]
