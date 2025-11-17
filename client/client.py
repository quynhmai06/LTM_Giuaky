import socket, json, threading, sys
from common.protocol_def import DELIM, ENC, send, unpack_lines
from client.ui import draw_board, help_text

HOST = "127.0.0.1"  # đổi sang IP máy server nếu chơi qua LAN
PORT = 50007

def recv_loop(sock):
    buf = ""
    while True:
        data = sock.recv(4096)
        if not data:
            print("Mất kết nối server.")
            sys.exit(0)
        buf += data.decode(ENC)
        for msg, buf in unpack_lines(buf):
            handle_msg(msg) 

def handle_msg(m):
    t = m.get("type")
    if t == "hello":
        print(m.get("msg"))
    elif t == "ok":
        print("OK:", m.get("msg"))
    elif t == "error":
        print("ERROR:", m.get("error"))
    elif t == "rooms":
        items = m.get("items", [])
        print("Rooms:", ", ".join([f"{r['id']}({r['n']})" for r in items]) or "(empty)")
    elif t == "state":
        print("\n==== ROOM:", m["room"], "====")
        print(draw_board(m["board"]))
        players = m.get("players", [])
        print("Players:", ", ".join([f"{p['name']}[{p['mark']}]" for p in players]) or "(waiting...)")
        if m["winner"] == "D":
            print("Kết quả: Hòa!")
        elif m["winner"] in ("X", "O"):
            print("Người thắng:", m["winner"])
        else:
            print("Lượt:", m["turn"])
    else:
        print("<<", m)

def main():
    print("Kết nối tới server...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        threading.Thread(target=recv_loop, args=(s,), daemon=True).start()
        print(help_text())
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nThoát.")
                break
            if not line:
                continue
            if line.startswith("/name "):
                _, name = line.split(" ", 1)
                send(s, {"type": "set_name", "name": name})
            elif line == "/rooms":
                send(s, {"type": "list_rooms"})
            elif line.startswith("/create "):
                _, room = line.split(" ", 1)
                send(s, {"type": "create_room", "room": room})
            elif line.startswith("/join "):
                _, room = line.split(" ", 1)
                send(s, {"type": "join_room", "room": room})
            elif line.startswith("/move ") or line.startswith("move "):
                try:
                    _, cell = line.split(" ", 1)
                    cell = int(cell)
                except Exception:
                    print("Cú pháp: /move <0..8>")
                    continue
                send(s, {"type": "move", "cell": cell})
            elif line == "/leave":
                send(s, {"type": "leave"})
            elif line == "/help":
                print(help_text())
            else:
                print("Lệnh không hợp lệ. Gõ /help.")

if __name__ == "__main__":
    main()
