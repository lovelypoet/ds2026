import subprocess
import sys
import os
import shutil
import platform

def get_mpi_executable():
    """Find mpicc/mpiexec executable"""
    # Windows default
    if os.name == 'nt':
        msmpi_path = r"C:\Program Files\Microsoft MPI\Bin\mpiexec.exe"
        if os.path.exists(msmpi_path):
            return msmpi_path
        # Fallback to PATH
        return shutil.which("mpiexec")
    else:
        # Linux/Mac
        return shutil.which("mpiexec") or shutil.which("mpirun")

def get_linux_terminal_cmd():
    """Find available terminal emulator and return start command prefix"""
    terminals = [
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("xfce4-terminal", ["xfce4-terminal", "-x"]),
        ("konsole", ["konsole", "-e"]),
        ("xterm", ["xterm", "-hold", "-e"]),
        ("terminator", ["terminator", "-x"])
    ]
    for term, cmd in terminals:
        if shutil.which(term):
            return cmd
    return None

def main():
    n = 3
    if len(sys.argv) > 1:
        n = sys.argv[1]

    mpi_exe = get_mpi_executable()
    if not mpi_exe:
        print("Error: 'mpiexec' not found. Please install MPI runtime.")
        if os.name == 'nt':
            print("Download MS-MPI from Microsoft.")
        else:
            print("Run: sudo apt install openmpi-bin python3-mpi4py")
        return

    # Construct command
    cmd = []
    
    if os.name == 'nt':
        # Windows: Use cmd /c start
        cmd = [
            mpi_exe, 
            "-n", str(n), 
            "cmd", "/c", "start", "/WAIT", "MPI Chat",
            "python", "-m", "MPI_communicator.main"
        ]
    else:
        # Linux: Use terminal emulator
        term_cmd = get_linux_terminal_cmd()
        python_cmd = [sys.executable, "-m", "MPI_communicator.main"]
        
        # Check if running as root
        mpi_args = ["-n", str(n)]
        if hasattr(os, "getuid") and os.getuid() == 0:
            print("Running as root detected. Adding --allow-run-as-root.")
            mpi_args.append("--allow-run-as-root")
        
        if term_cmd:
            # Launch separate windows
            cmd = [mpi_exe] + mpi_args + term_cmd + python_cmd
        else:
            print("Warning: No suitable terminal emulator found (gnome-terminal, xterm, etc).")
            print("Processes will share this terminal (might be messy).")
            cmd = [mpi_exe] + mpi_args + python_cmd

    print(f"Launching {n} processes...")
    print(f"Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
