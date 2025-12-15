import sys
from mpi4py import MPI
from .transport import MPITransport
from .server import Server
from .client import ChatClient
import uuid

def main():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    transport = MPITransport(comm)
    
    if rank == 0:
        print("==========================================")
        print(f"Starting MPI Chat Server on Rank {rank}")
        print(f"Total Processes: {size}")
        print("==========================================")
        server = Server(transport)
        try:
            server.start()
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
            sys.exit(0)
    else:
        user_id = f"user_{rank}_{uuid.uuid4().hex[:4]}"
        
        client = ChatClient(transport, user_id)
        try:
            client.login()
            client.start_input_loop()
        except KeyboardInterrupt:
            print("\n[Client] Exiting...")
            sys.exit(0)

if __name__ == "__main__":
    main()
