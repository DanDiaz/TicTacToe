# server.py
import socket
import threading
import json

HOST = "0.0.0.0"   # listen on all interfaces
PORT = 5182

# Game state helpers
WIN_LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]

def check_winner(board):
    for a,b,c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board):
        return "draw"
    return None

# Helper to send JSON with newline terminator
def send_json(conn, obj):
    data = (json.dumps(obj) + "\n").encode("utf-8")
    conn.sendall(data)

class GameRoom:
    def __init__(self):
        self.lock = threading.Lock()
        self.players = []  # list of (conn, addr, name, symbol)
        self.board = [None]*9
        self.turn = None  # 'X' or 'O'
        self.finished = False

    def add_player(self, conn, addr, name):
        with self.lock:
            if len(self.players) >= 2:
                return False
            symbol = 'X' if not self.players else 'O'
            self.players.append((conn, addr, name, symbol))
            # Send assign to this new player so they know their symbol
            try:
                send_json(conn, {"type":"assign", "symbol": symbol, "board": self.board, "turn": self.turn})
            except Exception:
                pass
            if len(self.players) == 2:
                self.turn = 'X'
                self.broadcast({"type": "start",
                                "players": [p[2] for p in self.players],
                                "symbols": [p[3] for p in self.players],
                                "turn": self.turn,
                                "board": self.board})
            else:
                send_json(conn, {"type": "waiting", "msg": "Waiting for second player..."})
            return True


    def broadcast(self, obj):
        remove_list = []
        for conn, addr, name, symbol in list(self.players):
            try:
                send_json(conn, obj)
            except Exception:
                remove_list.append((conn,addr,name,symbol))
        for rem in remove_list:
            self.remove_player(rem[0])

    def remove_player(self, conn):
        with self.lock:
            self.players = [p for p in self.players if p[0] is not conn]
            # if someone disconnects, mark game finished
            self.finished = True
            self.broadcast({"type": "end", "reason": "player_disconnected"})

    def handle_move(self, conn, symbol, pos):
        with self.lock:
            if self.finished:
                send_json(conn, {"type":"error","msg":"game finished"})
                return
            if symbol != self.turn:
                send_json(conn, {"type":"error","msg":"not your turn"})
                return
            if not (0 <= pos <= 8) or self.board[pos] is not None:
                send_json(conn, {"type":"error","msg":"invalid move"})
                return
            self.board[pos] = symbol
            winner = check_winner(self.board)
            if winner:
                self.finished = True
                self.broadcast({"type":"game_over","winner": winner, "board": self.board})
                return
            # swap turn
            self.turn = 'O' if self.turn == 'X' else 'X'
            self.broadcast({"type":"move","pos":pos,"symbol":symbol,"turn":self.turn,"board":self.board})

room = GameRoom()

def client_thread(conn, addr):
    """
    Expect each line to be JSON messages terminated by newline.
    Basic messages:
    - {"type":"join","name":"Alice"}
    - {"type":"move","pos":4}
    """
    try:
        buf = b""
        player_symbol = None
        player_name = None
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n",1)
                try:
                    msg = json.loads(line.decode("utf-8"))
                except Exception:
                    send_json(conn, {"type":"error","msg":"invalid json"})
                    continue

                if msg.get("type") == "join":
                    name = msg.get("name","Anon")
                    ok = room.add_player(conn, addr, name)
                    player_name = name
                    # find symbol
                    for p in room.players:
                        if p[0] is conn:
                            player_symbol = p[3]
                            break
                    if not ok:
                        send_json(conn, {"type":"error","msg":"room full"})
                        conn.close()
                        return

                elif msg.get("type") == "move":
                    if player_symbol is None:
                        send_json(conn, {"type":"error","msg":"not joined"})
                        continue
                    pos = int(msg.get("pos", -1))
                    room.handle_move(conn, player_symbol, pos)
                else:
                    send_json(conn, {"type":"error","msg":"unknown type"})
    except Exception as e:
        print("Client thread error:", e)
    finally:
        try:
            room.remove_player(conn)
            conn.close()
        except:
            pass

def main():
    print(f"Starting TicTacToe server on port {PORT} ...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            print("Connection from", addr)
            threading.Thread(target=client_thread, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
