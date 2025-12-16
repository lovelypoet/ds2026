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

## 4. Multi-Machine Setup (Running across devices)

MPI works by having **ONE Controller Machine** launch processes on **ALL** machines remotesly. You NEVER run the python script on every machine manually.

### Core Concept: The "Controller" Model
- **Controller (Rank 0)**: This is the ONLY machine where you type the command. It knows the IPs of everyone else.
- **Workers (Rank 1, 2...)**: These machines just sit idle running a listener service. They wait for the Controller to "push" the app to them.

### Prerequisites (For ALL Machines)
1.  **Same Source Code**: The project folder `MPI_communicator` must exist at the **EXACT SAME PATH** on all machines (e.g., `C:\MPI_Chat` or `/home/user/mpi_chat`).
2.  **Network**: All machines must be on the same LAN or VPN (able to ping each other).
3.  **Firewall**: 
    - **Windows**: Allow `mpiexec`, `smpd`, `python`.
    - **Linux**: Allow `ssh` (Port 22).

---

### Scenario A: Windows Cluster (e.g., 3 Laptops)
Windows uses the **SMPD** service to listen for connections.

**Step 1: Start Listener (On Machine 1, 2, and 3)**
Open CMD as Admin and run:
```cmd
smpd -d
```
*(Leave this running. It waits for commands).*

**Step 2: Launch App (On Machine 1 ONLY)**
Assuming IPs: `192.168.1.10` (M1), `192.168.1.11` (M2), `192.168.1.12` (M3).
```cmd
mpiexec -hosts 3 192.168.1.10 192.168.1.11 192.168.1.12 -n 3 cmd /c start "MPI Chat" python -m MPI_communicator.main
```
*   **Machine 1** becomes Rank 0 (Server).
*   **Machine 2** becomes Rank 1.
*   **Machine 3** becomes Rank 2.

---

### Scenario B: Linux Cluster (e.g., 3 VMs / Ubuntu)
Linux uses **SSH** instead of SMPD.

**Step 1: Setup SSH (On All Machines)**
Install SSH Server:
```bash
sudo apt install openssh-server -y
sudo service ssh start
```

**Step 2: Password-less Access (On Controller Only)**
The Controller must be able to SSH into others without a password.
```bash
# On Controller (Machine 1)
ssh-keygen -t rsa  # Press Enter for all
ssh-copy-id user@192.168.1.11
ssh-copy-id user@192.168.1.12
```

**Step 3: Launch App (On Controller Only)**
```bash
mpiexec -host 192.168.1.10,192.168.1.11,192.168.1.12 -n 3 xterm -e python3 -m MPI_communicator.main
```

---

### Scenario C: Mixed OS (Windows + Linux)
**Not Recommended directly.**
MPI protocols on Windows and Linux are often incompatible.
*   **Best Fix**: Use **WSL** on your Windows machine. Install `openmpi-bin` inside WSL. Now treat it exactly like **Scenario B (Linux Cluster)**.
