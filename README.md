# Multiplayer Tic Tac Toe Game

A simple multiplayer Tic Tac Toe game built in Python, featuring a client-server architecture.

## 📦 Requirements
Make sure you have Python 3 installed and `pyinstaller` available.

```bash
pip install pyinstaller
```

## 🧩 Building the Client Executable

To create a standalone client executable:

1. Navigate to the project directory:
   ```bash
   cd path/to/project
   ```
2. Run the following command:
   ```bash
   pyinstaller --onefile --noconsole client.py --name TicTacToeClient
   ```
3. After successful compilation, the executable will be available at:
   ```
   dist/TicTacToeClient.exe
   ```

## 🖥️ Running the Server

One player must host the game by running the server:

```bash
python server.py
```

## 🌐 Network Configuration

To allow remote players to connect:

- Configure your **firewall** to allow inbound TCP traffic on the specified port.
- If playing over the internet, set up **port forwarding** on your **router** to forward external traffic to your host machine.
