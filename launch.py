import os, sys

# 检测是否运行在 PyInstaller 打包环境中
def is_pyinstaller():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_base_path():
    """获取程序基础路径"""
    if is_pyinstaller():
        # PyInstaller 环境
        return sys._MEIPASS
    else:
        # 普通 Python 环境
        return os.path.dirname(os.path.abspath(sys.argv[0]))

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'launch.log')
def log(msg):
    import datetime
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except: pass

try:
    log("=== 符籙便簽 v3.0 啟動 ===")
    base = get_base_path()
    log(f"程序目录 = {base}")
    log(f"日志文件 = {LOG_FILE}")
    log(f"PyInstaller 环境：{is_pyinstaller()}")

    # 自动检测 tcl/tk 库路径
    tcl_lib = None
    tk_lib = None

    # 方案 1: 传统 tcl/tk8.6 目录结构
    if os.path.exists(os.path.join(base, 'tcl', 'tcl8.6')):
        tcl_lib = os.path.join(base, 'tcl', 'tcl8.6')
        tk_lib = os.path.join(base, 'tcl', 'tk8.6')
    # 方案 2: PyInstaller _internal 结构
    elif os.path.exists(os.path.join(base, '_tcl_data')):
        tcl_lib = os.path.join(base, '_tcl_data')
        tk_lib = os.path.join(base, '_tk_data')
    # 方案 3: _internal 子目录
    elif os.path.exists(os.path.join(base, '_internal', '_tcl_data')):
        tcl_lib = os.path.join(base, '_internal', '_tcl_data')
        tk_lib = os.path.join(base, '_internal', '_tk_data')

    if tcl_lib and tk_lib:
        os.environ['TCL_LIBRARY'] = tcl_lib
        os.environ['TK_LIBRARY']  = tk_lib
        log(f"TCL_LIBRARY = {tcl_lib} (存在:{os.path.exists(tcl_lib)})")
        log(f"TK_LIBRARY  = {tk_lib}  (存在:{os.path.exists(tk_lib)})")
        log(f"tk.tcl      = {os.path.join(tk_lib,'tk.tcl')} (存在:{os.path.exists(os.path.join(tk_lib,'tk.tcl'))})")
    else:
        log("警告：未找到 tcl/tk 库，tkinter 可能无法正常工作")

    sys.path.insert(0, base)
    sys.path.insert(1, os.path.join(base, 'Lib'))

    log("导入 tkinter...")
    import tkinter as tk
    log(f"tkinter OK: Tcl={tk.TclVersion} Tk={tk.TkVersion}")

    log("导入 app...")
    import app
    log("启动主程序...")
    app.main()

except Exception as e:
    import traceback
    err = traceback.format_exc()
    log(f"启动失败: {e}")
    log(err)
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0,
            f"启动失败！\n\n{e}\n\n详情请查看:\n{LOG_FILE}",
            "符籙便簽 - 錯誤", 0x10)
    except:
        pass
