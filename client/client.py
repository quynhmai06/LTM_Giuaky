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