import json

ENC = "utf-8"
DELIM = "\n"

def pack(obj) -> bytes:
    """Encode JSON object to bytes with trailing newline."""
    return (json.dumps(obj, ensure_ascii=False) + DELIM).encode(ENC)

def unpack_lines(buffer: str):
    """
    Generator: tách các JSON theo newline trong buffer string.
    Trả về (obj, remaining_buffer).
    """
    while True:
        idx = buffer.find(DELIM)
        if idx == -1:
            break
        raw = buffer[:idx]
        buffer = buffer[idx+len(DELIM):]
        if raw.strip():
            yield json.loads(raw), buffer

def send(sock, obj):
    sock.sendall(pack(obj))
