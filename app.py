"""
符籙便簽 v3.0 — 古风道家符纸风格桌面便签
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json, os, sys, math
from datetime import datetime
from pathlib import Path
import uuid

APP_NAME = "符籙便簽"
if sys.platform == "win32":
    DATA_DIR = Path(os.environ.get("APPDATA","~")) / "StickyNotes"
else:
    DATA_DIR = Path.home() / ".stickynotes"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "notes.json"

# ─── 古风色系 ────────────────────────────────────────────────────────────────
COLORS = {
    # 浅色系（符纸色）
    "paper":   {"bg":"#F5E6C8","toolbar":"#EDD98A","border":"#8B4513","text":"#1A0A00","placeholder":"#8B7355","name":"宣紙","swatch":"#EDD98A","dark":False},
    "crimson": {"bg":"#FAE8E0","toolbar":"#F2C4B0","border":"#8B1A1A","text":"#1A0A00","placeholder":"#8B6060","name":"硃砂","swatch":"#F2C4B0","dark":False},
    "celadon": {"bg":"#E8F0E8","toolbar":"#C8D8C0","border":"#2A4A2A","text":"#0A1A0A","placeholder":"#607060","name":"青瓷","swatch":"#C8D8C0","dark":False},
    "indigo":  {"bg":"#E4E8F0","toolbar":"#B8C4D8","border":"#1A2A4A","text":"#0A0A1A","placeholder":"#506070","name":"靛藍","swatch":"#B8C4D8","dark":False},
    # 深色系（暗色符纸）
    "vermil":  {"bg":"#2A0A0A","toolbar":"#3A1010","border":"#C0392B","text":"#F5E6C8","placeholder":"#AA8866","name":"硃紅","swatch":"#C0392B","dark":True},
    "inkblack":{"bg":"#0A0A08","toolbar":"#181810","border":"#4A4030","text":"#EDD98A","placeholder":"#806040","name":"墨黑","swatch":"#2A2818","dark":True},
    "darkgrn": {"bg":"#081A10","toolbar":"#102010","border":"#2A5A2A","text":"#C8E8C0","placeholder":"#507050","name":"墨綠","swatch":"#1A3A1A","dark":True},
    "midnight":{"bg":"#080818","toolbar":"#101828","border":"#2A3A6A","text":"#C0C8E8","placeholder":"#506080","name":"夜藍","swatch":"#181838","dark":True},
    "eggplant":{"bg":"#180A1A","toolbar":"#241228","border":"#5A2A6A","text":"#D8C0E0","placeholder":"#806090","name":"紫黑","swatch":"#2A1230","dark":True},
    "umber":   {"bg":"#1A0A04","toolbar":"#281408","border":"#6A2A0A","text":"#E8C8A0","placeholder":"#906040","name":"赭褐","swatch":"#3A1808","dark":True},
}
COLOR_KEYS = list(COLORS.keys())

# 面板主题（仿古宣纸）
PANEL = {
    "bg":"#F0DDB0","bg2":"#E8D0A0","border":"#8B4513",
    "text":"#1A0A00","text2":"#5A3A10","text3":"#8B7040",
    "danger":"#8B1A1A","success":"#2A5A1A","accent":"#C0392B",
}

# 符录装饰字符
TALISMANS_LEFT  = ["壽","福","吉","祿","禧","貴","財","旺"]
TALISMANS_RIGHT = ["辟","邪","鎮","宅","平","安","康","寧"]
TALISMAN_TOP    = "符籙鎮宅  吉祥如意  萬事大吉"
TALISMAN_CORNER = ["☰","☷","☵","☲"]  # 八卦四角

# ─── 数据层 ──────────────────────────────────────────────────────────────────
class NoteStore:
    def __init__(self):
        self._notes={}; self._cbs=[]; self.load()
    def load(self):
        try:
            if DATA_FILE.exists():
                self._notes={n["id"]:n for n in json.loads(DATA_FILE.read_text(encoding="utf-8"))}
        except Exception as e: print(f"Load error: {e}")
    def save(self):
        try: DATA_FILE.write_text(json.dumps(list(self._notes.values()),ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as e: print(f"Save error: {e}")
    def all(self): return list(self._notes.values())
    def get(self, nid): return self._notes.get(nid)
    def create(self, color="paper"):
        n={"id":str(uuid.uuid4()),"content":"","color":color,"pinned":False,"desktop_pinned":False,
           "created":datetime.now().isoformat(),"modified":datetime.now().isoformat(),
           "win_x":None,"win_y":None,"win_w":300,"win_h":360}
        self._notes[n["id"]]=n; self.save(); self._notify(); return n
    def update(self, nid, **kw):
        if nid not in self._notes: return
        self._notes[nid].update(kw); self._notes[nid]["modified"]=datetime.now().isoformat()
        self.save(); self._notify()
    def delete(self, nid):
        self._notes.pop(nid,None); self.save(); self._notify()
    def subscribe(self, cb): self._cbs.append(cb)
    def _notify(self):
        for cb in self._cbs:
            try: cb()
            except: pass

# ─── 符录绘制工具 ─────────────────────────────────────────────────────────────
def draw_talisman_border(canvas, w, h, color_key):
    """在 canvas 上绘制古风符录边框"""
    c = COLORS[color_key]
    ink   = c["text"]      # 主墨色
    cinnabar = c["border"] # 朱砂/边框色

    # 双层外框
    canvas.create_rectangle(2,2,w-2,h-2, outline=cinnabar, width=2)
    canvas.create_rectangle(6,6,w-6,h-6, outline=cinnabar, width=1)

    # 四角八卦符
    font_corner = get_font(9)
    corners = [(10,10),(w-10,10),(10,h-10),(w-10,h-10)]
    anchors = ["nw","ne","sw","se"]
    for (cx,cy),anc,sym in zip(corners, anchors, TALISMAN_CORNER):
        canvas.create_text(cx,cy, text=sym, font=font_corner,
                           fill=cinnabar, anchor=anc)

    # 顶部横幅文字
    canvas.create_line(14,18,w-14,18, fill=cinnabar, width=1)
    canvas.create_text(w//2, 13, text=TALISMAN_TOP,
                       font=get_font(7), fill=cinnabar, anchor="center")
    canvas.create_line(14,22,w-14,22, fill=cinnabar, width=1)

    # 底部横线
    canvas.create_line(14,h-22,w-14,h-22, fill=cinnabar, width=1)
    canvas.create_line(14,h-18,w-14,h-18, fill=cinnabar, width=1)

    # 左侧符文（竖排）
    n_syms = min(len(TALISMANS_LEFT), max(3, (h-80)//22))
    for i,sym in enumerate(TALISMANS_LEFT[:n_syms]):
        y = 32 + i * ((h-80)//n_syms)
        canvas.create_text(11, y, text=sym, font=get_font(9),
                           fill=cinnabar, anchor="center")

    # 右侧符文（竖排）
    for i,sym in enumerate(TALISMANS_RIGHT[:n_syms]):
        y = 32 + i * ((h-80)//n_syms)
        canvas.create_text(w-11, y, text=sym, font=get_font(9),
                           fill=cinnabar, anchor="center")

    # 竖线分隔符文与书写区
    canvas.create_line(18,26,18,h-24, fill=cinnabar, width=1, dash=(3,3))
    canvas.create_line(w-18,26,w-18,h-24, fill=cinnabar, width=1, dash=(3,3))

def get_font(size, weight="normal"):
    """根据平台选择合适的中文字体"""
    if sys.platform == "win32":
        faces = ["仿宋", "仿宋_GB2312", "华文仿宋", "楷体", "Microsoft YaHei"]
    else:
        faces = ["AR PL UMing CN", "WenQuanYi Micro Hei", "PingFang SC", "Noto Serif CJK SC"]
    return (faces[0], size, weight)

# ─── 悬浮球（圆形 + 繁体"吉"）────────────────────────────────────────────────
class FloatingBall:
    SIZE = 64
    EDGE_PEEK = 48

    def __init__(self, root, on_click):
        self.root=root; self.on_click=on_click
        self._hidden=False; self._anim_id=None
        self._hide_timer=None; self._dragged=False
        sw=root.winfo_screenwidth(); sh=root.winfo_screenheight()
        self._sw=sw; self._sh=sh

        self.win=tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost",True)
        self.win.attributes("-alpha",0.92)
        self.win.configure(bg="#8B4513")

        self._x=float(sw-self.SIZE-8)
        self._y=float(sh//2-self.SIZE//2)
        self.win.geometry(f"{self.SIZE}x{self.SIZE}+{int(self._x)}+{int(self._y)}")

        self.cv=tk.Canvas(self.win,width=self.SIZE,height=self.SIZE,
                          bg="#8B4513",highlightthickness=0,bd=0)
        self.cv.pack()
        self._draw_ball()

        self.cv.bind("<ButtonPress-1>",  self._press)
        self.cv.bind("<B1-Motion>",       self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<Enter>",lambda e:self._emerge())
        self.cv.bind("<Leave>",lambda e:self._sched_hide(2500))
        self._sched_hide(3500)

    def _draw_ball(self):
        s=self.SIZE; self.cv.delete("all")
        # 背景圆（朱砂红渐变感）
        self.cv.create_oval(1,1,s-1,s-1, fill="#8B1A1A", outline="#C0392B", width=2)
        # 内圈
        self.cv.create_oval(5,5,s-5,s-5, fill="#A52020", outline="#EDD98A", width=1)
        # 繁体"吉"字（大字）
        self.cv.create_text(s//2+1,s//2+1, text="吉", font=(get_font(24,"bold")[0],22,"bold"),
                            fill="#1A0A00", anchor="center")
        self.cv.create_text(s//2,s//2, text="吉", font=(get_font(24,"bold")[0],22,"bold"),
                            fill="#EDD98A", anchor="center")
        # 小字装饰（上下）
        self.cv.create_text(s//2, 6, text="符", font=get_font(7), fill="#AA9955", anchor="center")
        self.cv.create_text(s//2, s-6, text="籙", font=get_font(7), fill="#AA9955", anchor="center")

    def _press(self,e):
        self._emerge()
        if self._hide_timer: self.win.after_cancel(self._hide_timer); self._hide_timer=None
        self._ox=e.x_root-int(self._x); self._oy=e.y_root-int(self._y)
        self._sx=e.x_root; self._sy=e.y_root; self._dragged=False

    def _drag(self,e):
        if abs(e.x_root-self._sx)>5 or abs(e.y_root-self._sy)>5: self._dragged=True
        if self._dragged:
            self._x=max(0.0,min(float(e.x_root-self._ox),float(self._sw-self.SIZE)))
            self._y=max(0.0,min(float(e.y_root-self._oy),float(self._sh-self.SIZE)))
            self.win.geometry(f"+{int(self._x)}+{int(self._y)}")

    def _release(self,e):
        if not self._dragged: self.on_click()
        else: self._snap()
        self._sched_hide(2500)

    def _snap(self):
        tx=0.0 if (self._x+self.SIZE/2)<self._sw/2 else float(self._sw-self.SIZE)
        self._anim(tx,self._y)

    def _anim(self,tx,ty,steps=12):
        if self._anim_id: self.win.after_cancel(self._anim_id)
        dx=(tx-self._x)/steps; dy=(ty-self._y)/steps
        def step(n):
            if n<=0: self._x,self._y=tx,ty; self.win.geometry(f"+{int(tx)}+{int(ty)}"); return
            self._x+=dx; self._y+=dy; self.win.geometry(f"+{int(self._x)}+{int(self._y)}")
            self._anim_id=self.win.after(16,lambda:step(n-1))
        step(steps)

    def _sched_hide(self,delay=2000):
        if self._hide_timer: self.win.after_cancel(self._hide_timer)
        self._hide_timer=self.win.after(delay,self._sink)

    def _sink(self):
        self._hidden=True
        tx=-self.SIZE+self.EDGE_PEEK if (self._x+self.SIZE/2)<self._sw/2 else float(self._sw-self.EDGE_PEEK)
        self._anim(tx,self._y)
        self.win.attributes("-alpha",0.6)

    def _emerge(self):
        if not self._hidden: return
        self._hidden=False
        self.win.attributes("-alpha",0.92)
        tx=0.0 if (self._x+self.SIZE/2)<self._sw/2 else float(self._sw-self.SIZE)
        self._anim(tx,self._y)

# ─── 便签窗口 ─────────────────────────────────────────────────────────────────
class NoteWindow:
    def __init__(self,store,note_id,on_close=None):
        self.store=store; self.note_id=note_id; self.on_close=on_close
        self._save_job=None; self._destroyed=False
        note=store.get(note_id)
        if not note: return
        c=COLORS[note.get("color","paper")]
        self.win=tk.Toplevel()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost",note.get("desktop_pinned",False))
        self.win.attributes("-alpha",0.97)
        self.win.configure(bg=c["border"])
        self.win.minsize(220,280)
        sw=self.win.winfo_screenwidth(); sh=self.win.winfo_screenheight()
        w=note.get("win_w",300); h=note.get("win_h",360)
        x=note.get("win_x") or sw//2-w//2; y=note.get("win_y") or sh//2-h//2
        self.win.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self._c=c; self._color_key=note.get("color","paper")
        self._w=w; self._h=h
        self._build(c,note)
        self.win.bind("<Control-w>",lambda e:self._close())
        self.win.bind("<Control-s>",lambda e:self._save_now())
        self.win.bind("<Configure>",self._on_cfg)
        self.win.after(50,lambda:self._load(note))

    def _build(self,c,note):
        outer=tk.Frame(self.win,bg=c["border"],bd=0)
        outer.pack(fill="both",expand=True,padx=1,pady=1)
        self._outer=outer

        # ── 符录 Canvas 背景 ──
        self.bg_canvas=tk.Canvas(outer,bg=c["bg"],highlightthickness=0,bd=0)
        self.bg_canvas.place(x=0,y=0,relwidth=1,relheight=1)

        # ── 顶部工具栏（融入背景色）──
        tb_bg = c["toolbar"]
        self.tb=tk.Frame(outer,bg=tb_bg,height=30,bd=0)
        self.tb.place(x=0,y=0,relwidth=1,height=30)
        self.tb.bind("<ButtonPress-1>",self._ds)
        self.tb.bind("<B1-Motion>",self._dm)

        # 颜色选择（分两排：浅色4个+深色6个）
        sf=tk.Frame(self.tb,bg=tb_bg); sf.place(x=4,y=3)
        self._swatches={}
        row1=tk.Frame(sf,bg=tb_bg); row1.pack(side="top")
        row2=tk.Frame(sf,bg=tb_bg); row2.pack(side="top")
        light_keys=[k for k in COLOR_KEYS if not COLORS[k]["dark"]]
        dark_keys =[k for k in COLOR_KEYS if COLORS[k]["dark"]]
        for k in light_keys:
            col=COLORS[k]; b=tk.Label(row1,bg=col["swatch"],width=2,height=1,cursor="hand2",relief="flat",bd=0)
            b.pack(side="left",padx=1); b.bind("<Button-1>",lambda e,k=k:self._color(k))
            self._swatches[k]=b
        for k in dark_keys:
            col=COLORS[k]; b=tk.Label(row2,bg=col["swatch"],width=2,height=1,cursor="hand2",relief="flat",bd=0)
            b.pack(side="left",padx=1); b.bind("<Button-1>",lambda e,k=k:self._color(k))
            self._swatches[k]=b
        self._swatch_active(note.get("color","paper"))

        # 拖拽区
        drag=tk.Frame(self.tb,bg=tb_bg); drag.place(relx=0.45,y=0,relwidth=0.25,height=30)
        drag.bind("<ButtonPress-1>",self._ds); drag.bind("<B1-Motion>",self._dm)

        # 右侧按钮
        bf=tk.Frame(self.tb,bg=tb_bg); bf.place(relx=1.0,y=3,anchor="ne",x=-4)
        btn_fg = c["text"] if not c["dark"] else "#EDD98A"
        btn_color = c["border"]

        self.dpin=tk.Label(bf,text="📌" if note.get("desktop_pinned") else "📎",
            bg=tb_bg,cursor="hand2",font=("Segoe UI Emoji",10))
        self.dpin.pack(side="left",padx=1)
        self.dpin.bind("<Button-1>",lambda e:self._toggle_dpin())
        self._tip(self.dpin,"固定到桌面")

        db=tk.Label(bf,text="✕",bg=tb_bg,fg=btn_fg,cursor="hand2",font=get_font(10,"bold"))
        db.pack(side="left",padx=1)
        db.bind("<Button-1>",lambda e:self._delete())
        db.bind("<Enter>",lambda e:db.config(fg=PANEL["danger"]))
        db.bind("<Leave>",lambda e:db.config(fg=btn_fg))

        cl=tk.Label(bf,text="—",bg=tb_bg,fg=btn_fg,cursor="hand2",font=get_font(11,"bold"))
        cl.pack(side="left",padx=1)
        cl.bind("<Button-1>",lambda e:self._close())

        # ── 文字编辑区（透明叠在 Canvas 上）──
        font_face=get_font(11)[0]
        self.text=tk.Text(outer,
            bg=c["bg"],fg=c["text"],
            font=(font_face,11),
            relief="flat",bd=0,
            padx=22,pady=5,  # 给符文留边距
            wrap="word",undo=True,
            insertbackground=c["text"],
            selectbackground=c["border"],
            selectforeground=c["bg"] if c["dark"] else c["text"],
            spacing1=3,spacing3=3)
        # 把编辑区放在工具栏下，底部留给符文
        self.text.place(x=18,y=30,relwidth=1,width=-36,relheight=1,height=-54)
        self.text.bind("<<Modified>>",self._changed)

        # ── 底部状态栏 ──
        sb_bg=c["toolbar"]
        self.sb=tk.Frame(outer,bg=sb_bg,height=22,bd=0)
        self.sb.place(x=0,rely=1.0,anchor="sw",relwidth=1,height=22)
        self.wlbl=tk.Label(self.sb,text="0 字",bg=sb_bg,fg=c["placeholder"],font=get_font(8))
        self.wlbl.pack(side="left",padx=10)
        self.slbl=tk.Label(self.sb,text="● 已保存",bg=sb_bg,fg=c["placeholder"],font=get_font(8))
        self.slbl.pack(side="right",padx=10)

        # ── 缩放手柄 ──
        rc="size_nw_se" if sys.platform=="win32" else "bottom_right_corner"
        grip=tk.Label(outer,text="◢",bg=sb_bg,fg=c["border"],cursor=rc,font=get_font(9))
        grip.place(relx=1.0,rely=1.0,anchor="se",x=-1,y=-1)
        grip.bind("<ButtonPress-1>",self._rs)
        grip.bind("<B1-Motion>",self._rm)

        # 绘制符录（延迟，等 canvas 有尺寸后）
        outer.bind("<Configure>",self._on_outer_resize)
        self.win.after(100,self._redraw_talisman)

    def _redraw_talisman(self):
        try:
            w=self._outer.winfo_width(); h=self._outer.winfo_height()
            if w<10 or h<10: self.win.after(100,self._redraw_talisman); return
            self.bg_canvas.configure(width=w,height=h)
            self.bg_canvas.delete("all")
            # 背景填充
            self.bg_canvas.create_rectangle(0,0,w,h,fill=self._c["bg"],outline="")
            draw_talisman_border(self.bg_canvas,w,h,self._color_key)
        except: pass

    def _on_outer_resize(self,e):
        self.win.after(50,self._redraw_talisman)

    def _tip(self,w,text):
        tip=None
        def show(e):
            nonlocal tip
            tip=tk.Toplevel(w); tip.overrideredirect(True)
            tip.geometry(f"+{w.winfo_rootx()+20}+{w.winfo_rooty()+20}")
            tk.Label(tip,text=text,bg="#EDD98A",relief="solid",bd=1,font=get_font(9),padx=4,pady=2).pack()
        def hide(e):
            nonlocal tip
            if tip:
                try: tip.destroy()
                except: pass
                tip=None
        w.bind("<Enter>",show); w.bind("<Leave>",hide)

    def _load(self,note):
        self.text.insert("1.0",note.get("content",""))
        self.text.edit_reset(); self.text.edit_modified(False); self._wc()

    def _ds(self,e): self._dx=e.x_root-self.win.winfo_x(); self._dy=e.y_root-self.win.winfo_y()
    def _dm(self,e): self.win.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")
    def _rs(self,e): self._rx=e.x_root; self._ry=e.y_root; self._rw=self.win.winfo_width(); self._rh=self.win.winfo_height()
    def _rm(self,e):
        nw=max(220,self._rw+e.x_root-self._rx); nh=max(280,self._rh+e.y_root-self._ry)
        self.win.geometry(f"{nw}x{nh}")

    def _on_cfg(self,e):
        if e.widget==self.win:
            self.store.update(self.note_id,win_x=self.win.winfo_x(),win_y=self.win.winfo_y(),
                              win_w=self.win.winfo_width(),win_h=self.win.winfo_height())

    def _changed(self,e=None):
        if not self.text.edit_modified(): return
        self.text.edit_modified(False); self._wc(); self._ss("saving")
        if self._save_job: self.win.after_cancel(self._save_job)
        self._save_job=self.win.after(800,self._save_now)

    def _wc(self):
        n=len(self.text.get("1.0","end-1c").replace(" ","").replace("\n",""))
        self.wlbl.config(text=f"{n} 字")

    def _ss(self,s):
        if s=="saving": self.slbl.config(text="書寫中…",fg=PANEL["text2"])
        elif s=="saved":
            self.slbl.config(text="✓ 已封存",fg=PANEL["success"])
            self.win.after(2000,lambda:self.slbl.config(text="● 已保存",fg=self._c["placeholder"]))

    def _save_now(self):
        self.store.update(self.note_id,content=self.text.get("1.0","end-1c")); self._ss("saved")

    def _color(self,k):
        self._color_key=k; c=COLORS[k]; self._c=c
        self.store.update(self.note_id,color=k)
        self.win.configure(bg=c["border"])
        self._outer.configure(bg=c["border"])
        self.tb.configure(bg=c["toolbar"])
        self.text.configure(bg=c["bg"],fg=c["text"],insertbackground=c["text"],
                            selectbackground=c["border"])
        self.sb.configure(bg=c["toolbar"])
        self.wlbl.configure(bg=c["toolbar"],fg=c["placeholder"])
        self.slbl.configure(bg=c["toolbar"],fg=c["placeholder"])
        self.dpin.configure(bg=c["toolbar"])
        for w in self.tb.winfo_children():
            try: w.configure(bg=c["toolbar"])
            except: pass
        self._swatch_active(k)
        self._redraw_talisman()

    def _swatch_active(self,ak):
        for k,b in self._swatches.items():
            b.configure(relief="solid" if k==ak else "flat",bd=2 if k==ak else 0)

    def _toggle_dpin(self):
        note=self.store.get(self.note_id)
        if not note: return
        v=not note.get("desktop_pinned",False)
        self.store.update(self.note_id,desktop_pinned=v)
        self.win.attributes("-topmost",v)
        self.dpin.config(text="📌" if v else "📎")
        self.slbl.config(text="已鎮守桌面 📌" if v else "已解除鎮守",fg=PANEL["success"] if v else self._c["placeholder"])
        self.win.after(2000,lambda:self.slbl.config(text="● 已保存",fg=self._c["placeholder"]))

    def _delete(self):
        if messagebox.askyesno("刪除符籙","確定要刪除此符籙便簽？",parent=self.win):
            self._save_now(); self.store.delete(self.note_id); self._destroy()

    def _close(self): self._save_now(); self._destroy()
    def _destroy(self):
        if self._destroyed: return
        self._destroyed=True
        if self.on_close: self.on_close(self.note_id)
        try: self.win.destroy()
        except: pass
    def is_alive(self): return not self._destroyed
    def focus(self):
        try: self.win.lift(); self.win.focus_force()
        except: pass

# ─── 主面板 ──────────────────────────────────────────────────────────────────
class MainPanel:
    def __init__(self,store):
        self.store=store; self.note_windows={}; self._filter_color=None
        self._build_root()
        self._search_var=tk.StringVar()
        self._build_ui()
        store.subscribe(self._refresh)
        self._refresh()
        self.root.after(500,self._restore_desktop)

    def _restore_desktop(self):
        for note in self.store.all():
            if note.get("desktop_pinned"): self._open(note["id"])

    def _build_root(self):
        self.root=tk.Tk(); self.root.title(APP_NAME)
        self.root.configure(bg=PANEL["bg"]); self.root.overrideredirect(True)
        self.root.attributes("-topmost",False)
        W,H=380,580; sw=self.root.winfo_screenwidth(); sh=self.root.winfo_screenheight()
        self.root.geometry(f"{W}x{H}+{sw-W-20}+{sh-H-60}")
        self.root.minsize(320,440); self.root.resizable(True,True)
        self.root.configure(highlightbackground=PANEL["border"],highlightthickness=2)

    def _build_ui(self):
        r=self.root
        # 标题栏（仿古风格）
        tb=tk.Frame(r,bg=PANEL["bg2"],height=52); tb.pack(fill="x"); tb.pack_propagate(False)
        tb.bind("<ButtonPress-1>",self._ds); tb.bind("<B1-Motion>",self._dm)

        # 装饰线
        tk.Frame(r,bg=PANEL["border"],height=2).pack(fill="x")

        lf=tk.Frame(tb,bg=PANEL["bg2"]); lf.pack(side="left",padx=12,pady=8)
        # 古风标题
        tk.Label(lf,text="符",bg=PANEL["bg2"],fg=PANEL["accent"],
                 font=(get_font(22,"bold")[0],20,"bold")).pack(side="left")
        tk.Label(lf,text="籙",bg=PANEL["bg2"],fg=PANEL["border"],
                 font=(get_font(18)[0],16)).pack(side="left")
        tk.Label(lf,text=" 便簽",bg=PANEL["bg2"],fg=PANEL["text"],
                 font=(get_font(14,"bold")[0],13,"bold")).pack(side="left")

        rf=tk.Frame(tb,bg=PANEL["bg2"]); rf.pack(side="right",padx=10)
        for txt,cmd,hover in [("⊖",lambda:self.hide(),PANEL["text"]),
                               ("⊗",lambda:self.hide(),PANEL["danger"])]:
            b=tk.Label(rf,text=txt,bg=PANEL["bg2"],fg=PANEL["text2"],
                       cursor="hand2",font=get_font(14))
            b.pack(side="left",padx=3)
            b.bind("<Button-1>",lambda e,c=cmd:c())
            b.bind("<Enter>",lambda e,b=b,h=hover:b.config(fg=h))
            b.bind("<Leave>",lambda e,b=b:b.config(fg=PANEL["text2"]))

        # 装饰横幅
        banner=tk.Frame(r,bg=PANEL["bg2"],height=24); banner.pack(fill="x")
        tk.Label(banner,text="☰  吉祥如意  萬事大吉  諸事順遂  ☷",
                 bg=PANEL["bg2"],fg=PANEL["border"],font=get_font(9)).pack()
        tk.Frame(r,bg=PANEL["border"],height=1).pack(fill="x")

        # 搜索
        sf=tk.Frame(r,bg=PANEL["bg"],pady=8); sf.pack(fill="x",padx=12)
        self.clbl=tk.Label(sf,text="",bg=PANEL["bg"],fg=PANEL["text3"],
                           font=get_font(9),anchor="w")
        self.clbl.pack(fill="x",pady=(0,5))
        sb=tk.Frame(sf,bg=PANEL["bg2"],highlightbackground=PANEL["border"],highlightthickness=1)
        sb.pack(fill="x")
        tk.Label(sb,text="🔍",bg=PANEL["bg2"],font=("Segoe UI Emoji",10)).pack(side="left",padx=8)
        self._search_var.trace_add("write",lambda *_:self._refresh())
        tk.Entry(sb,textvariable=self._search_var,bg=PANEL["bg2"],fg=PANEL["text"],
                 font=get_font(11),relief="flat",insertbackground=PANEL["text"]).pack(
                 side="left",fill="x",expand=True,pady=6,padx=(0,8))
        cx=tk.Label(sb,text="✕",bg=PANEL["bg2"],fg=PANEL["text3"],cursor="hand2",font=get_font(10))
        cx.pack(side="right",padx=6); cx.bind("<Button-1>",lambda e:self._search_var.set(""))

        # 颜色筛选（两排：浅色+深色）
        ff=tk.Frame(r,bg=PANEL["bg"]); ff.pack(fill="x",padx=12,pady=(0,4))
        self._fbtns={}
        ab=tk.Label(ff,text="全部",bg=PANEL["border"],fg=PANEL["bg"],
                    font=get_font(9),padx=8,pady=2,cursor="hand2")
        ab.pack(side="left",padx=(0,3)); ab.bind("<Button-1>",lambda e:self._filter(None))
        self._fbtns["all"]=ab

        row1=tk.Frame(r,bg=PANEL["bg"]); row1.pack(fill="x",padx=12,pady=(0,1))
        row2=tk.Frame(r,bg=PANEL["bg"]); row2.pack(fill="x",padx=12,pady=(0,4))
        light_keys=[k for k in COLOR_KEYS if not COLORS[k]["dark"]]
        dark_keys =[k for k in COLOR_KEYS if COLORS[k]["dark"]]
        for k in light_keys:
            col=COLORS[k]
            d=tk.Label(row1,bg=col["swatch"],text=col["name"],fg="#1A0A00",
                       font=get_font(8),padx=4,pady=1,cursor="hand2")
            d.pack(side="left",padx=2); d.bind("<Button-1>",lambda e,k=k:self._filter(k))
            self._fbtns[k]=d
        for k in dark_keys:
            col=COLORS[k]
            d=tk.Label(row2,bg=col["swatch"],text=col["name"],fg="#EDD98A",
                       font=get_font(8),padx=4,pady=1,cursor="hand2")
            d.pack(side="left",padx=2); d.bind("<Button-1>",lambda e,k=k:self._filter(k))
            self._fbtns[k]=d

        tk.Frame(r,bg=PANEL["border"],height=1).pack(fill="x")

        # 便签网格
        lframe=tk.Frame(r,bg=PANEL["bg"]); lframe.pack(fill="both",expand=True,padx=8,pady=4)
        self.canvas=tk.Canvas(lframe,bg=PANEL["bg"],bd=0,highlightthickness=0)
        scr=ttk.Scrollbar(lframe,orient="vertical",command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scr.set)
        scr.pack(side="right",fill="y"); self.canvas.pack(side="left",fill="both",expand=True)
        self.gf=tk.Frame(self.canvas,bg=PANEL["bg"])
        self.cw=self.canvas.create_window((0,0),window=self.gf,anchor="nw")
        self.gf.bind("<Configure>",lambda e:self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",lambda e:self.canvas.itemconfig(self.cw,width=e.width))
        for w in [self.canvas,self.gf]:
            w.bind("<MouseWheel>",lambda e:self.canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

        # 底部新建按钮
        tk.Frame(r,bg=PANEL["border"],height=1).pack(fill="x")
        ft=tk.Frame(r,bg=PANEL["bg2"],pady=8); ft.pack(fill="x",padx=12)
        self.abtn=tk.Button(ft,text="✦  書符立簽",
            bg=PANEL["bg2"],fg=PANEL["text"],font=get_font(12,"bold"),
            relief="flat",activebackground=PANEL["bg"],activeforeground=PANEL["accent"],
            cursor="hand2",bd=0,
            highlightbackground=PANEL["border"],highlightthickness=1,
            pady=7,command=self._picker_toggle)
        self.abtn.pack(fill="x")

        # 颜色选择弹出层
        self._pv=False
        self._pf=tk.Frame(r,bg=PANEL["bg2"],
                          highlightbackground=PANEL["border"],highlightthickness=1)
        tk.Label(self._pf,text="選擇符紙顏色",bg=PANEL["bg2"],fg=PANEL["text3"],
                 font=get_font(9)).pack(anchor="w",padx=12,pady=(8,4))
        # 浅色排
        tk.Label(self._pf,text="淺色符紙",bg=PANEL["bg2"],fg=PANEL["text3"],font=get_font(8)).pack(anchor="w",padx=14)
        pc1=tk.Frame(self._pf,bg=PANEL["bg2"]); pc1.pack(padx=12,pady=(0,4),fill="x")
        for k in light_keys:
            col=COLORS[k]; f=tk.Frame(pc1,bg=PANEL["bg2"]); f.pack(side="left",padx=3)
            sw_btn=tk.Label(f,bg=col["swatch"],width=4,height=2,cursor="hand2",relief="flat")
            sw_btn.pack()
            sw_btn.bind("<Button-1>",lambda e,k=k:self._create(k))
            tk.Label(f,text=col["name"],bg=PANEL["bg2"],fg=PANEL["text3"],font=get_font(8)).pack()
        # 深色排
        tk.Label(self._pf,text="深色符紙",bg=PANEL["bg2"],fg=PANEL["text3"],font=get_font(8)).pack(anchor="w",padx=14)
        pc2=tk.Frame(self._pf,bg=PANEL["bg2"]); pc2.pack(padx=12,pady=(0,10),fill="x")
        for k in dark_keys:
            col=COLORS[k]; f=tk.Frame(pc2,bg=PANEL["bg2"]); f.pack(side="left",padx=3)
            sw_btn=tk.Label(f,bg=col["swatch"],width=4,height=2,cursor="hand2",relief="flat")
            sw_btn.pack()
            sw_btn.bind("<Button-1>",lambda e,k=k:self._create(k))
            tk.Label(f,text=col["name"],bg=PANEL["bg2"],fg=PANEL["text3"],font=get_font(8)).pack()

    def _card(self,parent,note,col,row):
        c=COLORS[note.get("color","paper")]; dp=note.get("desktop_pinned",False)
        brd_color="#C0392B" if dp else c["border"]
        card=tk.Frame(parent,bg=c["bg"],highlightbackground=brd_color,
                      highlightthickness=2 if dp else 1,cursor="hand2",width=162,height=130)
        card.grid(row=row,column=col,padx=3,pady=3,sticky="nsew"); card.grid_propagate(False)
        card.bind("<Button-1>",lambda e:self._open(note["id"]))
        card.bind("<MouseWheel>",lambda e:self.canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

        # 符录小角标
        corner_text="📌" if dp else ("📍" if note.get("pinned") else "☰")
        tk.Label(card,text=corner_text,bg=c["bg"],
                 font=("Segoe UI Emoji",8) if dp or note.get("pinned") else get_font(8)
                 ).place(relx=1.0,x=-4,y=3,anchor="ne")

        # 左侧小符文
        tk.Label(card,text="符",bg=c["bg"],fg=c["border"],
                 font=get_font(7)).place(x=3,y=3)

        ct=note.get("content","").strip()
        text_color=c["text"]
        cl=tk.Label(card,text=ct[:100] if ct else "空白符籙…",
                    bg=c["bg"],fg=text_color if ct else c["placeholder"],
                    font=get_font(10),wraplength=140,justify="left",anchor="nw")
        cl.place(x=12,y=16,width=138,height=82)
        cl.bind("<Button-1>",lambda e:self._open(note["id"]))
        cl.bind("<MouseWheel>",lambda e:self.canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

        # 底部日期和颜色名
        col_name=c["name"]
        tk.Label(card,text=f"{col_name} · {self._date(note.get('modified',''))}",
                 bg=c["bg"],fg=c["placeholder"],font=get_font(7),anchor="w"
                 ).place(x=8,rely=1.0,y=-18,width=130)

        db=tk.Label(card,text="✕",bg=c["bg"],fg=c["placeholder"],cursor="hand2",font=get_font(9))
        db.place(relx=1.0,rely=1.0,x=-5,y=-5,anchor="se")
        db.bind("<Button-1>",lambda e:self._del(note["id"]))
        db.bind("<Enter>",lambda e:db.config(fg=PANEL["danger"]))
        db.bind("<Leave>",lambda e:db.config(fg=c["placeholder"]))

        def ent(e): card.config(highlightbackground="#C0392B",highlightthickness=2)
        def lv(e):  card.config(highlightbackground=brd_color,highlightthickness=2 if dp else 1)
        for w in [card,cl]: w.bind("<Enter>",ent); w.bind("<Leave>",lv)

    def _refresh(self):
        for w in self.gf.winfo_children(): w.destroy()
        notes=self.store.all(); q=self._search_var.get().strip().lower()
        if self._filter_color: notes=[n for n in notes if n.get("color")==self._filter_color]
        if q: notes=[n for n in notes if q in n.get("content","").lower()]
        dp=[n for n in notes if n.get("desktop_pinned")]
        pn=[n for n in notes if n.get("pinned") and not n.get("desktop_pinned")]
        ot=[n for n in notes if not n.get("desktop_pinned") and not n.get("pinned")]
        notes=dp+pn+ot
        total=len(self.store.all())
        self.clbl.config(text="空無一物" if total==0 else f"共 {total} 張符籙")
        if not notes:
            msg="未尋到匹配符籙" if (q or self._filter_color) else "點擊下方書符立簽"
            tk.Label(self.gf,text=f"\n☯\n\n{msg}",bg=PANEL["bg"],fg=PANEL["text3"],
                     font=get_font(12),justify="center").grid(row=0,column=0,columnspan=2,pady=40)
            return
        self.gf.columnconfigure(0,weight=1); self.gf.columnconfigure(1,weight=1)
        for i,note in enumerate(notes): self._card(self.gf,note,i%2,i//2)

    def _open(self,nid):
        if nid in self.note_windows and self.note_windows[nid].is_alive():
            self.note_windows[nid].focus(); return
        win=NoteWindow(self.store,nid,on_close=lambda n:self.note_windows.pop(n,None))
        self.note_windows[nid]=win

    def _create(self,color="paper"):
        self._picker_hide(); note=self.store.create(color); self._open(note["id"])

    def _del(self,nid):
        if messagebox.askyesno("刪除符籙","確定要刪除此符籙便簽？"):
            if nid in self.note_windows:
                try: self.note_windows[nid].win.destroy()
                except: pass
                self.note_windows.pop(nid,None)
            self.store.delete(nid)

    def _filter(self,color):
        self._filter_color=color
        for k,b in self._fbtns.items():
            if k=="all": b.config(bg=PANEL["border"] if color is None else PANEL["bg2"],
                                   fg=PANEL["bg"] if color is None else PANEL["text2"])
            else:
                c=COLORS[k]; b.config(relief="solid" if k==color else "flat",bd=2 if k==color else 0)
        self._refresh()

    def _picker_toggle(self):
        if self._pv: self._picker_hide()
        else:
            self._pv=True
            self._pf.place(relx=0,rely=1.0,anchor="sw",x=12,y=-56,relwidth=1,width=-24)
            self._pf.lift()

    def _picker_hide(self): self._pv=False; self._pf.place_forget()
    def _ds(self,e): self._dx=e.x_root-self.root.winfo_x(); self._dy=e.y_root-self.root.winfo_y()
    def _dm(self,e): self.root.geometry(f"+{e.x_root-self._dx}+{e.y_root-self._dy}")
    def hide(self): self.root.withdraw()
    def show(self): self.root.deiconify(); self.root.lift(); self.root.focus_force()
    def _f(self,size,w="normal"): return get_font(size,w)
    def _date(self,iso):
        if not iso: return ""
        try:
            s=(datetime.now()-datetime.fromisoformat(iso)).total_seconds()
            if s<60: return "剛剛"
            if s<3600: return f"{int(s//60)}分鐘前"
            if s<86400: return f"{int(s//3600)}時前"
            return datetime.fromisoformat(iso).strftime("%m/%d")
        except: return ""
    def run(self): self.root.mainloop()

# ─── 入口 ────────────────────────────────────────────────────────────────────
def main():
    import sys as _s, os as _o, datetime as _d
    _base=_o.path.dirname(_o.path.abspath(_s.argv[0])); _log=_o.path.join(_base,"launch.log")
    def _lw(msg):
        line=f"[{_d.datetime.now().strftime('%H:%M:%S')}] {msg}"; print(line)
        try: open(_log,"a",encoding="utf-8").write(line+"\n")
        except: pass
    _lw("=== 符籙便簽 v3.0 啟動 ===")
    store=NoteStore()
    _lw("MainPanel 初始化...")
    panel=MainPanel(store)
    _lw("FloatingBall 初始化...")
    def toggle():
        if panel.root.winfo_viewable(): panel.hide()
        else: panel.show()
    ball=FloatingBall(panel.root,on_click=toggle)
    panel.root.after(200,panel.hide)
    _lw("進入主循環...")
    panel.run()
    _lw("退出")

if __name__=="__main__":
    main()
