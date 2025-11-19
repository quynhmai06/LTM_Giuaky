import os, json, socket, threading, random, traceback
from datetime import datetime
from common.protocol_def import send, ENC

HOST, PORT = "0.0.0.0", 50007

clients = {}  # sock -> {"name": str}
rooms   = {}

def now(): return datetime.now().strftime("%H:%M:%S")
def ts_filename(): return datetime.now().strftime("%Y%m%d_%H%M%S")
def other(m): return "O" if m=="X" else "X"
def log(*a): print(f"[{now()}]", *a, flush=True)

def ensure_room(room_id, N=10, K=5, bot=False):
    if room_id not in rooms:
        rooms[room_id] = {
            "players": [],
            "board": [None] * (N * N),
            "N": N,
            "K": K,
            "turn": "X",
            "winner": None,
            "winline": [],
            "bot": bool(bot),
            # Tỉ số theo room
            "score": {"X": 0, "O": 0, "D": 0},
            "log": {
                "meta": {
                    "room": room_id,
                    "N": N,
                    "K": K,
                    "created": now(),
                    "bot": bool(bot),
                },
                "moves": [],
            },
        }
        os.makedirs("logs", exist_ok=True)
        log(f"ROOM create '{room_id}' (N={N},K={K}, bot={bot})")

def room_of(sock):
    for rid, r in rooms.items():
        for p in r["players"]:
            if p["sock"] is sock: return rid, r
    return None, None

def broadcast_room(room_id, payload):
    r = rooms.get(room_id)
    if not r: return
    for p in r["players"]:
        if not p["sock"]:
            continue
        per = dict(payload)
        per["your_mark"] = p["mark"]
        try: send(p["sock"], per)
        except: pass

def next_mark(r):
    used = [p["mark"] for p in r["players"]]
    if "X" not in used: return "X"
    if "O" not in used: return "O"
    return None

def push_state(room_id):
    r = rooms[room_id]
    payload = {
        "type": "state",
        "room": room_id,
        "board": r["board"],
        "turn": r["turn"],
        "winner": r["winner"] or "",
        "N": r["N"],
        "K": r["K"],
        "players": [{"name": p["name"], "mark": p["mark"]} for p in r["players"]],
        "winline": r.get("winline", []),
        # gửi luôn tỉ số cho client
        "score": r.get("score", {"X": 0, "O": 0, "D": 0}),
    }
    broadcast_room(room_id, payload)

# ---- Winner K in N×N + trả về đường thắng ----
def compute_winner_with_line(board, N, K):
    def at(i,j):
        if 0<=i<N and 0<=j<N: return board[i*N+j]
        return None
    dirs = [(1,0),(0,1),(1,1),(1,-1)]
    for i in range(N):
        for j in range(N):
            first = at(i,j)
            if not first: continue
            for di,dj in dirs:
                cells = [i*N+j]
                ok=True
                for step in range(1,K):
                    if at(i+di*step, j+dj*step)==first:
                        cells.append((i+di*step)*N + (j+dj*step))
                    else:
                        ok=False; break
                if ok: return first, cells
    if all(x is not None for x in board): return "D", []
    return None, []

def reset_room(room_id, N=None, K=None):
    r = rooms[room_id]
    if N:
        r["N"] = N
    if K:
        r["K"] = K
    r["board"] = [None] * (r["N"] * r["N"])
    r["turn"] = "X"
    r["winner"] = None
    r["winline"] = []
    # KHÔNG reset score, chỉ reset log
    r["log"] = {
        "meta": {
            "room": room_id,
            "N": r["N"],
            "K": r["K"],
            "created": now(),
            "bot": r.get("bot", False),
        },
        "moves": [],
    }
    log(f"ROOM reset '{room_id}' -> N={r['N']},K={r['K']}")
    push_state(room_id)

def join_room(sock, name, room_id):
    r = rooms[room_id]
    mark = next_mark(r)
    if mark is None: return False, "Room full"
    r["players"].append({"sock":sock,"name":name or "Guest","mark":mark})
    log(f"ROOM join '{room_id}': {name or 'Guest'} as {mark}")
    push_state(room_id)
    return True, "Joined"

def leave_current(sock):
    rid, r = room_of(sock)
    if not r: return
    left=None
    r["players"] = [p for p in r["players"] if not ((p["sock"] is sock) and (left:=p["name"]))]
    if left: log(f"ROOM leave '{rid}': {left}")
    if not r["players"]:
        rooms.pop(rid, None); log(f"ROOM remove '{rid}' (empty)")
    else:
        push_state(rid)

# ---- BOT ----
def bot_move(room_id):
    r = rooms[room_id]
    if not r.get("bot"):
        return
    bot = next((p for p in r["players"] if p["name"] == "BOT"), None)
    if not bot or r["winner"] or r["turn"] != bot["mark"]:
        return

    empties = [i for i, v in enumerate(r["board"]) if v is None]
    if not empties:
        return
    N = r["N"]
    center = (N * N) // 2
    cell = center if center in empties else random.choice(empties)

    r["board"][cell] = bot["mark"]
    r["log"]["moves"].append({"ts": now(), "player": "BOT", "mark": bot["mark"], "cell": cell})
    win, line = compute_winner_with_line(r["board"], r["N"], r["K"])
    r["winner"], r["winline"] = win, line

    if r["winner"]:
        if win in ("X", "O", "D"):
            r.setdefault("score", {"X": 0, "O": 0, "D": 0})
            r["score"][win] += 1
        push_state(room_id)
        persist_log(room_id)
    else:
        r["turn"] = other(bot["mark"])
        push_state(room_id)

def persist_log(room_id):
    r = rooms[room_id]
    try:
        fname = os.path.join("logs", f"{room_id}_{ts_filename()}.json")
        with open(fname, "w", encoding="utf-8") as f:
            data = r["log"] | {
                "result": {
                    "winner": r["winner"],
                    "winline": r.get("winline", []),
                },
                "score": r.get("score", {"X": 0, "O": 0, "D": 0}),
            }
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"LOG saved {fname}")
    except Exception as e:
        log("LOG error:", e)

# ---- Vòng lặp nhận dữ liệu: tách theo '\n' ----
def handle(sock, addr):
    clients[sock] = {"name": None}
    log("NEW conn", addr)
    send(sock, {"type":"hello","msg":f"Xin chào từ server! {addr}"})
    buf=""
    try:
        while True:
            data = sock.recv(4096)
            if not data: break
            buf += data.decode(ENC)
            while "\n" in buf:
                line, buf = buf.split("\n",1)
                line=line.strip()
                if not line:
                    continue
                try:
                    m=json.loads(line)
                except Exception as e:
                    log("JSON parse error", e, line)
                    continue
                try:
                    log("RECV", addr, m)
                    process(sock, m)
                except Exception as e:
                    log("ERROR in process:", e)
                    traceback.print_exc()
                    try: send(sock, {"type":"error","error":f"Server exception: {e}"})
                    except: pass
    finally:
        leave_current(sock)
        clients.pop(sock, None)
        try: sock.close()
        except: pass
        log("CLOSE", addr)

# ---- Xử lý message ----
def process(sock, m):
    t = m.get("type")

    if t=="set_name":
        clients[sock]["name"] = (m.get("name") or "Guest").strip()
        send(sock, {"type":"ok","msg":"name set"})

    elif t=="list_rooms":
        items=[{"id":rid,"n":len(r["players"]),"N":r["N"],"K":r["K"],"bot":r.get("bot",False)}
               for rid,r in rooms.items()]
        send(sock, {"type":"rooms","items":items})

    elif t=="create_room":
        rid = (m.get("room") or "room").strip().lower()
        N   = int(m.get("size",10) or 10)
        K   = int(m.get("win",5) or 5)
        bot = bool(m.get("bot", False))
        ensure_room(rid, N, K, bot)
        ok,_ = join_room(sock, clients[sock]["name"], rid)
        if bot:
            r = rooms[rid]
            mark = next_mark(r)
            if mark:
                r["players"].append({"sock":None,"name":"BOT","mark":mark})
                log(f"ROOM bot attached '{rid}' as {mark}")
                push_state(rid)
        send(sock, {"type":"ok","msg":f"room {rid} created (N={N},K={K},bot={bot}); Joined"})

    elif t=="join_room":
        rid = (m.get("room") or "").strip().lower()
        if rid not in rooms:
            items=[{"id":r, "n":len(rooms[r]['players'])} for r in rooms.keys()]
            send(sock, {"type":"error","error":"Room not found","rooms":items})
            return
        ok,msg = join_room(sock, clients[sock]["name"], rid)
        if ok: send(sock, {"type":"ok","msg":msg})
        else:  send(sock, {"type":"error","error":msg})

    elif t=="leave":
        leave_current(sock); send(sock, {"type":"ok","msg":"left"})

    elif t=="reset":
        rid, r = room_of(sock)
        if not r: 
            send(sock, {"type":"error","error":"Not in room"}); return
        NN = int(m.get("size",0) or 0) or None
        KK = int(m.get("win",0)  or 0) or None
        reset_room(rid, NN, KK)

    elif t=="move":
        cell = int(m.get("cell", -1))
        rid, r = room_of(sock)
        if not r:
            send(sock, {"type": "error", "error": "Not in room"}); return
        if r["winner"]:
            send(sock, {"type": "error", "error": "Game over"}); return
        me = next(p for p in r["players"] if p["sock"] is sock)
        if r["turn"] != me["mark"]:
            send(sock, {"type": "error", "error": "Not your turn"}); return
        N = r["N"]
        if not (0 <= cell < N * N) or r["board"][cell] is not None:
            send(sock, {"type": "error", "error": "Invalid move"}); return

        r["board"][cell] = me["mark"]
        r["log"]["moves"].append({"ts": now(), "player": me["name"], "mark": me["mark"], "cell": cell})
        win, line = compute_winner_with_line(r["board"], r["N"], r["K"])
        r["winner"], r["winline"] = win, line

        if r["winner"]:
            if win in ("X", "O", "D"):
                r.setdefault("score", {"X": 0, "O": 0, "D": 0})
                r["score"][win] += 1
            push_state(rid)
            persist_log(rid)
        else:
            r["turn"] = other(me["mark"])
            push_state(rid)
            bot_move(rid)

    elif t=="chat":
        txt = (m.get("text") or "").strip()
        rid, r = room_of(sock)
        if r and txt:
            broadcast_room(rid, {"type":"chat","from": clients[sock]["name"] or "Guest","text":txt,"ts": now()})
    else:
        send(sock, {"type":"error","error":f"Unknown type {t}"})

def main():
    log(f"Server listening on {HOST}:{PORT}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT)); s.listen(100)
    try:
        while True:
            c, addr = s.accept()
            threading.Thread(target=handle, args=(c,addr), daemon=True).start()
    finally:
        s.close()

if __name__=="__main__":
    main()
