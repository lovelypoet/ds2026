### Install Microsoft MPI
Run the following commands in **PowerShell** (Administrator recommended):

```powershell
# 1. Install the Runtime
winget install -e --id Microsoft.msmpi

# 2. Install the SDK
winget install -e --id Microsoft.msmpisdk
```

**IMPORTANT**: After installation, **Restart your Terminal** (close and reopen) to ensure `mpiexec` is added to your PATH.

### Install Python Dependencies
```bash
pip install mpi4py
```

## 2. How to Run

### Method A: The Easy Way (Launcher)
We provided a Python launcher that finds `mpiexec` for you automatically.

```powershell
# Default (1 Server + 2 Clients)
python launcher.py

# Custom number of clients (e.g., 4 processes)
python launcher.py 4
```

### Method B: The Standard Way (Manual)
If you have `mpiexec` in your PATH:

```powershell
# Run with 3 processes (Rank 0=Server, Rank 1,2=Clients)
mpiexec -n 3 python -m MPI_communicator.main
```

---

## 3. How to Use
- **Server (Rank 0)**: Runs in the background, logging activity.
- **Clients**: You will see a prompt `You:`.
    - Type a message and hit **Enter** to broadcast.
    - Type `/users` to see who is online.
    - Type `/dm <rank> <message>` to whisper.
    - Type `/quit` to leave.

## 4. Multi-Machine Setup
To run across multiple computers:
1. Install MS-MPI on all machines.
2. Ensure source code is identical on all machines.
3. Run:
   ```powershell
   mpiexec -hosts 2 <IP_A> <IP_B> -n 2 python -m MPI_communicator.main
   ```
