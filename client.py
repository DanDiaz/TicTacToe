# client.py
import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox

SERVER_HOST = "127.0.0.1"  # change to host IP when connecting over network
SERVER_PORT = 5182

def send_json(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))

class TicTacToeClient:
    def __init__(self, master):
        self.master = master
        master.title("TicTacToe Client")
        self.sock = None
        self.symbol = None
        self.turn = None
        self.board = [None]*9
        self.connected = False

        self.topfrm = tk.Frame(master)
        self.topfrm.pack(pady=5)
        tk.Label(self.topfrm, text="Server IP:").pack(side="left")
        self.host_entry = tk.Entry(self.topfrm)
        self.host_entry.insert(0, SERVER_HOST)
        self.host_entry.pack(side="left", padx=5)
        tk.Label(self.topfrm, text="Port:").pack(side="left")
        self.port_entry = tk.Entry(self.topfrm, width=6)
        self.port_entry.insert(0, str(SERVER_PORT))
        self.port_entry.pack(side="left")
        tk.Button(self.topfrm, text="Connect", command=self.connect).pack(side="left", padx=5)

        self.board_frame = tk.Frame(master)
        self.board_frame.pack()
        self.buttons = []
        for i in range(9):
            btn = tk.Button(self.board_frame, text="", width=6, height=3, font=("Helvetica", 20),
                            command=lambda i=i: self.on_click(i))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
            self.buttons.append(btn)

        self.status = tk.Label(master, text="Not connected")
        self.status.pack(pady=5)

    def connect(self):
        host = self.host_entry.get().strip()
        port = int(self.port_entry.get().strip())
        name = simpledialog.askstring("Name", "Enter your name:", parent=self.master) or "Player"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
        except Exception as e:
            messagebox.showerror("Connection failed", str(e))
            return
        self.sock = sock
        self.connected = True
        send_json(self.sock, {"type":"join","name":name})
        self.status.configure(text="Connected — waiting for messages...")
        threading.Thread(target=self.listen_thread, daemon=True).start()

    def listen_thread(self):
        buf = b""
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n",1)
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except Exception:
                        continue
                    self.handle_msg(msg)
        except Exception as e:
            print("listen error", e)
        finally:
            self.connected = False
            self.status.configure(text="Disconnected")
            try:
                self.sock.close()
            except:
                pass

    def handle_msg(self, msg):
        t = msg.get("type")
        if t == "waiting":
            self.status.configure(text=msg.get("msg","Waiting"))
        elif t == "start":
            # players and symbols available
            # our symbol is found by comparing socket? server tells both their symbols via separate join responses, but here we deduce by listening for "start" and previous join assigned
            # We'll rely on server that earlier join set our symbol via separate message isn't implemented; so server includes symbols list only.
            # To keep simple: server already sent us our symbol on join (it doesn't currently). So we'll check inside players list: assume first name equals local name? We didn't store name locally; but we did send it.
            # Simpler: server broadcast start but didn't tell clients their own symbol, but server previously sent waiting then no personal symbol. To make it reliable, server assigns symbol and we pick it from players list by socket identity — it's on server side only.
            # Workaround: server sends "start" with turn and board; then clients will be assigned symbol from the "symbols" list by position: first player that joined is X, second is O.
            # But client needs to know whether it's X or O — server doesn't tell who is who by name. So server is updated to include "your_symbol" if needed.
            pass

        elif t == "move":
            self.board = msg.get("board", self.board)
            self.turn = msg.get("turn", self.turn)
            self.update_buttons()
            self.status.configure(text=f"Turn: {self.turn}")
        elif t == "game_over":
            self.board = msg.get("board", self.board)
            self.update_buttons()
            winner = msg.get("winner")
            if winner == "draw":
                messagebox.showinfo("Game Over", "It's a draw!")
            else:
                messagebox.showinfo("Game Over", f"{winner} wins!")
            self.status.configure(text="Game over")
        elif t == "error":
            messagebox.showerror("Error", msg.get("msg",""))
        elif t == "end":
            reason = msg.get("reason","")
            messagebox.showinfo("Game ended", f"Game ended: {reason}")
            self.status.configure(text="Ended")
        elif t == "assign":
            # server tells us our symbol and full board & turn
            self.symbol = msg.get("symbol")
            self.turn = msg.get("turn")
            self.board = msg.get("board", self.board)
            self.update_buttons()
            self.status.configure(text=f"You are {self.symbol}. Turn: {self.turn}")
        elif t == "start":
            # fallback: if server provides board and turn
            self.board = msg.get("board", self.board)
            self.turn = msg.get("turn", self.turn)
            self.update_buttons()
            self.status.configure(text=f"Game started. Turn: {self.turn}")

    def on_click(self, idx):
        if not self.connected:
            return
        if self.symbol is None:
            # we don't know our symbol yet but allow sending - server will reject if not our turn
            pass
        # attempt to send move
        send_json(self.sock, {"type":"move","pos": idx})

    def update_buttons(self):
        for i in range(9):
            val = self.board[i]
            self.buttons[i].configure(text=(val if val else ""))


if __name__ == "__main__":
    root = tk.Tk()
    app = TicTacToeClient(root)
    root.mainloop()
