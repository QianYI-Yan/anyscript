import os
import ctypes
import ctypes.wintypes
import time
import threading
import queue
import customtkinter as ctk
from tkinter import ttk
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================== Everything SDK 常量 ==================
EVERYTHING_REQUEST_FILE_NAME = 0x00000001
EVERYTHING_REQUEST_PATH = 0x00000002
EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME = 0x00000004
EVERYTHING_REQUEST_SIZE = 0x00000010
EVERYTHING_REQUEST_DATE_CREATED = 0x00000020
EVERYTHING_REQUEST_DATE_MODIFIED = 0x00000040
EVERYTHING_REQUEST_DATE_ACCESSED = 0x00000080

# ================== 查找 Everything DLL ==================
def find_everything_dll():
    candidates = [
        "Everything64.dll", "Everything32.dll",
        os.path.join(os.getcwd(), "Everything64.dll"),
        os.path.join(os.getcwd(), "Everything32.dll"),
        os.path.join(os.path.dirname(__file__), "Everything64.dll"),
        os.path.join(os.path.dirname(__file__), "Everything32.dll"),
        "C:\\Program Files\\Everything\\Everything64.dll",
        "C:\\Program Files (x86)\\Everything\\Everything32.dll",
        os.path.join(os.path.expanduser("~"), "Downloads", "Everything-SDK", "dll", "Everything64.dll"),
        os.path.join(os.path.expanduser("~"), "Downloads", "Everything-SDK", "dll", "Everything32.dll"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def load_everything_dll():
    dll_path = find_everything_dll()
    if not dll_path:
        raise FileNotFoundError("未找到 Everything DLL，请将 DLL 放入脚本目录")
    return ctypes.WinDLL(dll_path)

try:
    everything = load_everything_dll()
    print("Everything DLL 加载成功")
except Exception as e:
    print(f"加载 Everything DLL 失败: {e}")
    everything = None

if everything:
    everything.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
    everything.Everything_SetSearchW.restype = None
    everything.Everything_SetRequestFlags.argtypes = [ctypes.c_uint]
    everything.Everything_SetRequestFlags.restype = None
    everything.Everything_QueryW.argtypes = [ctypes.c_int]
    everything.Everything_QueryW.restype = ctypes.c_int
    everything.Everything_GetNumResults.argtypes = []
    everything.Everything_GetNumResults.restype = ctypes.c_int
    everything.Everything_GetResultFullPathNameW.argtypes = [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]
    everything.Everything_GetResultFullPathNameW.restype = ctypes.c_int
    everything.Everything_GetResultDateModified.argtypes = [ctypes.c_int]
    everything.Everything_GetResultDateModified.restype = ctypes.c_longlong
    everything.Everything_GetResultDateCreated.argtypes = [ctypes.c_int]
    everything.Everything_GetResultDateCreated.restype = ctypes.c_longlong
    everything.Everything_GetResultAttributes.argtypes = [ctypes.c_int]
    everything.Everything_GetResultAttributes.restype = ctypes.c_uint

# ================== Windows API 辅助函数 ==================
def get_final_path(target_path):
    try:
        handle = ctypes.windll.kernel32.CreateFileW(
            target_path,
            0x80000000,
            0x00000001,
            None,
            3,
            0x02000000,
            None
        )
        if handle == -1:
            return None
        buf = ctypes.create_unicode_buffer(260)
        length = ctypes.windll.kernel32.GetFinalPathNameByHandleW(handle, buf, 260, 0)
        ctypes.windll.kernel32.CloseHandle(handle)
        if length > 0:
            final = buf.value
            if final.startswith("\\\\?\\"):
                final = final[4:]
            elif final.startswith("\\??\\"):
                final = final[4:]
            return final.upper()
    except:
        pass
    return None

def is_junction_to_d(path):
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        if attrs & 0x400:
            target = get_final_path(path)
            return target and target.startswith("D:\\")
    except:
        pass
    return False

# ================== 扫描核心 ==================
def scan_with_everything():
    """使用 Everything 获取所有文件夹，然后过滤出指向 D 盘的 junction"""
    if not everything:
        return None  # Everything 不可用

    # 搜索所有文件夹
    everything.Everything_SetSearchW("type:folder")
    everything.Everything_SetRequestFlags(
        EVERYTHING_REQUEST_FULL_PATH_AND_FILE_NAME |
        EVERYTHING_REQUEST_DATE_MODIFIED |
        EVERYTHING_REQUEST_DATE_CREATED
    )
    if everything.Everything_QueryW(1) != 0:
        print("Everything 查询失败")
        return None

    total = everything.Everything_GetNumResults()
    print(f"Everything 找到 {total} 个文件夹")
    if total == 0:
        print("Everything 返回 0 个文件夹，可能是索引未包含目录，将回退到传统扫描。")
        return None

    results = []
    # 使用线程池并发检查
    def check_index(i):
        buf = ctypes.create_unicode_buffer(260)
        everything.Everything_GetResultFullPathNameW(i, buf, 260)
        path = buf.value
        if not is_junction_to_d(path):
            return None
        mod_time_ft = everything.Everything_GetResultDateModified(i)
        create_time_ft = everything.Everything_GetResultDateCreated(i)
        mod_time_str = datetime.fromtimestamp((mod_time_ft - 116444736000000000) / 10000000).strftime("%Y-%m-%d %H:%M:%S") if mod_time_ft else "未知"
        create_time_str = datetime.fromtimestamp((create_time_ft - 116444736000000000) / 10000000).strftime("%Y-%m-%d %H:%M:%S") if create_time_ft else "未知"
        target = get_final_path(path)
        return (path, target, create_time_str, mod_time_str)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(check_index, i) for i in range(total)]
        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)
                if len(results) % 100 == 0:
                    print(f"已发现 {len(results)} 个指向 D 盘的链接")
    return results

def scan_with_oswalk():
    """传统 os.walk 扫描，作为备用"""
    print("使用传统扫描方式 (os.walk)...")
    results = []
    exclude_dirs = {"System Volume Information"}
    top_dirs = []
    try:
        for item in os.listdir("C:\\"):
            full = os.path.join("C:\\", item)
            if os.path.isdir(full) and item not in exclude_dirs:
                top_dirs.append(full)
    except PermissionError:
        pass

    total_found = 0
    for root_dir in top_dirs:
        for root, dirs, files in os.walk(root_dir):
            # 跳过排除目录
            if exclude_dirs:
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for d in dirs:
                full_path = os.path.join(root, d)
                if is_junction_to_d(full_path):
                    target = get_final_path(full_path)
                    ctime, mtime = "未知", "未知"
                    try:
                        stat = os.stat(full_path)
                        ctime = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                    results.append((full_path, target, ctime, mtime))
                    total_found += 1
                    if total_found % 100 == 0:
                        print(f"已发现 {total_found} 个指向 D 盘的链接")
    return results

# ================== GUI 界面 ==================
class ResultWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("寂月的全盘扫描清单 - 指向 D 盘的目录链接")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.geometry("1000x600")
        self.minsize(800, 400)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree_frame = ctk.CTkFrame(self.main_frame)
        self.tree_frame.pack(fill="both", expand=True)

        self.columns = ("序号", "路径", "目标路径", "创建时间", "修改时间")
        self.tree = ttk.Treeview(self.tree_frame, columns=self.columns, show="headings", height=20)
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c, False))
        self.tree.column("序号", width=60, anchor="center")
        self.tree.column("路径", width=400, anchor="w")
        self.tree.column("目标路径", width=300, anchor="w")
        self.tree.column("创建时间", width=150, anchor="center")
        self.tree.column("修改时间", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.progress = ctk.CTkProgressBar(self.main_frame, width=400)
        self.progress.pack(pady=10, fill="x")
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self.main_frame, text="就绪")
        self.status_label.pack(pady=5)

        self.items = []  # (路径, 目标, 创建时间, 修改时间)

        # 启动扫描线程
        self.start_scan()

        self.update_gui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_scan(self):
        self.status_label.configure(text="正在扫描...")
        self.progress.set(0.5)
        self.after(100, self._run_scan)

    def _run_scan(self):
        def scan():
            results = scan_with_everything()
            if results is None:
                # Everything 不可用或返回 0，回退到 os.walk
                results = scan_with_oswalk()
            # 通过队列传递
            result_queue = queue.Queue()
            for r in results:
                result_queue.put(r)
            result_queue.put(None)
            return result_queue

        def collect():
            result_queue = scan()
            self.items.clear()
            for child in self.tree.get_children():
                self.tree.delete(child)
            count = 0
            while True:
                try:
                    item = result_queue.get(timeout=0.1)
                    if item is None:
                        break
                    path, target, ctime, mtime = item
                    count += 1
                    self.items.append((path, target, ctime, mtime))
                    self.tree.insert("", "end", values=(count, path, target, ctime, mtime))
                    self.status_label.configure(text=f"已发现 {count} 个指向 D 盘的链接")
                except queue.Empty:
                    self.update()
                    continue
            self.progress.set(1.0)
            self.status_label.configure(text=f"扫描完成！共发现 {count} 个指向 D 盘的链接")
        self.after(100, collect)

    def sort_column(self, col, reverse):
        col_index = self.columns.index(col) - 1
        self.items.sort(key=lambda x: x[col_index], reverse=reverse)
        for child in self.tree.get_children():
            self.tree.delete(child)
        for i, item in enumerate(self.items, 1):
            self.tree.insert("", "end", values=(i,) + item)
        for c in self.columns:
            self.tree.heading(c, text=c)
        self.tree.heading(col, text=f"{col} {'▼' if reverse else '▲'}")

    def update_gui(self):
        self.after(500, self.update_gui)

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    print("--- 寂月的全盘扫描清单 (智能扫描版) ---")
    app = ResultWindow()
    app.mainloop()