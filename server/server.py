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
    if all(x is not None     for x in board): return "D", []
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