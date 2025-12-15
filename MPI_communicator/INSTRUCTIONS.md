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
# Windows
pip install mpi4py

# Linux (Debian/Ubuntu)
sudo apt update
sudo apt install openmpi-bin python3-mpi4py python3-tk
# Note: 'python3-tk' might be needed if using strict UI libraries, 
# but for this CLI app, just openmpi + mpi4py is sufficient.
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
To run across multiple computers (e.g., Laptop A and Laptop B):

### 1. Verification (On ALL machines)
*   Install **MS-MPI** (SDK + Runtime).
*   Ensure the project folder is at the **exact same path** (e.g., `C:\ds2026_gp`).
*   Allow `python.exe`, `smpd.exe`, and `mpiexec.exe` through **Windows Firewall**.

### 2. Start Service (On ALL machines)
Run this in a separate terminal to listen for connections:
```powershell
smpd -d
# What: Starts the MPI background listener.
# Why: Required for machines to talk to each other.
```

### 3. Run the App (From the "Controller" machine)
The "Controller" is simply the machine where you type the `mpiexec` command. It can be the server or an unrelated node.

**Example: 3 Distinct Machines**
*   **Machine 1 (Server)**: `192.168.1.10`
*   **Machine 2 (Client A)**: `192.168.1.11`
*   **Machine 3 (Client B)**: `192.168.1.12`

Run this on Machine 1:
```powershell
mpiexec -hosts 3 192.168.1.10 192.168.1.11 192.168.1.12 -n 3 cmd /c start "MPI Chat" python -m MPI_communicator.main
```
**Explanation**:
*   `-hosts 3`: We are using 3 separate IPs.
*   The **first IP** becomes Rank 0 (Server).
*   The **second IP** becomes Rank 1 (Client A).
*   The **third IP** becomes Rank 2 (Client B).
*   `-n 3`: We are launching 3 processes total (one per IP).
