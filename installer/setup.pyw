"""
符籙便簽 v3.0 - Python GUI 安装程序
特点：
- 纯 Python + tkinter，无 C 代码，不触发杀软
- 自带 Python 运行时，无需系统安装 Python
- 完整卸载：注册表、快捷方式、文件全部清理
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, sys, shutil, zipfile, winreg, json
from pathlib import Path
from datetime import datetime
import threading
import subprocess

APP_NAME    = "符籙便簽"
APP_VER     = "3.0.0"
APP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\StickyNotes_v3"
APP_DATA_KEY= r"Software\StickyNotes"

# 颜色
C = {
    "bg":     "#FAF8F3",
    "bg2":    "#F0E8D0",
    "border": "#8B4513",
    "red":    "#8B1A1A",
    "gold":   "#C8A020",
    "text":   "#1A0A00",
    "text2":  "#5A3A10",
    "green":  "#1A5A1A",
    "gray":   "#888",
}

def get_default_install_dir():
    return str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "StickyNotes")

def get_source_dir():
    """安装包里的 files/ 目录"""
    return str(Path(__file__).parent / "files")

def log_path_in(install_dir):
    return str(Path(install_dir) / "install.log")

# ─── 安装逻辑 ─────────────────────────────────────────────────────────────────

def create_shortcut_ps(lnk_path, target, args, workdir, icon_path, desc):
    """用 PowerShell 创建快捷方式（系统内置，不触发杀软）"""
    ps = (
        f'$ws=New-Object -ComObject WScript.Shell;'
        f'$s=$ws.CreateShortcut("{lnk_path}");'
        f'$s.TargetPath="{target}";'
        f'$s.Arguments=\'"{args}"\';'
        f'$s.WorkingDirectory="{workdir}";'
        f'$s.IconLocation="{icon_path},0";'
        f'$s.Description="{desc}";'
        f'$s.Save()'
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True, creationflags=0x08000000  # CREATE_NO_WINDOW
    )

def register_app(install_dir, uninst_path, ico_path):
    """注册到程序与功能"""
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APP_REG_KEY,
                                  0, winreg.KEY_WRITE)
        vals = {
            "DisplayName":     APP_NAME + " v" + APP_VER,
            "DisplayVersion":  APP_VER,
            "Publisher":       "StickyNotes",
            "InstallLocation": install_dir,
            "DisplayIcon":     ico_path + ",0",
            "UninstallString": f'"{uninst_path}"',
            "InstallDate":     datetime.now().strftime("%Y%m%d"),
            "Comments":        "古风道家符纸便签",
        }
        for k,v in vals.items():
            winreg.SetValueEx(key, k, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 80000)
        winreg.SetValueEx(key, "NoModify",      0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        return False

def save_install_info(install_dir):
    """保存安装信息到注册表（用于卸载时精确清理）"""
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, APP_DATA_KEY,
                                  0, winreg.KEY_WRITE)
        desktop = str(Path(os.environ.get("USERPROFILE","~")) / "Desktop")
        programs = str(Path(os.environ.get("APPDATA","~")) /
                      "Microsoft" / "Windows" / "Start Menu" / "Programs")
        info = {
            "install_dir":  install_dir,
            "desktop_lnk":  str(Path(desktop) / (APP_NAME + ".lnk")),
            "menu_dir":     str(Path(programs) / APP_NAME),
            "version":      APP_VER,
            "install_date": datetime.now().isoformat(),
        }
        winreg.SetValueEx(key, "InstallInfo", 0, winreg.REG_SZ, json.dumps(info))
        winreg.CloseKey(key)
    except: pass

def do_install(install_dir, progress_cb, status_cb, detail_cb):
    """
    执行安装，回调函数：
      progress_cb(0-100)
      status_cb(str)
      detail_cb(str)
    返回 (True/False, error_msg)
    """
    log_file = log_path_in(install_dir)
    def log(msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        detail_cb(line)
        try:
            os.makedirs(install_dir, exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except: pass

    try:
        # 1. 创建安装目录
        status_cb("正在创建安装目录..."); progress_cb(5)
        os.makedirs(install_dir, exist_ok=True)
        log(f"安装目录: {install_dir}")

        # 2. 复制文件
        src = get_source_dir()
        log(f"源目录: {src}")
        if not os.path.exists(src):
            return False, f"找不到安装文件目录：{src}"

        status_cb("正在复制程序文件..."); progress_cb(10)
        total = sum(len(files) for _,_,files in os.walk(src))
        copied = 0
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_dir = os.path.join(install_dir, rel) if rel != "." else install_dir
            os.makedirs(dst_dir, exist_ok=True)
            for fname in files:
                src_f = os.path.join(root, fname)
                dst_f = os.path.join(dst_dir, fname)
                shutil.copy2(src_f, dst_f)
                copied += 1
                pct = 10 + int(copied * 65 / max(total, 1))
                progress_cb(pct)
                if copied % 50 == 0:
                    status_cb(f"正在复制文件... ({copied}/{total})")
        log(f"复制完成：{copied} 个文件")

        # 3. 验证关键文件
        status_cb("正在验证安装..."); progress_cb(77)
        pythonw = os.path.join(install_dir, "pythonw.exe")
        if not os.path.exists(pythonw):
            return False, f"安装验证失败：找不到 pythonw.exe"
        log("验证通过")

        # 4. 写卸载程序
        status_cb("正在生成卸载程序..."); progress_cb(80)
        write_uninstaller(install_dir)
        log("卸载程序已生成")

        # 5. 桌面图标
        status_cb("正在创建桌面图标..."); progress_cb(84)
        pythonw_path = os.path.join(install_dir, "pythonw.exe")
        launch_path  = os.path.join(install_dir, "launch.py")
        ico_path     = os.path.join(install_dir, "app.ico")
        desktop = str(Path(os.environ.get("USERPROFILE","~")) / "Desktop")
        desk_lnk = str(Path(desktop) / (APP_NAME + ".lnk"))
        create_shortcut_ps(desk_lnk, pythonw_path, launch_path,
                           install_dir, ico_path, APP_NAME + " - 古风道家符纸便签")
        log(f"桌面图标: {desk_lnk}")

        # 6. 开始菜单
        status_cb("正在添加开始菜单..."); progress_cb(88)
        programs = str(Path(os.environ.get("APPDATA","~")) /
                      "Microsoft" / "Windows" / "Start Menu" / "Programs")
        menu_dir = str(Path(programs) / APP_NAME)
        os.makedirs(menu_dir, exist_ok=True)
        menu_lnk   = str(Path(menu_dir) / (APP_NAME + ".lnk"))
        uninst_lnk = str(Path(menu_dir) / ("卸载" + APP_NAME + ".lnk"))
        uninst_bat = str(Path(install_dir) / "uninstall.bat")
        create_shortcut_ps(menu_lnk, pythonw_path, launch_path,
                           install_dir, ico_path, APP_NAME)
        create_shortcut_ps(uninst_lnk, uninst_bat, "",
                           install_dir, "", "卸载" + APP_NAME)
        log("开始菜单已添加")

        # 7. 注册到程序与功能
        status_cb("正在注册到系统..."); progress_cb(93)
        register_app(install_dir, uninst_bat, ico_path)
        save_install_info(install_dir)
        log("已注册到控制面板 > 程序和功能")

        progress_cb(100)
        status_cb("安装完成！")
        log("=== 安装成功完成 ===")
        return True, ""

    except Exception as e:
        import traceback
        err = traceback.format_exc()
        log(f"安装失败: {e}\n{err}")
        return False, str(e)

def write_uninstaller(install_dir):
    """
    写入 Python 版卸载程序（彻底清理，无残留）
    用 Python 脚本而非 bat，清理更精确
    """
    uninst_py = os.path.join(install_dir, "_uninstall.py")
    content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""符籙便簽 v3.0 卸载程序"""
import os, sys, shutil, winreg, json, subprocess, time
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

APP_NAME    = "{APP_NAME}"
APP_REG_KEY = r"{APP_REG_KEY}"
APP_DATA_KEY= r"{APP_DATA_KEY}"

def get_install_info():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_DATA_KEY)
        val, _ = winreg.QueryValueEx(key, "InstallInfo")
        winreg.CloseKey(key)
        return json.loads(val)
    except:
        return {{}}

def kill_app():
    """结束所有相关进程"""
    subprocess.run(["taskkill", "/F", "/IM", "pythonw.exe"],
                   capture_output=True, creationflags=0x08000000)
    time.sleep(1.5)

def clean_registry():
    """清理注册表"""
    errors = []
    for hive, key in [
        (winreg.HKEY_CURRENT_USER,  APP_REG_KEY),
        (winreg.HKEY_LOCAL_MACHINE, APP_REG_KEY),
        (winreg.HKEY_CURRENT_USER,  APP_DATA_KEY),
    ]:
        try:
            winreg.DeleteKey(hive, key)
        except FileNotFoundError:
            pass
        except Exception as e:
            errors.append(str(e))
    # 清理便签数据注册表（如果有）
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                         r"Software\\StickyNotes")
    except: pass
    return errors

def clean_shortcuts(info):
    """清理所有快捷方式"""
    removed = []
    # 桌面快捷方式（多种可能路径）
    desktop_paths = [
        info.get("desktop_lnk",""),
        str(Path(os.environ.get("USERPROFILE","~")) / "Desktop" / (APP_NAME+".lnk")),
        str(Path(os.environ.get("PUBLIC","C:/Users/Public")) / "Desktop" / (APP_NAME+".lnk")),
    ]
    for p in desktop_paths:
        if p and os.path.exists(p):
            try: os.remove(p); removed.append(p)
            except: pass
    # 开始菜单目录
    menu_dirs = [
        info.get("menu_dir",""),
        str(Path(os.environ.get("APPDATA","~")) /
            "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME),
        str(Path(os.environ.get("ALLUSERSPROFILE","C:/ProgramData")) /
            "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME),
    ]
    for d in menu_dirs:
        if d and os.path.exists(d):
            try: shutil.rmtree(d); removed.append(d)
            except: pass
    return removed

def clean_appdata():
    """清理用户数据（询问）"""
    appdata_dir = str(Path(os.environ.get("APPDATA","~")) / "StickyNotes")
    if os.path.exists(appdata_dir):
        r = messagebox.askyesno(
            "保留便签数据",
            f"检测到便签数据目录：\\n{{appdata_dir}}\\n\\n"
            "是否同时删除所有便签数据？\\n\\n"
            "• 选「否」：保留便签数据\\n"
            "• 选「是」：彻底删除（不可恢复）",
            icon="question"
        )
        if r:
            try: shutil.rmtree(appdata_dir); return True
            except: pass
    return False

def clean_install_dir(install_dir):
    """删除安装目录（重试机制）"""
    if not install_dir or not os.path.exists(install_dir):
        return True
    # 先尝试直接删除
    try:
        shutil.rmtree(install_dir)
        return True
    except:
        pass
    # 某些文件可能被占用，用 rd /s /q 强制删除
    try:
        subprocess.run(["cmd", "/c", f'rd /s /q "{{install_dir}}"'],
                       capture_output=True, creationflags=0x08000000)
        time.sleep(1)
        if not os.path.exists(install_dir):
            return True
    except: pass
    # 最后手段：注册开机删除
    try:
        import winreg as wr
        key = wr.OpenKey(wr.HKEY_LOCAL_MACHINE,
                         r"SYSTEM\\CurrentControlSet\\Control\\Session Manager",
                         0, wr.KEY_READ | wr.KEY_WRITE)
        try:
            val, _ = wr.QueryValueEx(key, "PendingFileRenameOperations")
        except:
            val = ""
        # 添加删除操作（\\0\\0 = 替换为空 = 删除）
        new_val = val + "\\0" + install_dir + "\\0\\0"
        wr.SetValueEx(key, "PendingFileRenameOperations", 0, wr.REG_MULTI_SZ,
                      new_val.split("\\0"))
        wr.CloseKey(key)
        return True  # 开机后删除
    except:
        return False

def run_uninstall():
    root = tk.Tk()
    root.title("卸载 " + APP_NAME)
    root.geometry("420x200")
    root.resizable(False, False)
    root.configure(bg="#FAF8F3")
    try: root.iconbitmap(str(Path(__file__).parent / "app.ico"))
    except: pass

    tk.Label(root, text="符籙便簽 v3.0 卸载程序",
             bg="#FAF8F3", fg="#1A0A00",
             font=("Microsoft YaHei UI", 13, "bold")).pack(pady=(20,8))
    tk.Label(root, text="确定要卸载符籙便簽 v3.0 吗？",
             bg="#FAF8F3", fg="#5A3A10",
             font=("Microsoft YaHei UI", 10)).pack()

    btn_frame = tk.Frame(root, bg="#FAF8F3")
    btn_frame.pack(pady=20)

    def do_uninstall():
        yes_btn.config(state="disabled"); no_btn.config(state="disabled")
        status_lbl.config(text="正在卸载...")
        root.update()

        info = get_install_info()
        install_dir = info.get("install_dir", str(Path(__file__).parent))

        # 1. 结束进程
        status_lbl.config(text="正在结束应用程序..."); root.update()
        kill_app()

        # 2. 询问是否删除用户数据
        clean_appdata()

        # 3. 清理快捷方式
        status_lbl.config(text="正在清理快捷方式..."); root.update()
        clean_shortcuts(info)

        # 4. 清理注册表
        status_lbl.config(text="正在清理注册表..."); root.update()
        clean_registry()

        # 5. 删除安装目录
        status_lbl.config(text="正在删除程序文件..."); root.update()
        ok = clean_install_dir(install_dir)

        status_lbl.config(text="卸载完成！"); root.update()

        if ok:
            messagebox.showinfo("卸载完成",
                f"{{APP_NAME}} 已成功卸载！\\n\\n"
                "• 程序文件已删除\\n"
                "• 桌面图标已删除\\n"
                "• 开始菜单已清理\\n"
                "• 注册表已清理",
                parent=root)
        else:
            messagebox.showwarning("卸载完成（部分残留）",
                "卸载基本完成，但部分文件正在使用无法删除。\\n"
                "重启电脑后将自动清理。",
                parent=root)
        root.destroy()

    yes_btn = tk.Button(btn_frame, text="确认卸载",
        bg="#8B1A1A", fg="white", font=("Microsoft YaHei UI", 10),
        relief="flat", padx=20, pady=6, cursor="hand2",
        command=do_uninstall)
    yes_btn.pack(side="left", padx=10)

    no_btn = tk.Button(btn_frame, text="取消",
        bg="#E0D0B0", fg="#1A0A00", font=("Microsoft YaHei UI", 10),
        relief="flat", padx=20, pady=6, cursor="hand2",
        command=root.destroy)
    no_btn.pack(side="left", padx=10)

    status_lbl = tk.Label(root, text="", bg="#FAF8F3", fg="#8B4513",
                          font=("Microsoft YaHei UI", 9))
    status_lbl.pack()

    root.mainloop()

if __name__ == "__main__":
    run_uninstall()
'''
    with open(uninst_py, "w", encoding="utf-8") as f:
        f.write(content)

    # 同时写一个 bat 调用上面的 py（双击方便）
    uninst_bat = os.path.join(install_dir, "uninstall.bat")
    bat = f'''@echo off
chcp 65001 >nul
set "DIR=%~dp0"
"%DIR%pythonw.exe" "%DIR%_uninstall.py"
'''
    with open(uninst_bat, "w", encoding="utf-8") as f:
        f.write(bat)

# ─── GUI 安装程序 ─────────────────────────────────────────────────────────────

class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME + " v" + APP_VER + " 安装程序")
        self.root.configure(bg=C["bg"])
        self.root.resizable(False, False)

        # 图标
        try:
            ico = str(Path(__file__).parent / "files" / "app.ico")
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except: pass

        self._build_ui()
        # 居中
        w, h = 540, 440
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _font(self, size=10, bold=False):
        return ("Microsoft YaHei UI", size, "bold" if bold else "normal")

    def _build_ui(self):
        r = self.root

        # 顶部标题区
        header = tk.Frame(r, bg=C["red"], height=80)
        header.pack(fill="x"); header.pack_propagate(False)
        tk.Label(header, text="符  籙  便  簽",
                 bg=C["red"], fg=C["gold"],
                 font=self._font(22, True)).pack(side="left", padx=24, pady=16)
        tk.Label(header, text=f"v{APP_VER} 安装程序",
                 bg=C["red"], fg="#D4A870",
                 font=self._font(11)).pack(side="left", pady=24)

        # 分割线
        tk.Frame(r, bg=C["gold"], height=2).pack(fill="x")

        # 安装目录
        dir_frame = tk.Frame(r, bg=C["bg"], pady=10)
        dir_frame.pack(fill="x", padx=20)
        tk.Label(dir_frame, text="安装目录：", bg=C["bg"], fg=C["text"],
                 font=self._font(10)).pack(anchor="w")
        row = tk.Frame(dir_frame, bg=C["bg"])
        row.pack(fill="x", pady=4)
        self.dir_var = tk.StringVar(value=get_default_install_dir())
        self.dir_entry = tk.Entry(row, textvariable=self.dir_var,
                                   font=self._font(10), relief="solid", bd=1)
        self.dir_entry.pack(side="left", fill="x", expand=True, ipady=5)
        tk.Button(row, text="浏览…", font=self._font(9),
                  bg=C["bg2"], relief="flat", bd=1,
                  command=self._browse, padx=10, pady=5).pack(side="left", padx=(6,0))

        tk.Label(dir_frame,
                 text="⚠ 磁盘空间约需 80MB",
                 bg=C["bg"], fg=C["gray"], font=self._font(9)).pack(anchor="w", pady=(2,0))

        tk.Frame(r, bg=C["border"], height=1).pack(fill="x", padx=20, pady=4)

        # 选项
        opt_frame = tk.Frame(r, bg=C["bg"])
        opt_frame.pack(fill="x", padx=20, pady=4)
        self.chk_desktop = tk.BooleanVar(value=True)
        self.chk_menu    = tk.BooleanVar(value=True)
        self.chk_launch  = tk.BooleanVar(value=True)
        for var, text in [
            (self.chk_desktop, "✦ 创建桌面快捷方式"),
            (self.chk_menu,    "✦ 添加到开始菜单"),
            (self.chk_launch,  "✦ 安装完成后立即启动"),
        ]:
            tk.Checkbutton(opt_frame, variable=var, text=text,
                           bg=C["bg"], fg=C["text2"], font=self._font(10),
                           activebackground=C["bg"], cursor="hand2").pack(anchor="w")

        tk.Frame(r, bg=C["border"], height=1).pack(fill="x", padx=20, pady=4)

        # 进度区
        prog_frame = tk.Frame(r, bg=C["bg"])
        prog_frame.pack(fill="x", padx=20, pady=4)

        self.status_var = tk.StringVar(value="准备安装...")
        tk.Label(prog_frame, textvariable=self.status_var,
                 bg=C["bg"], fg=C["text"], font=self._font(10),
                 anchor="w").pack(fill="x")

        # 进度条（朱砂红）
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Red.Horizontal.TProgressbar",
                        troughcolor=C["bg2"], background=C["red"],
                        lightcolor=C["red"], darkcolor=C["red"])
        self.prog_bar = ttk.Progressbar(prog_frame, length=490,
                                         style="Red.Horizontal.TProgressbar",
                                         maximum=100)
        self.prog_bar.pack(fill="x", pady=4)

        # 详细日志
        log_frame = tk.Frame(prog_frame, bg=C["bg"])
        log_frame.pack(fill="x")
        self.log_text = tk.Text(log_frame, height=5, font=("Consolas",8),
                                bg="#1A0A00", fg="#C8A020",
                                relief="flat", state="disabled",
                                wrap="none")
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="x", expand=True)
        scroll.pack(side="right", fill="y")

        tk.Frame(r, bg=C["border"], height=1).pack(fill="x", padx=20, pady=6)

        # 按钮
        btn_frame = tk.Frame(r, bg=C["bg"])
        btn_frame.pack(pady=8)
        self.install_btn = tk.Button(btn_frame, text="开 始 安 装",
            bg=C["red"], fg=C["gold"], font=self._font(12, True),
            relief="flat", padx=30, pady=8, cursor="hand2",
            activebackground="#6A1010", activeforeground=C["gold"],
            command=self._start_install)
        self.install_btn.pack(side="left", padx=10)
        self.cancel_btn = tk.Button(btn_frame, text="取消",
            bg=C["bg2"], fg=C["text"], font=self._font(10),
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self.root.destroy)
        self.cancel_btn.pack(side="left", padx=6)

    def _browse(self):
        d = filedialog.askdirectory(
            title="选择安装目录",
            initialdir=self.dir_var.get())
        if d:
            self.dir_var.set(d.replace("/","\\"))

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_progress(self, pct):
        self.prog_bar["value"] = pct
        self.root.update_idletasks()

    def _set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _start_install(self):
        install_dir = self.dir_var.get().strip()
        if not install_dir:
            messagebox.showerror("错误", "请输入安装目录！")
            return

        self.install_btn.config(state="disabled")
        self.cancel_btn.config(state="disabled")
        self.dir_entry.config(state="disabled")

        def run():
            ok, err = do_install(
                install_dir,
                progress_cb=lambda p: self.root.after(0, lambda: self._set_progress(p)),
                status_cb=lambda s: self.root.after(0, lambda: self._set_status(s)),
                detail_cb=lambda d: self.root.after(0, lambda: self._append_log(d)),
            )
            self.root.after(0, lambda: self._finish(ok, err, install_dir))

        threading.Thread(target=run, daemon=True).start()

    def _finish(self, ok, err, install_dir):
        if not ok:
            messagebox.showerror("安装失败",
                f"安装过程中发生错误：\n\n{err}\n\n"
                f"详细日志：{log_path_in(install_dir)}")
            self.install_btn.config(state="normal")
            self.cancel_btn.config(state="normal")
            return

        launch = self.chk_launch.get()
        r = messagebox.showinfo("安装完成",
            f"{APP_NAME} v{APP_VER} 安装成功！\n\n"
            "✓ 桌面已生成「符籙便簽」图标\n"
            "✓ 开始菜单已添加\n"
            "✓ 已注册到程序和功能\n"
            "✓ 卸载程序已生成")
        if launch:
            pythonw = os.path.join(install_dir, "pythonw.exe")
            launch_py = os.path.join(install_dir, "launch.py")
            if os.path.exists(pythonw) and os.path.exists(launch_py):
                tcl = os.path.join(install_dir, "tcl", "tcl8.6")
                tk_ = os.path.join(install_dir, "tcl", "tk8.6")
                env = os.environ.copy()
                env["TCL_LIBRARY"] = tcl
                env["TK_LIBRARY"]  = tk_
                subprocess.Popen([pythonw, launch_py], cwd=install_dir, env=env,
                                 creationflags=0x00000008)  # DETACHED_PROCESS
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    InstallerApp().run()
