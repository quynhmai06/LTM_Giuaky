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
