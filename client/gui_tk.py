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
    def __init__(self):
        super().__init__()
        self.title("Caro Socket • GUI"); self.geometry("980x680"); self.configure(bg=BG); self.minsize(860,560)

        # sẽ nhận từ StartDialog
        self.host=HOST; self.port=PORT
        self.sock=None; self.buf=""
        self.my_name=tk.StringVar(value="Player")
        self.room   =tk.StringVar(value="phong1")
        self.sizeN  =tk.IntVar(value=10)
        self.winK   =tk.IntVar(value=5)
        self.turn   =tk.StringVar(value="-")
        self.N=10; self.K=5
        self.board=[]; self.btns=[]
        self.winline=[]
        self.score = {"X": 0, "O": 0, "D": 0}

        self._init_style(); self._build_layout(); self.rebuild_board(self.N)
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(2, weight=1)

        # mở Start dialog
        self.after(100, self.start_dialog)

    # ---------- helpers ----------
    def _norm_room(self): return (self.room.get() or "").strip().lower()

    # ---------- Style ----------
    def _init_style(self):
        st=ttk.Style(); st.theme_use("clam")
        st.configure("Card.TFrame", background=CARD)
        st.configure("Header.TLabel", background=BG, foreground=INK, font=("Segoe UI",18,"bold"))
        st.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI",9))
        st.configure("Badge.TLabel", background="#e2e8f0", foreground=INK, font=("Segoe UI",10,"bold"), padding=(8,4))
        st.configure("BadgeOK.TLabel", background="#dcfce7", foreground=OK_GREEN)

    # ---------- UI ----------
    def _build_layout(self):
        hdr=ttk.Frame(self, style="Card.TFrame"); hdr.grid(row=0,column=0,sticky="ew",padx=12,pady=(12,8))
        ttk.Label(hdr, text="Caro Socket", style="Header.TLabel").pack(side="left")
        ttk.Label(hdr, text="Multi Client-Server (Tkinter)", style="Sub.TLabel").pack(side="left", padx=(10,0))

        ctrl=ttk.Frame(self, style="Card.TFrame"); ctrl.grid(row=1,column=0,sticky="ew",padx=12,pady=8,ipady=6)
        for i in range(12): ctrl.grid_columnconfigure(i,weight=0); ctrl.grid_columnconfigure(11,weight=1)
        def L(t): return ttk.Label(ctrl, text=t, background=CARD, foreground=INK)
        L("Tên:").grid(row=0,column=0,padx=(10,6)); ttk.Entry(ctrl,textvariable=self.my_name,width=16).grid(row=0,column=1)
        L("Phòng:").grid(row=0,column=2,padx=(14,6)); ttk.Entry(ctrl,textvariable=self.room,width=16).grid(row=0,column=3)
        L("N:").grid(row=0,column=4,padx=(14,6)); ttk.Spinbox(ctrl,from_=3,to=25,textvariable=self.sizeN,width=5).grid(row=0,column=5)
        L("K:").grid(row=0,column=6,padx=(10,6)); ttk.Spinbox(ctrl,from_=3,to=10,textvariable=self.winK,width=5).grid(row=0,column=7)
        ttk.Button(ctrl,text="Kết nối", command=self.connect_server).grid(row=0,column=8,padx=(16,6))
        ttk.Button(ctrl,text="Set name", command=self.set_name).grid(row=0,column=9,padx=4)
        ttk.Button(ctrl,text="Tạo phòng", command=self.create_room_pvp).grid(row=0,column=10,padx=4)
        ttk.Button(ctrl,text="Join phòng", command=self.join_room).grid(row=0,column=11,padx=4)

        # main area
        main=ttk.Frame(self, style="Card.TFrame"); main.grid(row=2,column=0,sticky="nsew",padx=12,pady=(8,12))
        main.grid_columnconfigure(0,weight=1); main.grid_columnconfigure(1,weight=1); main.grid_rowconfigure(0,weight=1)

        board_card=ttk.LabelFrame(main,text="Bàn cờ",padding=8); board_card.grid(row=0,column=0,sticky="nsew",padx=8,pady=8)
        board_card.grid_rowconfigure(0,weight=1); board_card.grid_columnconfigure(0,weight=1)
        self.canvas=tk.Canvas(board_card,highlightthickness=0,bg=BG); self.canvas.grid(row=0,column=0,sticky="nsew")
        self.board_frame=ttk.Frame(self.canvas); self.scroll=ttk.Scrollbar(board_card,orient="vertical",command=self.canvas.yview)
        self.scroll.grid(row=0,column=1,sticky="ns"); self.canvas.configure(yscrollcommand=self.scroll.set)

        self.canvas.create_window((0,0),window=self.board_frame,anchor="nw")
        self.board_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        btnbar=ttk.Frame(board_card); btnbar.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(6,0))
        ttk.Button(btnbar,text="Reset ván",command=self.reset_board).pack(side="left")
        ttk.Button(btnbar,text="Thoát phòng",command=self.leave_room).pack(side="left",padx=(6,0))

        # side: trạng thái + chat
        side=ttk.LabelFrame(main,text="Trạng thái & Chat",padding=8); side.grid(row=0,column=1,sticky="nsew",padx=8,pady=8)
        side.grid_columnconfigure(0,weight=1)
        row_badge=ttk.Frame(side); row_badge.grid(row=0,column=0,sticky="ew",pady=(0,8))
        self.turn_badge=ttk.Label(row_badge,text="Lượt: -",style="Badge.TLabel"); self.turn_badge.pack(side="left")
        self.res_badge =ttk.Label(row_badge,text="Kết quả: -",style="Badge.TLabel"); self.res_badge.pack(side="left",padx=8)

        # hiển thị tỉ số
        self.score_label = ttk.Label(side, text="Tỉ số: X 0 - 0 O (Hòa: 0)")
        self.score_label.grid(row=1, column=0, sticky="w", pady=(0, 6))

        chat_frame=ttk.Frame(side); chat_frame.grid(row=2,column=0,sticky="nsew"); side.grid_rowconfigure(2,weight=1)
        self.chatbox=tk.Text(chat_frame,height=16,bg="#f1f5f9",fg=INK,bd=0,highlightthickness=0,wrap="word")
        self.chatbox.configure(state="disabled"); self.chatbox.pack(fill="both",expand=True,padx=2,pady=2)

        entry=ttk.Frame(side); entry.grid(row=3,column=0,sticky="ew",pady=(6,0))
        self.msg_var=tk.StringVar(); e=ttk.Entry(entry,textvariable=self.msg_var); e.pack(side="left",fill="x",expand=True)
        e.bind("<Return>", lambda _ : self.send_chat()); ttk.Button(entry,text="Gửi",command=self.send_chat).pack(side="left",padx=(6,0))

    # ---------- Board ----------
    def rebuild_board(self, N):
        # clear
        for w in self.board_frame.winfo_children(): w.destroy()
        self.btns=[]; self.board=[None]*(N*N)
        for r in range(N):
            self.board_frame.grid_rowconfigure(r,weight=1)
            for c in range(N):
                self.board_frame.grid_columnconfigure(c,weight=1)
                idx=r*N+c
                btn=tk.Button(self.board_frame,text="",width=3,height=1,
                              font=("Segoe UI",14,"bold"),
                              bg=CARD,fg=INK,
                              command=lambda i=idx: self.click_cell(i))
                btn.grid(row=r,column=c,sticky="nsew",padx=1,pady=1)
                self.btns.append(btn)

    def _paint_cell(self, idx, val, in_win=False):
        btn=self.btns[idx]
        if val is None:
            btn.configure(text="",bg=CARD,fg=INK)
        else:
            color = PRIMARY if val=="X" else ERR_RED
            btn.configure(text=val, fg=color, bg=HILIGHT if in_win else CARD)

    # ---------- Networking ----------
    def start_dialog(self):
        dlg = StartDialog(self)
        self.wait_window(dlg)
        # lấy cấu hình
        self.host = dlg.host.get().strip() or "127.0.0.1"
        self.port = int(dlg.port.get() or 50007)
        self.my_name.set(dlg.name.get().strip() or "Player")
        self.room.set(dlg.room.get().strip() or "phong1")
        self.sizeN.set(int(dlg.N.get())); self.winK.set(int(dlg.K.get()))
        # auto connect
        self.connect_server()
        # auto create/join theo chế độ
        if dlg.mode.get()=="bot":
            self.create_room_bot()
        else:
            if dlg.action.get()=="create":
                self.create_room_pvp()
            else:
                self.join_room()

    def connect_server(self):
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock=None
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.connect((self.host,self.port))
        except Exception as e:
            messagebox.showerror("Lỗi",f"Kết nối thất bại: {e}",parent=self); return
        self.sock=s; self.buf=""
        threading.Thread(target=self.reader_loop,daemon=True).start()
        self.chat_push(f"Đã kết nối tới {self.host}:{self.port}")

        # gửi hello
        send(self.sock, {"type":"hello","name":self.my_name.get()})

    def reader_loop(self):
        try:
            while True:
                data = self.sock.recv(4096)
                if not data:
                    break
                self.buf += data.decode(ENC)

                # tách message theo '\n'
                while "\n" in self.buf:
                    line, self.buf = self.buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        m = json.loads(line)
                    except Exception as e:
                        print("parse error", e, line)
                        continue
                    self.after(0, self.handle_msg, m)
        except OSError:
            pass
        finally:
            self.after(0, lambda: self.chat_push("** Mất kết nối server **"))

    # ---------- Commands ----------
    def set_name(self):
        if not self.sock:
            messagebox.showwarning("Chưa kết nối","Hãy kết nối server trước"); return
        send(self.sock, {"type":"set_name","name":self.my_name.get()})

    def create_room_pvp(self):
        if not self.sock:
            messagebox.showwarning("Chưa kết nối","Hãy kết nối server trước"); return
        send(self.sock, {
            "type":"create_room",
            "room":self._norm_room(),
            "size":int(self.sizeN.get()),
            "win":int(self.winK.get()),
            "bot": False
        })

    def create_room_bot(self):
        if not self.sock:
            messagebox.showwarning("Chưa kết nối","Hãy kết nối server trước"); return
        send(self.sock, {
            "type":"create_room",
            "room":self._norm_room(),
            "size":int(self.sizeN.get()),
            "win":int(self.winK.get()),
            "bot": True
        })

    def join_room(self):
        if not self.sock:
            messagebox.showwarning("Chưa kết nối","Hãy kết nối server trước"); return
        send(self.sock, {"type":"join_room","room":self._norm_room()})

    def leave_room(self):
        if not self.sock: return
        send(self.sock, {"type":"leave"})

    def reset_board(self):
        if not self.sock: return
        send(self.sock, {"type":"reset"})

    def click_cell(self, idx):
        if not self.sock: return
        send(self.sock, {"type":"move","cell":idx})

    def send_chat(self):
        if not self.sock: return
        t=self.msg_var.get().strip()
        if not t: return
        send(self.sock, {"type":"chat","text":t})
        self.msg_var.set("")

    # ---------- Message handling ----------
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
