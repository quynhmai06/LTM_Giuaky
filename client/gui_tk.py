import socket, threading, tkinter as tk
import json
from tkinter import ttk, messagebox
from common.protocol_def import send, ENC

# giá trị mặc định (có thể chỉnh ở màn Start)
HOST, PORT = "127.0.0.1", 50007

PRIMARY  = "#2563eb"    # X
ERR_RED  = "#dc2626"    # O
HILIGHT  = "#fde68a"    # vàng nhạt highlight thắng
INK      = "#0f172a"; MUTED="#64748b"; BG="#f8fafc"; CARD="#ffffff"; OK_GREEN="#16a34a"


class StartDialog(tk.Toplevel):
    """Hộp thoại khởi động: nhập server, port, name, mode & room"""
    def __init__(self, master):
        super().__init__(master)
        self.title("Start Game"); self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self.host=tk.StringVar(value=HOST); self.port=tk.IntVar(value=PORT)
        self.name=tk.StringVar(value="Player")
        self.room=tk.StringVar(value="phong1")
        self.N=tk.IntVar(value=10); self.K=tk.IntVar(value=5)
        self.mode=tk.StringVar(value="pvp")  # pvp / bot
        self.action=tk.StringVar(value="create") # create / join (chỉ pvp)

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        frm=ttk.Frame(self,padding=12); frm.grid(row=0,column=0,sticky="nsew")
        self.columnconfigure(0,weight=1); self.rowconfigure(0,weight=1)

        def L(t): return ttk.Label(frm,text=t)

        L("Server:").grid(row=0,column=0,sticky="e",padx=6,pady=4)
        ttk.Entry(frm,textvariable=self.host,width=18).grid(row=0,column=1,sticky="w")
        L("Port:").grid(row=0,column=2,sticky="e",padx=6)
        ttk.Entry(frm,textvariable=self.port,width=8).grid(row=0,column=3,sticky="w")

        L("Tên:").grid(row=1,column=0,sticky="e",padx=6,pady=4)
        ttk.Entry(frm,textvariable=self.name,width=18).grid(row=1,column=1,sticky="w")

        L("Phòng:").grid(row=1,column=2,sticky="e",padx=6)
        ttk.Entry(frm,textvariable=self.room,width=12).grid(row=1,column=3,sticky="w")

        L("Kích thước N:").grid(row=2,column=0,sticky="e",padx=6,pady=4)
        ttk.Spinbox(frm,from_=3,to=25,textvariable=self.N,width=6).grid(row=2,column=1,sticky="w")
        L("Thắng K:").grid(row=2,column=2,sticky="e",padx=6)
        ttk.Spinbox(frm,from_=3,to=10,textvariable=self.K,width=6).grid(row=2,column=3,sticky="w")

        # mode
        modef=ttk.LabelFrame(frm,text="Chế độ"); modef.grid(row=3,column=0,columnspan=4,sticky="ew",pady=(8,4))
        ttk.Radiobutton(modef,text="PvP (2 người)",variable=self.mode,value="pvp",
                        command=self._update_mode).grid(row=0,column=0,sticky="w",padx=6,pady=2)
        ttk.Radiobutton(modef,text="Đánh với BOT",variable=self.mode,value="bot",
                        command=self._update_mode).grid(row=0,column=1,sticky="w",padx=6,pady=2)

        # action (create/join) chỉ PvP
        actf=ttk.LabelFrame(frm,text="Hành động (PvP)"); actf.grid(row=4,column=0,columnspan=4,sticky="ew",pady=(4,8))
        ttk.Radiobutton(actf,text="Tạo phòng",variable=self.action,value="create").grid(row=0,column=0,sticky="w",padx=6,pady=2)
        ttk.Radiobutton(actf,text="Join phòng",variable=self.action,value="join").grid(row=0,column=1,sticky="w",padx=6,pady=2)

        btns=ttk.Frame(frm); btns.grid(row=5,column=0,columnspan=4,sticky="e",pady=(4,0))
        ttk.Button(btns,text="OK",command=self._on_ok).pack(side="right",padx=(4,0))
        ttk.Button(btns,text="Cancel",command=self._on_close).pack(side="right")

        self._update_mode()

    def _update_mode(self):
        # hiện tại chưa cần disable radio, để người dùng chọn cho dễ
        pass

    def _on_ok(self):
        if not self.name.get().strip():
            messagebox.showerror("Lỗi","Tên không được rỗng",parent=self); return
        if not self.room.get().strip():
            messagebox.showerror("Lỗi","Phòng không được rỗng",parent=self); return
        try:
            int(self.port.get())
        except Exception:
            messagebox.showerror("Lỗi","Port phải là số",parent=self); return
        self.destroy()

    def _on_close(self):
        self.master.destroy()

class App(tk.Tk):
    def handle_msg(self, m):
        t = m.get("type")
        if t == "state":
            self.N, self.K = int(m.get("N", self.N)), int(m.get("K", self.K))
            if len(self.btns) != self.N * self.N:
                self.rebuild_board(self.N)

            self.board = m["board"]
            self.turn.set(m.get("turn", "-"))
            self.winline = m.get("winline", []) or []
            winner = (m.get("winner") or "")

            # cập nhật tỉ số nếu server gửi
            score = m.get("score")
            if isinstance(score, dict):
                self.score = {**{"X": 0, "O": 0, "D": 0}, **score}
                self.score_label.configure(
                    text=f"Tỉ số: X {self.score['X']} - {self.score['O']} O (Hòa: {self.score['D']})"
                )

            # kẻ & highlight
            winset = set(self.winline)
            for i in range(self.N * self.N):
                val = self.board[i]
                self._paint_cell(i, val, i in winset)

            # trạng thái
            self.turn_badge.configure(text=f"Lượt: {self.turn.get()}", style="Badge.TLabel")
            if winner == "D":
                self.res_badge.configure(text="Kết quả: Hòa", style="BadgeOK.TLabel")
            elif winner in ("X", "O"):
                self.res_badge.configure(text=f"Kết quả: {winner} thắng", style="BadgeOK.TLabel")
            else:
                self.res_badge.configure(text="Kết quả: ...", style="Badge.TLabel")

            # Cho phép bấm ô nếu chưa hết ván; server vẫn kiểm tra lượt
            if winner:
                for i in range(self.N * self.N):
                    self.btns[i]["state"] = "disabled"
            else:
                for i in range(self.N * self.N):
                    self.btns[i]["state"] = "normal" if (self.board[i] is None) else "disabled"

        elif t=="ok":
            self.chat_push(f"OK: {m.get('msg','')}")
        elif t=="error":
            items=m.get("rooms")
            if items:
                self.chat_push("ERROR: "+m.get("error",""))
                self.chat_push("Phòng hiện có: "+", ".join(f"{it['id']}({it['n']})" for it in items))
            else:
                self.chat_push(f"ERROR: {m.get('error','')}")
        elif t=="chat":
            self.chat_push(f"[{m.get('ts','')}] {m.get('from','?')}: {m.get('text','')}")
        elif t=="hello":
            self.chat_push(m.get("msg",""))

    def chat_push(self, line):
        self.chatbox.configure(state="normal")
        self.chatbox.insert("end", line+"\n")
        self.chatbox.configure(state="disabled")
        self.chatbox.see("end")


if __name__=="__main__":
    App().mainloop()