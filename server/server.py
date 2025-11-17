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