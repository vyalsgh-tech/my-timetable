import sys
import os
import csv
import json
import ctypes
import threading
import re
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import tkinter.font as tkfont
import tkinter.simpledialog as simpledialog
from PIL import Image, ImageTk
import pystray
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 🚨 Supabase 클라우드 연동 설정 (필수 기입)
# ==========================================
SUPABASE_URL = "여기에_선생님의_Supabase_URL을_입력하세요"
SUPABASE_KEY = "여기에_선생님의_Supabase_API_KEY를_입력하세요"

USE_SUPABASE = "여기에" not in SUPABASE_URL

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}
HEADERS_UPSERT = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation"
}
# ==========================================

class TimetableWidget:
    def __init__(self, root):
        self.root = root
        
        self.themes = [
            { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'titlebar_bg': '#2c3e50' },
            { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'titlebar_bg': '#d6caba' },
            { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'titlebar_bg': '#5c9ce6' },
            { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'titlebar_bg': '#3b6a57' },
            { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'titlebar_bg': '#555555' }
        ]

        self.root.overrideredirect(True)
        self._offset_x = 0
        self._offset_y = 0
        self.click_timer = None
        self.selected_memo_idx = None
        self.is_locked = False
        self.is_topmost = False

        self.base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        appdata_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'TeacherTimetable')
        if not os.path.exists(appdata_dir):
            try: os.makedirs(appdata_dir)
            except: pass
        
        self.config_file = os.path.join(appdata_dir, 'settings.txt')
        self.memos_file = os.path.join(appdata_dir, 'memos.json')
        self.custom_data_file = os.path.join(appdata_dir, 'custom_data.json')

        self.icon_path = os.path.join(self.base_dir, 'logo.ico')
        if os.path.exists(self.icon_path):
            self.root.iconbitmap(self.icon_path)

        self.root.after(100, self.set_appwindow)
        self.setup_tray()

        self.teachers_data = {}
        self.memos_data = {}
        self.custom_data = {} 
        self.week_offset = 0

        self.period_times = [
            ("조회", "07:40", "08:00"), ("1교시", "08:00", "08:50"), ("2교시", "09:00", "09:50"),
            ("3교시", "10:00", "10:50"), ("4교시", "11:00", "11:50"), ("점심",  "11:50", "12:40"),
            ("5교시", "12:40", "13:30"), ("6교시", "13:40", "14:30"), ("7교시", "14:40", "15:30"),
            ("8교시", "16:00", "16:50"), ("9교시", "17:00", "17:50")
        ]
        self.days = ["월", "화", "수", "목", "금"]
        self.cells = {} 

        self.load_settings()
        
        ff = self.settings.get('font_family', '맑은 고딕')
        self.font_title = tkfont.Font(family=ff, size=9, weight='bold')
        self.font_head = tkfont.Font(family=ff, size=10, weight='bold')
        self.font_period = tkfont.Font(family=ff, size=8, weight='bold')
        self.font_cell = tkfont.Font(family=ff, size=10, weight='bold')
        self.font_cell_strike = tkfont.Font(family=ff, size=10, weight='bold', overstrike=1)

        self.load_csv_data()
        self.load_memos()
        self.load_custom_data()
        
        self.root.attributes('-topmost', self.is_topmost)
        self.root.attributes('-alpha', self.settings.get('alpha', 0.95))
        
        if self.settings.get('auto_login') and self.settings.get('logged_in_user'):
            self.verify_and_load_user(self.settings['logged_in_user'])
            self.start_main_app()
        else:
            self.build_login_ui()

    def parse_text_color(self, raw_text):
        if not raw_text: return "", None
        m = re.match(r'^<span style=[\'"]color:([^"\']+)[\'"]>(.*)</span>$', raw_text, re.DOTALL | re.IGNORECASE)
        if m: return m.group(2), m.group(1)
        return raw_text, None

    def set_appwindow(self):
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = style & ~0x00000080 | 0x00040000 
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        self.root.withdraw()
        self.root.deiconify()

    def setup_tray(self):
        if os.path.exists(self.icon_path): image = Image.open(self.icon_path)
        else: image = Image.new('RGB', (64, 64), color=(44, 62, 80))
        menu = pystray.Menu(
            pystray.MenuItem("시간표 보이기", self.show_window),
            pystray.MenuItem("시간표 숨기기", self.hide_window),
            pystray.MenuItem("프로그램 종료", self.close_app)
        )
        self.tray_icon = pystray.Icon("Timetable", image, "교사 시간표", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item): self.root.after(0, self.root.deiconify)
    def hide_window(self, icon, item): self.root.after(0, self.root.withdraw)
    def minimize_app(self):
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 6) 

    def toggle_maximize(self):
        if self.root.state() == 'zoomed':
            self.root.state('normal')
            if hasattr(self, 'max_btn'): self.max_btn.config(text="□")
        else:
            self.root.state('zoomed')
            if hasattr(self, 'max_btn'): self.max_btn.config(text="❐")

    def close_app(self, icon=None, item=None):
        self.save_settings() 
        if hasattr(self, 'tray_icon'): self.tray_icon.stop()
        self.root.destroy()

    def load_csv_data(self):
        file_path = os.path.join(self.base_dir, 'data.csv')
        if not os.path.exists(file_path): return
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if not row or len(row) < 36: continue
                    name = row[0]
                    periods_per_day = (len(row) - 1) // 5
                    schedule = {"월": [], "화": [], "수": [], "목": [], "금": []}
                    for i, day in enumerate(self.days):
                        start_idx = 1 + i * periods_per_day
                        day_list = row[start_idx : start_idx + periods_per_day][:9]
                        while len(day_list) < 9:
                            day_list.append("")
                        schedule[day] = day_list
                    self.teachers_data[name] = schedule
        except: pass

    def load_settings(self):
        self.settings = {
            'logged_in_user': None, 'teacher': None, 'auto_login': False, 'show_extra': False, 'show_zero': False, 'show_memo': True,
            'show_memo_expanded': False, 'theme_idx': 0, 'is_locked': False, 'is_topmost': False, 
            'width': 608, 'height': 555, 'x': 100, 'y': 100, 'font_family': '맑은 고딕', 'alpha': 0.95
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = f.read().strip()
                    if data.startswith('{'): self.settings.update(json.loads(data))
            except: pass

        self.show_extra = self.settings['show_extra']
        self.show_zero = self.settings['show_zero']
        self.show_memo = self.settings.get('show_memo', True)
        self.show_memo_expanded = self.settings.get('show_memo_expanded', False)
        self.current_theme_idx = self.settings['theme_idx']
        self.is_locked = self.settings['is_locked']
        self.is_topmost = self.settings['is_topmost']
        self.base_width = self.settings['width']
        self.base_height = self.settings['height']
        self.scale_var = tk.StringVar(value="100%")
        self.alpha_var = tk.DoubleVar(value=self.settings.get('alpha', 0.95))

    def save_settings(self):
        try:
            if hasattr(self, 'teacher_var') and self.teacher_var.get():
                self.settings['teacher'] = self.teacher_var.get()
            self.settings['show_extra'] = self.show_extra
            self.settings['show_zero'] = self.show_zero
            self.settings['show_memo'] = self.show_memo
            self.settings['show_memo_expanded'] = getattr(self, 'show_memo_expanded', False)
            self.settings['theme_idx'] = self.current_theme_idx
            self.settings['is_locked'] = self.is_locked
            self.settings['is_topmost'] = self.is_topmost
            if self.root.winfo_exists() and self.root.state() != 'zoomed':
                self.settings['width'] = self.root.winfo_width()
                self.settings['height'] = self.root.winfo_height()
                self.settings['x'] = self.root.winfo_x()
                self.settings['y'] = self.root.winfo_y()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False)
        except: pass

    def load_memos(self):
        if os.path.exists(self.memos_file):
            try:
                with open(self.memos_file, 'r', encoding='utf-8') as f: self.memos_data = json.load(f)
            except: self.memos_data = {}

    def save_memos(self):
        try:
            with open(self.memos_file, 'w', encoding='utf-8') as f: json.dump(self.memos_data, f, ensure_ascii=False)
        except: pass

    def load_custom_data(self):
        if os.path.exists(self.custom_data_file):
            try:
                with open(self.custom_data_file, 'r', encoding='utf-8') as f: self.custom_data = json.load(f)
            except: self.custom_data = {}

    def save_custom_data(self):
        try:
            with open(self.custom_data_file, 'w', encoding='utf-8') as f: json.dump(self.custom_data, f, ensure_ascii=False)
        except: pass

    def verify_and_load_user(self, user_id):
        if not USE_SUPABASE: return None
        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{user_id}", headers=HEADERS, verify=False)
            if r.status_code == 200 and len(r.json()) > 0:
                u_data = r.json()[0]
                self.current_theme_idx = u_data.get('theme_idx', 0)
                self.settings['font_family'] = u_data.get('font_name', '맑은 고딕')
                self.show_zero = u_data.get('show_zero', False)
                self.show_extra = u_data.get('show_extra', False)
                self.show_memo = u_data.get('show_memo', True)
                return u_data
        except: pass
        return None

    def bg_sync_db(self):
        if not USE_SUPABASE: return
        
        try:
            r1 = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, verify=False)
            if r1.status_code == 200:
                new_custom = {}
                for row in r1.json():
                    t = row.get('teacher_name')
                    dk = row.get('date_key')
                    if not t or not dk: continue
                    if t not in new_custom: new_custom[t] = {}
                    new_custom[t][dk] = row.get('subject', '')
                self.custom_data = new_custom
                self.save_custom_data()
        except: pass

        try:
            r2 = requests.get(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, verify=False)
            if r2.status_code == 200:
                new_memos = {}
                for row in r2.json():
                    t = row.get('teacher_name')
                    if not t: continue
                    if t not in new_memos: new_memos[t] = []
                    new_memos[t].append(row)
                
                final_memos = {}
                for t, rows in new_memos.items():
                    sorted_rows = sorted(rows, key=lambda x: x.get('id', 0), reverse=True)
                    final_memos[t] = []
                    for row in sorted_rows:
                        final_memos[t].append({
                            'id': row.get('id'), 
                            'text': row.get('memo_text', ''), 
                            'strike': row.get('is_strike', False), 
                            'important': row.get('is_important', False)
                        })
                self.memos_data = final_memos
                self.save_memos()
        except: pass

        self.root.after(0, self.refresh_schedule_display)
        self.root.after(0, self.refresh_memo_list)

    def build_login_ui(self):
        for widget in self.root.winfo_children(): widget.destroy()
        
        w, h = 400, 350
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.configure(bg='#ecf0f1')
        
        title_bar = tk.Frame(self.root, bg='#2c3e50', bd=0)
        title_bar.pack(fill='x', side='top')
        
        title_lbl = tk.Label(title_bar, text="로그인 - 명덕외고 시간표", bg='#2c3e50', fg='white', font=('맑은 고딕', 9, 'bold'))
        title_lbl.pack(side='left', padx=10, pady=5)
        
        tk.Button(title_bar, text="X", bg='#c0392b', fg='white', bd=0, width=4, font=('맑은 고딕', 9), command=self.close_app).pack(side='right')

        for w_item in [title_bar, title_lbl]:
            w_item.bind('<Button-1>', self.click_window)
            w_item.bind('<B1-Motion>', self.drag_window)

        main_f = tk.Frame(self.root, bg='#ecf0f1')
        main_f.pack(expand=True, fill='both', padx=20, pady=20)
        
        tk.Label(main_f, text="🏫 시간표 뷰어", font=('맑은 고딕', 18, 'bold'), bg='#ecf0f1', fg='#2c3e50').pack(pady=(5, 15))
        
        tk.Label(main_f, text="아이디(성함)", bg='#ecf0f1').pack(anchor='w')
        self.id_entry = tk.Entry(main_f, font=('맑은 고딕', 10)); self.id_entry.pack(fill='x', pady=(0, 10))
        
        tk.Label(main_f, text="비밀번호", bg='#ecf0f1').pack(anchor='w')
        self.pw_entry = tk.Entry(main_f, show='*', font=('맑은 고딕', 10)); self.pw_entry.pack(fill='x', pady=(0, 10))
        
        self.auto_login_var = tk.BooleanVar(value=self.settings.get('auto_login', False))
        tk.Checkbutton(main_f, text="자동 로그인", variable=self.auto_login_var, bg='#ecf0f1', font=('맑은 고딕', 9)).pack(anchor='w', pady=(0, 10))

        tk.Button(main_f, text="로그인", bg='#2980b9', fg='white', font=('맑은 고딕', 10, 'bold'), command=self.do_login).pack(fill='x', pady=2)
        tk.Button(main_f, text="계정 생성", bg='#27ae60', fg='white', font=('맑은 고딕', 10, 'bold'), command=self.do_register).pack(fill='x', pady=2)

    def do_login(self):
        u_id, u_pw = self.id_entry.get().strip(), self.pw_entry.get().strip()
        if not u_id or not u_pw:
            messagebox.showwarning("입력 누락", "아이디와 비밀번호를 모두 입력해 주세요."); return
        
        if not USE_SUPABASE:
            self.settings['logged_in_user'] = u_id
            self.settings['teacher'] = u_id 
            self.settings['auto_login'] = self.auto_login_var.get()
            self.start_main_app(); return

        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{u_id}", headers=HEADERS, verify=False)
            data = r.json()
            if r.status_code == 200 and len(data) > 0:
                if str(data[0]['password']) == u_pw:
                    self.settings['logged_in_user'] = u_id
                    self.settings['teacher'] = u_id 
                    self.settings['auto_login'] = self.auto_login_var.get()
                    self.verify_and_load_user(u_id)
                    self.start_main_app()
                else: messagebox.showerror("로그인 실패", "비밀번호가 일치하지 않습니다.")
            else: messagebox.showerror("로그인 실패", "등록되지 않은 이름입니다.")
        except Exception as e:
            messagebox.showerror("오류", f"로그인 중 오류가 발생했습니다: {e}")

    def do_register(self):
        u_id, u_pw = self.id_entry.get().strip(), self.pw_entry.get().strip()
        if not u_id or not u_pw: return
        try:
            r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{u_id}", headers=HEADERS, verify=False)
            if r.status_code == 200 and len(r.json()) > 0: messagebox.showwarning("경고", "이미 존재하는 성함입니다.")
            else:
                requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json={"teacher_name": u_id, "password": u_pw}, verify=False)
                messagebox.showinfo("완료", f"{u_id} 선생님, 계정 생성이 완료되었습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"계정 생성 중 오류: {e}")

    def start_main_app(self):
        for widget in self.root.winfo_children(): widget.destroy()
        self.save_settings()
        
        w = self.settings.get('width', 608)
        if w < 500: w = 608 
        h = self.base_height_core
        
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = self.settings.get('x', int((sw - w) / 2))
        y = self.settings.get('y', int((sh - h) / 2))
        
        if self.root.state() != 'zoomed':
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.update_font_size(w, h)
        
        self.build_ui()
        self.apply_theme()
        self.update_time_and_date()
        if USE_SUPABASE: threading.Thread(target=self.bg_sync_db, daemon=True).start()

    def build_ui(self):
        self.title_bar = tk.Frame(self.root, bd=0)
        self.title_bar.pack(fill='x', side='top')
        exe_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.title_lbl = tk.Label(self.title_bar, text=exe_name, font=('맑은 고딕', 9, 'bold'))
        self.title_lbl.pack(side='left', padx=10, pady=2)
        self.close_btn = tk.Button(self.title_bar, text="X", bd=0, width=4, font=('맑은 고딕', 9), command=self.close_app)
        self.close_btn.pack(side='right')
        self.max_btn = tk.Button(self.title_bar, text="□", bd=0, width=4, font=('맑은 고딕', 9), command=self.toggle_maximize)
        self.max_btn.pack(side='right')
        self.min_btn = tk.Button(self.title_bar, text="─", bd=0, width=4, font=('맑은 고딕', 9), command=self.minimize_app)
        self.min_btn.pack(side='right')

        for w in [self.title_bar, self.title_lbl]:
            w.bind('<Button-1>', self.click_window)
            w.bind('<B1-Motion>', self.drag_window)

        self.top_bar = tk.Frame(self.root, bd=0)
        self.top_bar.pack(fill='x', padx=2, pady=(0, 2))
        self.left_frame = tk.Frame(self.top_bar, bd=0); self.left_frame.pack(side='left')
        self.right_frame = tk.Frame(self.top_bar, bd=0); self.right_frame.pack(side='right')

        teacher_names = list(self.teachers_data.keys())
        self.teacher_var = tk.StringVar()
        self.teacher_cb = ttk.Combobox(self.left_frame, textvariable=self.teacher_var, values=teacher_names, width=7, state='readonly', font=self.font_title)
        self.teacher_cb.pack(side='left', padx=2)
        self.teacher_cb.bind('<<ComboboxSelected>>', self.on_teacher_select)

        self.prev_btn = tk.Button(self.left_frame, text="◀", bd=0, width=2, font=self.font_title, command=self.prev_week)
        self.prev_btn.pack(side='left', padx=1)
        self.curr_btn_border = tk.Frame(self.left_frame, bd=0); self.curr_btn_border.pack(side='left', padx=1)
        self.curr_btn = tk.Button(self.curr_btn_border, text="이번주", bd=0, width=5, font=self.font_title, command=self.curr_week)
        self.curr_btn.pack(padx=2, pady=2) 
        self.next_btn = tk.Button(self.left_frame, text="▶", bd=0, width=2, font=self.font_title, command=self.next_week)
        self.next_btn.pack(side='left', padx=1)
        self.memo_btn = tk.Button(self.left_frame, text="메모", bd=0, width=4, font=self.font_title, command=self.toggle_memo)
        self.memo_btn.pack(side='left', padx=2)
        self.zero_btn = tk.Button(self.left_frame, text="조회+", bd=0, width=6, font=self.font_title, command=self.toggle_zero)
        self.zero_btn.pack(side='left', padx=2)
        self.extra_btn = tk.Button(self.left_frame, text="8,9교시+", bd=0, width=7, font=self.font_title, command=self.toggle_extra)
        self.extra_btn.pack(side='left', padx=2)

        if teacher_names:
            login_u = self.settings.get('logged_in_user')
            target_u = login_u if login_u in teacher_names else self.settings.get('teacher')
            if not target_u or target_u not in teacher_names: 
                target_u = "표민호" if "표민호" in teacher_names else teacher_names[0]
            
            default_idx = teacher_names.index(target_u)
            self.teacher_cb.current(default_idx)
            self.teacher_var.set(target_u) 
            self.current_schedule = self.teachers_data.get(target_u, {d: [""]*9 for d in self.days})

        self.alpha_lbl = tk.Label(self.right_frame, text="투명도", font=('맑은 고딕', 8, 'bold'))
        self.alpha_lbl.pack(side='left', padx=(2, 0))
        self.alpha_scale = ttk.Scale(self.right_frame, from_=0.3, to=1.0, variable=self.alpha_var, orient='horizontal', length=60, command=self.on_alpha_slide)
        self.alpha_scale.pack(side='left', padx=(2, 6))
        tk.Button(self.right_frame, text="저장", bg='#27ae60', fg='white', bd=0, width=4, font=self.font_title, command=self.manual_save_db).pack(side='left', padx=2)
        self.settings_mb = tk.Menubutton(self.right_frame, text="설정 ⚙", bg='#7f8c8d', fg='white', bd=0, width=6, font=self.font_title, relief='flat')
        self.settings_menu = tk.Menu(self.settings_mb, tearoff=0, font=('맑은 고딕', 9))
        self.settings_mb.config(menu=self.settings_menu); self.settings_mb.pack(side='left', padx=2)
        self.update_settings_menu()

        self.grid_frame = tk.Frame(self.root); self.grid_frame.pack(fill='both', expand=True, padx=3, pady=3)
        self.memo_frame = tk.Frame(self.root); 
        self.memo_input_f = tk.Frame(self.memo_frame); self.memo_input_f.pack(side='bottom', fill='x')
        self.memo_entry = tk.Entry(self.memo_input_f, font=self.font_title); self.memo_entry.pack(side='left', fill='x', expand=True, padx=(0, 4)); self.memo_entry.bind('<Return>', self.add_memo)
        tk.Button(self.memo_input_f, text="추가", bg='#27ae60', fg='white', bd=0, font=self.font_title, command=self.add_memo).pack(side='left', padx=1)
        tk.Button(self.memo_input_f, text="수정", bg='#f39c12', fg='white', bd=0, font=self.font_title, command=self.edit_memo).pack(side='left', padx=1)
        tk.Button(self.memo_input_f, text="삭제", bg='#e74c3c', fg='white', bd=0, font=self.font_title, command=self.delete_memo).pack(side='left', padx=1)
        tk.Button(self.memo_input_f, text="전체삭제", bg='#c0392b', fg='white', bd=0, font=self.font_title, command=self.delete_all_memos).pack(side='left', padx=1)
        self.memo_expand_btn = tk.Button(self.memo_input_f, text="▼ 확장", bg='#8e44ad', fg='white', bd=0, font=self.font_title, command=self.toggle_memo_expand); self.memo_expand_btn.pack(side='right', padx=1)
        
        self.memo_list_f = tk.Frame(self.memo_frame); self.memo_list_f.pack(side='bottom', fill='both', expand=True, pady=(0, 4))
        self.memo_sb = tk.Scrollbar(self.memo_list_f); self.memo_sb.pack(side='right', fill='y')
        init_height = 10 if self.show_memo_expanded else 4
        self.memo_text = tk.Text(self.memo_list_f, height=init_height, font=self.font_title, cursor="arrow", spacing1=2, spacing3=2, yscrollcommand=self.memo_sb.set); self.memo_text.pack(side='left', fill='both', expand=True)
        self.memo_sb.config(command=self.memo_text.yview)
        
        self.memo_text.tag_configure("strike", overstrike=True, foreground="#95a5a6"); self.memo_text.tag_configure("selected", background="#f1c40f"); self.memo_text.tag_configure("important_star", foreground="#f39c12")
        self.memo_text.bind("<Button-1>", self.on_memo_click); self.memo_text.bind("<Double-Button-1>", self.on_memo_double_click); self.memo_text.bind("<Button-3>", self.show_memo_context_menu)

        self.create_grid(); self.apply_row_visibility(); self.refresh_memo_list()
        
        if self.show_memo: self.memo_frame.pack(side='bottom', fill='x', padx=4, pady=(0, 4))
        
        self.sizegrip_nw = tk.Frame(self.root, cursor="size_nw_se"); self.sizegrip_nw.place(relx=0, rely=0, width=8, height=8)
        self.sizegrip_ne = tk.Frame(self.root, cursor="size_ne_sw"); self.sizegrip_ne.place(relx=1, rely=0, anchor='ne', width=8, height=8)
        self.sizegrip_sw = tk.Frame(self.root, cursor="size_ne_sw"); self.sizegrip_sw.place(relx=0, rely=1, anchor='sw', width=8, height=8)
        self.sizegrip_se = tk.Frame(self.root, cursor="size_nw_se"); self.sizegrip_se.place(relx=1, rely=1, anchor='se', width=8, height=8)
        for grip, corner in [(self.sizegrip_nw, 'nw'), (self.sizegrip_ne, 'ne'), (self.sizegrip_sw, 'sw'), (self.sizegrip_se, 'se')]: grip.bind("<Button-1>", self.start_resize); grip.bind("<B1-Motion>", lambda e, c=corner: self.do_resize(e, c))
        self.update_lock_visuals()

    def update_settings_menu(self):
        self.settings_menu.delete(0, 'end')
        u = self.settings.get('logged_in_user')
        if u:
            self.settings_menu.add_command(label=f"👤 {u}님 (로그아웃)", command=self.logout)
            if u == "표민호": self.settings_menu.add_command(label="👨‍🏫 [관리자] 비번 초기화", command=self.reset_user_password)
            self.settings_menu.add_separator()
        self.settings_menu.add_command(label="🔓 화면 고정 풀기" if self.is_locked else "🔒 화면 고정하기", command=self.toggle_lock)
        self.settings_menu.add_command(label="⏬ 일반창 변경" if self.is_topmost else "⏫ 항상 위 고정", command=self.toggle_topmost)
        self.settings_menu.add_separator()
        f_menu = tk.Menu(self.settings_menu, tearoff=0, font=('맑은 고딕', 9))
        for f in ["맑은 고딕", "바탕", "돋움", "굴림", "Arial"]: f_menu.add_command(label=f, command=lambda val=f: self.apply_font(val))
        self.settings_menu.add_cascade(label="A 폰트 변경", menu=f_menu)
        t_menu = tk.Menu(self.settings_menu, tearoff=0, font=('맑은 고딕', 9))
        for i, t in enumerate(self.themes): t_menu.add_command(label=t['name'], command=lambda idx=i: self.apply_specific_theme(idx))
        self.settings_menu.add_cascade(label="🎨 테마 변경", menu=t_menu)
        alpha_menu = tk.Menu(self.settings_menu, tearoff=0, font=('맑은 고딕', 9))
        for a in [100, 90, 80, 70, 60, 50]: alpha_menu.add_command(label=f"{a}%", command=lambda val=a: self.apply_alpha(val))
        self.settings_menu.add_cascade(label="💧 투명도 조절", menu=alpha_menu)
        scale_menu = tk.Menu(self.settings_menu, tearoff=0, font=('맑은 고딕', 9))
        for s in ["80%", "100%", "120%", "150%", "200%"]: scale_menu.add_command(label=s, command=lambda val=s: self.apply_scale(val))
        self.settings_menu.add_cascade(label="🔍 화면 배율", menu=scale_menu)
        self.settings_menu.add_separator()
        self.settings_menu.add_command(label="📥 메모 가져오기 (.txt/.csv)", command=self.import_memos)
        self.settings_menu.add_command(label="📤 메모 내보내기 (.txt/.csv)", command=self.export_memos)
        self.settings_menu.add_command(label="🔄 크기 초기화", command=self.reset_size)

    def manual_save_db(self):
        u = self.settings.get('logged_in_user')
        if not u or not USE_SUPABASE: messagebox.showinfo("저장", "로컬 저장 완료."); return
        try:
            requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{u}", headers=HEADERS, json={"theme_idx": self.current_theme_idx, "font_name": self.settings.get('font_family', '맑은 고딕'), "show_zero": self.show_zero, "show_extra": self.show_extra, "show_memo": self.show_memo}, verify=False)
            if u in self.custom_data:
                for dk, sub in self.custom_data[u].items(): 
                    requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule?on_conflict=teacher_name,date_key", headers=HEADERS_UPSERT, json={"teacher_name": u, "date_key": dk, "subject": sub}, verify=False)
            if u in self.memos_data:
                for m in self.memos_data[u]:
                    if 'id' not in m:
                        r = requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": u, "memo_text": m['text'], "is_strike": m.get('strike', False), "is_important": m.get('important', False)}, verify=False)
                        if r.status_code in [200, 201] and len(r.json()) > 0: m['id'] = r.json()[0]['id']
            messagebox.showinfo("성공", "클라우드 동기화 완료!")
        except Exception as e: messagebox.showerror("에러", str(e))

    def reset_user_password(self):
        target = simpledialog.askstring("관리자", "초기화할 이름:", parent=self.root)
        if target:
            requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{target}", headers=HEADERS, json={"password": "1234"}, verify=False)
            messagebox.showinfo("성공", f"{target} 선생님의 비밀번호가 1234로 초기화됨.")

    def logout(self): 
        self.settings['logged_in_user'] = None; self.settings['auto_login'] = False
        self.save_settings(); self.build_login_ui()
    
    def on_alpha_slide(self, val): self.root.attributes('-alpha', float(val)); self.settings['alpha'] = float(val)
    def apply_alpha(self, percent): val = percent/100.0; self.alpha_var.set(val); self.on_alpha_slide(val)
    def apply_font(self, f_n): self.settings['font_family'] = f_n; [f.config(family=f_n) for f in [self.font_title, self.font_head, self.font_period, self.font_cell, self.font_cell_strike]]; self.save_settings()
    def apply_specific_theme(self, idx): self.current_theme_idx = idx; self.apply_theme(); self.refresh_schedule_display(); self.save_settings()
    def apply_scale(self, v): r = int(v[:-1])/100.0; nw, nh = int(608*r), int(self.base_height_core*r); self.root.geometry(f"{nw}x{nh}"); self.update_font_size(nw, nh)

    def refresh_memo_list(self):
        u = self.teacher_var.get()
        if not u: return
        
        self.memo_text.config(state='normal')
        self.memo_text.delete('1.0', tk.END)
        
        if u not in self.memos_data or not self.memos_data[u]:
            self.memo_text.config(state='disabled')
            return
            
        total = len(self.memos_data[u])
        for i, m in enumerate(self.memos_data[u]):
            pref = "★ " if m.get('important') else ""
            clean_text, color = self.parse_text_color(m['text'])
            start_idx = f"{i+1}.0"
            end_idx = f"{i+1}.end"
            
            self.memo_text.insert(tk.END, f"{pref}{total-i}. {clean_text}\n")
            
            if color:
                tag_name = f"color_{i}"
                self.memo_text.tag_configure(tag_name, foreground=color)
                self.memo_text.tag_add(tag_name, start_idx, end_idx)
                
            if m.get('strike'): self.memo_text.tag_add("strike", start_idx, end_idx)
            if m.get('important'): self.memo_text.tag_add("important_star", start_idx, f"{i+1}.2")
            if self.selected_memo_idx == i: self.memo_text.tag_add("selected", start_idx, end_idx)
        self.memo_text.config(state='disabled')

    def on_memo_click(self, ev):
        u = self.teacher_var.get()
        if not u or u not in self.memos_data: return
        idx_str = self.memo_text.index(f"@{ev.x},{ev.y}")
        self.selected_memo_idx = int(idx_str.split('.')[0]) - 1; self.refresh_memo_list()

    def on_memo_double_click(self, ev): self.edit_memo(); return "break"
    
    def show_memo_context_menu(self, ev):
        menu = tk.Menu(self.root, tearoff=0, font=('맑은 고딕', 9))
        menu.add_command(label="완료(취소선)", command=self.toggle_memo_strike)
        menu.add_command(label="수정", command=self.edit_memo)
        menu.add_command(label="삭제", command=self.delete_memo)
        menu.add_command(label="중요(⭐)", command=self.toggle_memo_important)
        
        color_menu = tk.Menu(menu, tearoff=0, font=('맑은 고딕', 9))
        colors = [("기본색(초기화)", ""), ("빨간색", "#e74c3c"), ("파란색", "#3498db"), ("초록색", "#27ae60"), ("보라색", "#9b59b6"), ("검정색", "#333333")]
        for name, code in colors:
            color_menu.add_command(label=name, command=lambda c=code: self.change_memo_color(c))
        menu.add_cascade(label="글자색 변경", menu=color_menu)
        
        menu.tk_popup(ev.x_root, ev.y_root)

    def toggle_memo_strike(self):
        u = self.teacher_var.get()
        if u and self.selected_memo_idx is not None and self.selected_memo_idx < len(self.memos_data[u]):
            m = self.memos_data[u][self.selected_memo_idx]; m['strike'] = not m.get('strike', False)
            if USE_SUPABASE and 'id' in m: requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{m['id']}", headers=HEADERS, json={"is_strike": m['strike']}, verify=False)
            self.refresh_memo_list(); self.save_memos()

    def toggle_memo_important(self):
        u = self.teacher_var.get()
        if u and self.selected_memo_idx is not None and self.selected_memo_idx < len(self.memos_data[u]):
            m = self.memos_data[u][self.selected_memo_idx]; m['important'] = not m.get('important', False)
            if USE_SUPABASE and 'id' in m: requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{m['id']}", headers=HEADERS, json={"is_important": m['important']}, verify=False)
            self.refresh_memo_list(); self.save_memos()

    def change_memo_color(self, color):
        u = self.teacher_var.get()
        if u and self.selected_memo_idx is not None and self.selected_memo_idx < len(self.memos_data[u]):
            m = self.memos_data[u][self.selected_memo_idx]
            clean_text, _ = self.parse_text_color(m['text'])
            if color: new_t = f'<span style="color:{color}">{clean_text}</span>'
            else: new_t = clean_text
            m['text'] = new_t
            if USE_SUPABASE and 'id' in m:
                try: requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{m['id']}", headers=HEADERS, json={"memo_text": new_t}, verify=False)
                except: pass
            self.refresh_memo_list(); self.save_memos()

    def add_memo(self, ev=None):
        u, text = self.teacher_var.get(), self.memo_entry.get().strip()
        if u and text:
            if USE_SUPABASE:
                try:
                    r = requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": u, "memo_text": text}, verify=False)
                    if r.status_code in [200, 201] and len(r.json()) > 0: self.memos_data.setdefault(u, []).insert(0, {'id': r.json()[0]['id'], 'text': text, 'strike': False, 'important': False})
                    else: self.memos_data.setdefault(u, []).insert(0, {'text': text, 'strike': False, 'important': False})
                except: self.memos_data.setdefault(u, []).insert(0, {'text': text, 'strike': False, 'important': False})
            else: self.memos_data.setdefault(u, []).insert(0, {'text': text, 'strike': False, 'important': False})
            self.memo_entry.delete(0, tk.END); self.refresh_memo_list(); self.save_memos()

    def edit_memo(self):
        u = self.teacher_var.get()
        if u and self.selected_memo_idx is not None and self.selected_memo_idx < len(self.memos_data[u]):
            m = self.memos_data[u][self.selected_memo_idx]
            clean_text, old_color = self.parse_text_color(m['text'])
            new_t = simpledialog.askstring("수정", "내용:", initialvalue=clean_text)
            if new_t:
                save_t = f'<span style="color:{old_color}">{new_t.strip()}</span>' if old_color else new_t.strip()
                m['text'] = save_t
                if USE_SUPABASE and 'id' in m: requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{m['id']}", headers=HEADERS, json={"memo_text": save_t}, verify=False)
                self.refresh_memo_list(); self.save_memos()

    def delete_memo(self):
        u = self.teacher_var.get()
        if u and self.selected_memo_idx is not None and self.selected_memo_idx < len(self.memos_data[u]):
            m = self.memos_data[u][self.selected_memo_idx]
            if USE_SUPABASE and 'id' in m: requests.delete(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{m['id']}", headers=HEADERS, verify=False)
            del self.memos_data[u][self.selected_memo_idx]; self.selected_memo_idx = None; self.refresh_memo_list(); self.save_memos()

    def delete_all_memos(self):
        u = self.teacher_var.get()
        if u and messagebox.askyesno("삭제", "전부 삭제?"):
            if USE_SUPABASE: requests.delete(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{u}", headers=HEADERS, verify=False)
            self.memos_data[u] = []; self.refresh_memo_list(); self.save_memos()

    def export_memos(self):
        u = self.teacher_var.get(); path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for m in self.memos_data.get(u, []): 
                    clean_text, _ = self.parse_text_color(m['text'])
                    f.write(f"{'[완료]' if m.get('strike') else ''}{clean_text}\n")

    def import_memos(self):
        u = self.teacher_var.get(); path = filedialog.askopenfilename()
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f: self.memos_data.setdefault(u, []).insert(0, {'text': line.strip(), 'strike': False})
            except:
                with open(path, 'r', encoding='cp949') as f:
                    for line in f: self.memos_data.setdefault(u, []).insert(0, {'text': line.strip(), 'strike': False})
            self.refresh_memo_list(); self.save_memos()

    def toggle_memo_expand(self):
        self.show_memo_expanded = not self.show_memo_expanded; self.memo_text.config(height=10 if self.show_memo_expanded else 4); self.memo_expand_btn.config(text="▲ 축소" if self.show_memo_expanded else "▼ 확장"); self.resize_window_for_rows()

    @property
    def base_height_core(self):
        h = 445
        if self.show_zero: h += 40
        if self.show_extra: h += 80
        if self.show_memo: h += 220 if self.show_memo_expanded else 110 
        return h

    def toggle_memo(self):
        self.show_memo = not self.show_memo
        if self.show_memo: self.memo_frame.pack(side='bottom', fill='x', padx=4, pady=(0, 4))
        else: self.memo_frame.pack_forget()
        self.resize_window_for_rows()

    def toggle_zero(self): self.show_zero = not self.show_zero; self.resize_window_for_rows()
    def toggle_extra(self): self.show_extra = not self.show_extra; self.resize_window_for_rows()
    
    def resize_window_for_rows(self):
        nh = self.base_height_core; self.root.geometry(f"{self.root.winfo_width()}x{nh}"); self.apply_row_visibility(); self.apply_theme(); self.update_font_size(self.root.winfo_width(), nh); self.save_settings()
    
    def apply_row_visibility(self):
        if self.show_zero:
            self.grid_frame.rowconfigure(1, weight=1); self.cells["period_1"].grid()
            for c in range(1,6): self.cells[f"cell_1_{c}"].grid()
        else:
            self.grid_frame.rowconfigure(1, weight=0); self.cells["period_1"].grid_remove()
            for c in range(1,6): self.cells[f"cell_1_{c}"].grid_remove()
        for r in [10,11]:
            if self.show_extra:
                self.grid_frame.rowconfigure(r, weight=1); self.cells[f"period_{r}"].grid()
                for c in range(1,6): self.cells[f"cell_{r}_{c}"].grid()
            else:
                self.grid_frame.rowconfigure(r, weight=0); self.cells[f"period_{r}"].grid_remove()
                for c in range(1,6): self.cells[f"cell_{r}_{c}"].grid_remove()

    def prev_week(self): self.week_offset -= 1; self.refresh_schedule_display(); self.update_time_and_date()
    def next_week(self): self.week_offset += 1; self.refresh_schedule_display(); self.update_time_and_date()
    def curr_week(self): self.week_offset = 0; self.refresh_schedule_display(); self.update_time_and_date()

    def create_grid(self):
        for r in range(len(self.period_times)+1): self.grid_frame.rowconfigure(r, weight=1)
        for c in range(6): self.grid_frame.columnconfigure(c, weight=1)
        self.corner_lbl = tk.Label(self.grid_frame, text="교시", font=self.font_head, highlightthickness=2); self.corner_lbl.grid(row=0, column=0, sticky='nsew', pady=1, padx=1)
        for c, day in enumerate(self.days, 1):
            lbl = tk.Label(self.grid_frame, text=day, font=self.font_head, highlightthickness=2); lbl.grid(row=0, column=c, sticky='nsew', pady=1, padx=1); self.cells[f"header_{c}"] = lbl
        for r, (p, s, e) in enumerate(self.period_times, 1):
            p_lbl = tk.Label(self.grid_frame, text=f"{p}\n{s}~{e}", font=self.font_period, highlightthickness=2); p_lbl.grid(row=r, column=0, sticky='nsew', pady=1, padx=1); p_lbl.bind('<Button-1>', self.click_window); p_lbl.bind('<B1-Motion>', self.drag_window); self.cells[f"period_{r}"] = p_lbl
            for c in range(1, 6):
                cell = tk.Label(self.grid_frame, text="", font=self.font_cell, height=2, highlightthickness=2, cursor="hand2"); cell.grid(row=r, column=c, sticky='nsew', pady=1, padx=1)
                cell.bind("<Button-1>", lambda ev, r=r, c=c: self.on_cell_single_click(ev, r, c)); cell.bind("<Double-Button-1>", lambda ev, r=r, c=c: self.on_cell_double_click(ev, r, c)); cell.bind("<Button-3>", lambda ev, r=r, c=c: self.show_cell_context_menu(ev, r, c)); self.cells[f"cell_{r}_{c}"] = cell

        self.refresh_schedule_display()

    def show_cell_context_menu(self, event, row, col):
        teacher = self.teacher_var.get()
        if not teacher: return
        
        menu = tk.Menu(self.root, tearoff=0, font=('맑은 고딕', 9))
        menu.add_command(label="입력/수정", command=lambda: self.process_single_click(row, col))
        menu.add_command(label="완료(취소선)", command=lambda: self.process_double_click(row, col))
        menu.add_command(label="삭제", command=lambda: self.delete_cell_data(row, col))
        
        color_menu = tk.Menu(menu, tearoff=0, font=('맑은 고딕', 9))
        colors = [("기본색(초기화)", ""), ("빨간색", "#e74c3c"), ("파란색", "#3498db"), ("초록색", "#27ae60"), ("보라색", "#9b59b6"), ("검정색", "#333333")]
        for name, code in colors:
            color_menu.add_command(label=name, command=lambda r=row, c=col, color=code: self.change_cell_color(r, c, color))
        menu.add_cascade(label="글자색 변경", menu=color_menu)
        
        menu.tk_popup(event.x_root, event.y_root)

    def change_cell_color(self, r, c, color):
        u = self.teacher_var.get()
        if not u: return
        
        monday = datetime.now() + timedelta(weeks=self.week_offset) - timedelta(days=datetime.now().weekday())
        key = f"{(monday + timedelta(days=c-1)).strftime('%Y-%m-%d')}_{r}"
        
        cur_v = self.custom_data.get(u, {}).get(key, "")
        p_n = self.period_times[r-1][0]
        
        if p_n in ["점심", "조회"]: orig = ""
        else:
            s_l = self.current_schedule.get(self.days[c-1], [])
            idx = r - 2 if r < 6 else r - 3
            orig = s_l[idx] if idx < len(s_l) else ""

        if cur_v == "__STRIKE__" or not cur_v: cur_v = orig
        if not cur_v: return
            
        clean_text, _ = self.parse_text_color(cur_v)
        
        if color: new_v = f'<span style="color:{color}">{clean_text}</span>'
        else: new_v = clean_text
            
        self.custom_data.setdefault(u, {})[key] = new_v
        if USE_SUPABASE: 
            try: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule?on_conflict=teacher_name,date_key", headers=HEADERS_UPSERT, json={"teacher_name": u, "date_key": key, "subject": new_v}, verify=False)
            except: pass
        self.save_custom_data()
        self.refresh_schedule_display()
        # 💡 [핵심] 딜레이 없이 0.1초 만에 화면에 즉시 색상을 렌더링하는 코드 추가
        self.update_time_and_date()

    def delete_cell_data(self, row, col):
        teacher = self.teacher_var.get()
        if not teacher: return

        now = datetime.now()
        target_date = now + timedelta(weeks=self.week_offset)
        monday = target_date - timedelta(days=target_date.weekday())
        cell_date = monday + timedelta(days=col-1)
        date_key = f"{cell_date.strftime('%Y-%m-%d')}_{row}"

        if teacher in self.custom_data and date_key in self.custom_data[teacher]:
            del self.custom_data[teacher][date_key]
            
            if USE_SUPABASE:
                try: requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{teacher}&date_key=eq.{date_key}", headers=HEADERS, verify=False)
                except: pass
                
            self.save_custom_data()
            self.refresh_schedule_display()
            self.update_time_and_date()

    def on_cell_single_click(self, event, row, col):
        if self.click_timer:
            self.root.after_cancel(self.click_timer)
        self.click_timer = self.root.after(250, lambda: self.process_single_click(row, col))

    def on_cell_double_click(self, event, row, col):
        if self.click_timer:
            self.root.after_cancel(self.click_timer)
            self.click_timer = None
        self.process_double_click(row, col)

    def process_single_click(self, r, c):
        self.click_timer = None
        u = self.teacher_var.get()
        if not u: return
        
        monday = datetime.now() + timedelta(weeks=self.week_offset) - timedelta(days=datetime.now().weekday())
        key = f"{(monday + timedelta(days=c-1)).strftime('%Y-%m-%d')}_{r}"
        
        p_n = self.period_times[r-1][0]
        if p_n in ["점심", "조회"]:
            orig = ""
        else:
            s_l = self.current_schedule.get(self.days[c-1], [])
            idx = r - 2 if r < 6 else r - 3
            orig = s_l[idx] if idx < len(s_l) else ""
            
        cur_v = self.custom_data.get(u, {}).get(key, orig)
        if cur_v == "__STRIKE__": 
            cur_v = ""
            old_color = None
        else:
            cur_v, old_color = self.parse_text_color(cur_v)
        
        new_v = simpledialog.askstring("입력/수정", "내용을 입력하세요 (수정 시 덮어씁니다):", parent=self.root, initialvalue=cur_v)
        if new_v is not None:
            if not new_v.strip(): 
                self.custom_data.get(u, {}).pop(key, None)
                if USE_SUPABASE: 
                    try: requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{u}&date_key=eq.{key}", headers=HEADERS, verify=False)
                    except: pass
            else: 
                save_v = f'<span style="color:{old_color}">{new_v.strip()}</span>' if old_color else new_v.strip()
                self.custom_data.setdefault(u, {})[key] = save_v
                if USE_SUPABASE: 
                    try: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule?on_conflict=teacher_name,date_key", headers=HEADERS_UPSERT, json={"teacher_name": u, "date_key": key, "subject": save_v}, verify=False)
                    except: pass
            self.save_custom_data()
            self.refresh_schedule_display()
            # 💡 [추가] 즉시 업데이트 
            self.update_time_and_date()

    def process_double_click(self, r, c):
        u = self.teacher_var.get()
        if not u: return
        
        monday = datetime.now() + timedelta(weeks=self.week_offset) - timedelta(days=datetime.now().weekday())
        key = f"{(monday + timedelta(days=c-1)).strftime('%Y-%m-%d')}_{r}"
        
        if key in self.custom_data.get(u, {}):
            if self.custom_data[u][key] == "__STRIKE__": 
                self.custom_data[u].pop(key)
                if USE_SUPABASE: 
                    try: requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{u}&date_key=eq.{key}", headers=HEADERS, verify=False)
                    except: pass
            else: 
                self.custom_data[u][key] = "__STRIKE__"
                if USE_SUPABASE: 
                    try: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule?on_conflict=teacher_name,date_key", headers=HEADERS_UPSERT, json={"teacher_name": u, "date_key": key, "subject": "__STRIKE__"}, verify=False)
                    except: pass
        else:
            self.custom_data.setdefault(u, {})[key] = "__STRIKE__"
            if USE_SUPABASE: 
                try: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule?on_conflict=teacher_name,date_key", headers=HEADERS_UPSERT, json={"teacher_name": u, "date_key": key, "subject": "__STRIKE__"}, verify=False)
                except: pass
        self.save_custom_data()
        self.refresh_schedule_display()
        # 💡 [추가] 즉시 업데이트 
        self.update_time_and_date()

    def update_font_size(self, w, h):
        s = min(w/608, h/self.base_height_core)
        for f, sz in [(self.font_head, 10), (self.font_period, 8), (self.font_cell, 10), (self.font_cell_strike, 10)]: f.config(size=max(8, int(sz*s)))

    def reset_size(self): self.root.geometry(f"608x{self.base_height_core}"); self.update_font_size(608, self.base_height_core); self.save_settings()
    def start_resize(self, ev): self._rsx, self._rsy, self._sw, self._sh, self._sx, self._sy = ev.x_root, ev.y_root, self.root.winfo_width(), self.root.winfo_height(), self.root.winfo_x(), self.root.winfo_y()
    def do_resize(self, ev, c):
        dx, dy = ev.x_root - self._rsx, ev.y_root - self._rsy; mw, mh = int(608*0.8), int(self.base_height_core*0.8); nw, nh, nx, ny = self._sw, self._sh, self._sx, self._sy
        if 'e' in c: nw = max(mw, self._sw+dx)
        if 'w' in c: nw = max(mw, self._sw-dx); nx = self._sx+(self._sw-nw)
        if 's' in c: nh = max(mh, self._sh+dy)
        if 'n' in c: nh = max(mh, self._sh-dy); ny = self._sy+(self._sh-nh)
        self.root.geometry(f"{nw}x{nh}+{nx}+{ny}"); self.update_font_size(nw, nh)

    def apply_theme(self):
        t = self.themes[self.current_theme_idx]; self.root.configure(bg=t['bg']); self.title_bar.configure(bg=t['titlebar_bg']); self.title_lbl.configure(bg=t['titlebar_bg'], fg=t.get('head_fg', 'white'))
        for b in [self.min_btn, self.max_btn, self.close_btn]: b.configure(bg=t['titlebar_bg'], fg=t.get('head_fg', 'white'))
        for f in [self.top_bar, self.left_frame, self.right_frame]: f.configure(bg=t['top'])
        self.grid_frame.configure(bg=t['grid']); self.memo_frame.configure(bg=t['bg']); self.memo_input_f.configure(bg=t['bg']); self.memo_list_f.configure(bg=t['bg']); self.memo_text.configure(bg=t['cell_bg'], fg=t['cell_fg'])
        self.corner_lbl.configure(bg=t['head_bg'], fg=t['head_fg'], highlightbackground=t['head_bg'])
        for g in [self.sizegrip_nw, self.sizegrip_ne]: g.configure(bg=t['top'])
        for g in [self.sizegrip_sw, self.sizegrip_se]: g.configure(bg=t['bg'])
        for b in [self.curr_btn, self.prev_btn, self.next_btn]: b.configure(bg=t['head_bg'], fg=t['head_fg'])
        self.alpha_lbl.configure(bg=t['top'], fg=t.get('head_fg', 'white')); self.zero_btn.config(text="조회-", bg='#e74c3c', fg='white') if self.show_zero else self.zero_btn.config(text="조회+", bg=t['head_bg'], fg=t['head_fg'])
        self.extra_btn.config(text="8,9교시-", bg='#e74c3c', fg='white') if self.show_extra else self.extra_btn.config(text="8,9교시+", bg=t['head_bg'], fg=t['head_fg'])
        if not self.show_memo: self.memo_btn.config(bg=t['head_bg'], fg=t['head_fg'])

    def on_teacher_select(self, ev=None): self.current_schedule = self.teachers_data.get(self.teacher_var.get(), {d: [""]*9 for d in self.days}); self.week_offset = 0; self.selected_memo_idx = None; self.refresh_schedule_display(); self.refresh_memo_list(); self.save_settings()
    def toggle_lock(self): self.is_locked = not self.is_locked; self.update_lock_visuals(); self.update_settings_menu(); self.save_settings()
    def update_lock_visuals(self):
        cursor = "arrow" if self.is_locked else "fleur"; self.corner_lbl.config(cursor=cursor)
        for r in range(1, len(self.period_times)+1): 
            if f"period_{r}" in self.cells: self.cells[f"period_{r}"].config(cursor=cursor)
        self.sizegrip_nw.config(cursor="arrow" if self.is_locked else "size_nw_se")
        self.sizegrip_ne.config(cursor="arrow" if self.is_locked else "size_ne_sw")
        self.sizegrip_sw.config(cursor="arrow" if self.is_locked else "size_ne_sw")
        self.sizegrip_se.config(cursor="arrow" if self.is_locked else "size_nw_se")
    def toggle_topmost(self): self.is_topmost = not self.is_topmost; self.root.attributes('-topmost', self.is_topmost); self.update_settings_menu(); self.save_settings()
    def click_window(self, ev):
        if not self.is_locked: self._offset_x, self._offset_y = ev.x, ev.y
    def drag_window(self, ev):
        if not self.is_locked: self.root.geometry(f"+{self.root.winfo_x() - self._offset_x + ev.x}+{self.root.winfo_y() - self._offset_y + ev.y}")

    def refresh_schedule_display(self):
        monday = datetime.now() + timedelta(weeks=self.week_offset) - timedelta(days=datetime.now().weekday()); u = self.teacher_var.get(); data = self.custom_data.get(u, {})
        for r, (p, s, e) in enumerate(self.period_times, 1):
            for c, d in enumerate(self.days, 1):
                key = f"{(monday+timedelta(days=c-1)).strftime('%Y-%m-%d')}_{r}"; sub = "" if p in ["점심", "조회"] else self.current_schedule.get(d, [""]*9)[r-2 if r<6 else r-3]
                
                if key in data:
                    if data[key] != "__STRIKE__":
                        clean_sub, _ = self.parse_text_color(data[key])
                        sub = clean_sub
                    else: sub = ""
                
                self.cells[f"cell_{r}_{c}"].config(text=sub)

    def update_time_and_date(self):
        now = datetime.now(); mnd = now + timedelta(weeks=self.week_offset) - timedelta(days=now.weekday()); t = self.themes[self.current_theme_idx]; cur_d = now.weekday() + 1; is_cur_w = (self.week_offset == 0)
        for c, d in enumerate(self.days, 1):
            self.cells[f"header_{c}"].config(text=f"{d} ({(mnd+timedelta(days=c-1)).strftime('%m/%d')})", bg=t['hl_per'] if (is_cur_w and c==cur_d) else t['head_bg'], fg='white' if (is_cur_w and c==cur_d and t['name']!='웜 파스텔') else t['head_fg'])
        now_m = now.hour*60+now.minute; act_r, pre_r = None, None
        for r, (p, s, e) in enumerate(self.period_times, 1):
            sm, em = int(s.split(':')[0])*60+int(s.split(':')[1]), int(e.split(':')[0])*60+int(e.split(':')[1])
            if sm <= now_m <= em: act_r = r; pre_r = r+1 if p=="점심" else None; break
            elif now_m < sm: pre_r = r; break
        for r in range(1, len(self.period_times)+1):
            self.cells[f"period_{r}"].config(bg=t['per_bg'], fg=t['per_fg'], highlightbackground=t['per_bg'])
            for c in range(1, 6): self.cells[f"cell_{r}_{c}"].config(bg=t['lunch_bg'] if self.period_times[r-1][0] in ["점심", "조회"] else t['cell_bg'], fg=t['cell_fg'], highlightbackground=t['lunch_bg'] if self.period_times[r-1][0] in ["점심", "조회"] else t['cell_bg'])
        if is_cur_w:
            self.curr_btn_border.config(bg='#f1c40f')
            if act_r:
                self.cells[f"period_{act_r}"].config(bg=t['hl_per'], fg='white' if t['name']!='웜 파스텔' else 'black', highlightbackground=t['hl_per'])
                if 1<=cur_d<=5: self.cells[f"cell_{act_r}_{cur_d}"].config(bg=t['hl_cell'], fg='black', highlightbackground=t['hl_cell'])
            if pre_r and 1<=cur_d<=5: self.cells[f"period_{pre_r}"].config(highlightbackground=t['hl_per']); self.cells[f"cell_{pre_r}_{cur_d}"].config(highlightbackground=t['hl_cell'])
        else: self.curr_btn_border.config(bg=t['top'])
        
        u = self.teacher_var.get(); data = self.custom_data.get(u, {})
        for r in range(1, len(self.period_times)+1):
            for c in range(1, 6):
                key = f"{(mnd+timedelta(days=c-1)).strftime('%Y-%m-%d')}_{r}"
                cell_bg = self.cells[f"cell_{r}_{c}"].cget("bg")
                default_fg = '#e74c3c' if cell_bg in [t['cell_bg'], t.get('lunch_bg')] else '#c0392b'
                
                if key in data:
                    if data[key] == "__STRIKE__":
                        self.cells[f"cell_{r}_{c}"].config(font=self.font_cell_strike, fg=default_fg)
                    else:
                        _, color = self.parse_text_color(data[key])
                        self.cells[f"cell_{r}_{c}"].config(font=self.font_cell, fg=color if color else default_fg)
                else: 
                    self.cells[f"cell_{r}_{c}"].config(font=self.font_cell, fg=t['cell_fg'])
                    
        if hasattr(self, 'timer_id'): self.root.after_cancel(self.timer_id)
        self.timer_id = self.root.after(60000, self.update_time_and_date)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("교사 시간표")
    app = TimetableWidget(root)
    root.mainloop()