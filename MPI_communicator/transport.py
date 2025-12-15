from typing import Protocol, Tuple, Any, Optional
from mpi4py import MPI
import pickle
import time

TAG_MSG = 1
TAG_FILE_META = 2
TAG_FILE_CHUNK = 3
TAG_CMD = 4
TAG_CHECK = 5

class MPITransport:
    def __init__(self, comm=MPI.COMM_WORLD):
        self.comm = comm
        self.rank = comm.Get_rank()
        self.size = comm.Get_size()
        self.connected = True

    def send(self, data: Any, destination: int, tag: int = TAG_MSG) -> None:
        try:
            self.comm.send(data, dest=destination, tag=tag)
        except Exception as e:
            print(f"[Transport] Error sending to {destination}: {e}")

    def receive(self, source: int = MPI.ANY_SOURCE, tag: int = MPI.ANY_TAG) -> Tuple[Any, int, int]:
        status = MPI.Status()
        data = self.comm.recv(source=source, tag=tag, status=status)
        return data, status.Get_source(), status.Get_tag()

    def check_msg(self) -> bool:
        status = MPI.Status()
        return self.comm.Iprobe(source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)

    def get_rank(self) -> int:
        return self.rank

    def close(self):
        self.connected = False
