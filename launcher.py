import subprocess
import sys
import os

MSMPI_PATH = r"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe"

def main():
    n = 3
    if len(sys.argv) > 1:
        n = sys.argv[1]

    if not os.path.exists(MSMPI_PATH):
        print(f"Error: mpiexec not found at {MSMPI_PATH}")
        return

    # Use 'start /WAIT' to open separate windows and keep parent alive
    cmd = [
        MSMPI_PATH, 
        "-n", str(n), 
        "cmd", "/c", "start", "/WAIT", "MPI Chat",
        "python", "-m", "MPI_communicator.main"
    ]
    
    print(f"Launching {n} separate terminals...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
