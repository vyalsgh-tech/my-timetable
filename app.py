import streamlit as st
import streamlit.components.v1 as components
import requests
import csv
import os
import inspect
import threading
import re
import unicodedata
import io
import glob
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

# 💡 1-1. PWA(웹앱) 전체화면 모드 강제 주입
components.html("""
<script>
    const doc = window.parent.document;
    if (!doc.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
        const meta1 = doc.createElement('meta'); meta1.name = "apple-mobile-web-app-capable"; meta1.content = "yes"; doc.head.appendChild(meta1);
        const meta2 = doc.createElement('meta'); meta2.name = "mobile-web-app-capable"; meta2.content = "yes"; doc.head.appendChild(meta2);
        const meta3 = doc.createElement('meta'); meta3.name = "apple-mobile-web-app-status-bar-style"; meta3.content = "black-translucent"; doc.head.appendChild(meta3);
        const icon = doc.createElement('link'); icon.rel = "apple-touch-icon"; icon.href = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f3eb.png"; doc.head.appendChild(icon);
    }
</script>
""", height=0, width=0)

# 💡 URL 파라미터를 통한 상태 완벽 복구
params = st.query_params
if "user" in params and 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = params["user"]
if "t" in params:
    st.session_state.teacher = params["t"]

if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0
if 'show_zero' not in st.session_state: st.session_state.show_zero = False
if 'show_extra' not in st.session_state: st.session_state.show_extra = False
if 'show_memo' not in st.session_state: st.session_state.show_memo = True 
# 💡 [버그 해결] 강제로 '표민호'로 덮어씌워지던 로직을 로그인된 유저 우선으로 변경
if 'teacher' not in st.session_state: 
    st.session_state.teacher = st.session_state.logged_in_user if st.session_state.logged_in_user else "표민호"
if 'theme_idx' not in st.session_state: st.session_state.theme_idx = 0
if 'font_name' not in st.session_state: st.session_state.font_name = "맑은 고딕"

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'text': '#ffffff',
      'acad_per_bg': '#8e44ad', 'acad_per_fg': 'white', 'acad_cell_bg': '#413a52', 'acad_cell_fg': '#f1c40f' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'text': '#333333',
      'acad_per_bg': '#ffdac1', 'acad_per_fg': '#333333', 'acad_cell_bg': '#ffe5d9', 'acad_cell_fg': '#5c4d3c' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'text': '#2c3e50',
      'acad_per_bg': '#1abc9c', 'acad_per_fg': 'white', 'acad_cell_bg': '#d1f2eb', 'acad_cell_fg': '#0e6251' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'text': '#1a3026',
      'acad_per_bg': '#d35400', 'acad_per_fg': 'white', 'acad_cell_bg': '#fad7a1', 'acad_cell_fg': '#6e2c00' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'text': '#222222',
      'acad_per_bg': '#424242', 'acad_per_fg': 'white', 'acad_cell_bg': '#cfcfcf', 'acad_cell_fg': '#000000' }
]
t = themes[st.session_state.theme_idx]

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}

def update_db_bg(url, headers, user, key, val):
    try: requests.patch(f"{url}/rest/v1/users?teacher_name=eq.{user}", headers=headers, json={key: val}, timeout=3)
    except: pass

def verify_and_load_user(user_id):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{user_id}", headers=HEADERS)
    if r.status_code == 200 and len(r.json()) > 0:
        u_data = r.json()[0]
        st.session_state.theme_idx = u_data.get('theme_idx', 0)
        st.session_state.font_name = u_data.get('font_name', '맑은 고딕')
        st.session_state.show_zero = u_data.get('show_zero', False)
        st.session_state.show_extra = u_data.get('show_extra', False)
        st.session_state.show_memo = u_data.get('show_memo', True)
        return u_data
    return None

if st.session_state.logged_in_user:
    verify_and_load_user(st.session_state.logged_in_user)

# --- 로그인 화면 ---
if st.session_state.logged_in_user is None:
    st.markdown(f"<div style='text-align:center; padding: 2rem 0 1rem 0;'><div style='font-size: 3rem;'>🏫</div><h1 style='font-size: 26px; font-weight: 800;'>명덕외고 뷰어</h1></div>", unsafe_allow_html=True)
    st.info("💡 입력/수정은 PC버전을 이용해 주세요.")
    tab1, tab2 = st.tabs(["🔐 로그인", "📝 새 계정 등록"])
    with tab1:
        login_id = st.text_input("아이디 (선생님 성함)", placeholder="예: 표민호")
        login_pw = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True, type="primary"):
            if login_id and login_pw:
                u_data = verify_and_load_user(login_id)
                if u_data:
                    if u_data['password'] == login_pw:
                        st.session_state.logged_in_user = login_id
                        st.session_state.teacher = login_id
                        st.query_params["user"] = login_id 
                        st.query_params["t"] = login_id # 로그인 시 명시적으로 teacher 파라미터도 동기화
                        st.rerun()
                    else: st.error("비밀번호가 일치하지 않습니다.")
                else: st.error("등록되지 않은 선생님입니다.")
    st.stop()

# --- 데이터 로드 ---
@st.cache_data
def load_csv():
    days = ["월", "화", "수", "목", "금"]
    t_data = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, 'data.csv')
    if not os.path.exists(file_path): file_path = 'data.csv'
        
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if not row or len(row) < 36: continue
                    name = row[0]
                    periods_per_day = (len(row) - 1) // 5
                    schedule = {d: [] for d in days}
                    for i, day in enumerate(days):
                        start_idx = 1 + i * periods_per_day
                        schedule[day] = row[start_idx : start_idx + periods_per_day][:9]
                    t_data[name] = schedule
        except: pass
    return t_data

def load_academic_data():
    academic_schedule = {}
    target_file = None
    
    for filepath in glob.glob("**/*학사일정*.csv", recursive=True):
        if "수업일수" not in filepath:
            target_file = filepath
            break

    if not target_file or not os.path.exists(target_file): return {}
    
    reader = None
    for enc in ['utf-8-sig', 'cp949', 'euc-kr', 'utf-8']:
        try:
            with open(target_file, 'r', encoding=enc) as f:
                content = f.read()
                if "월" in content or "일" in content or "학" in content:
                    reader = list(csv.reader(io.StringIO(content)))
                    break
        except: pass

    if not reader: return {}
    
    try:
        header_row_idx = 0
        for i, row in enumerate(reader):
            if any("월" in str(cell) for cell in row):
                header_row_idx = i
                break
                
        header = reader[header_row_idx]
        month_cols = {}
        for col_idx, val in enumerate(header):
            m = re.search(r'(\d+)\s*월', str(val).replace(" ", ""))
            if m: month_cols[int(m.group(1))] = col_idx + 1
        
        days_of_week = ['월', '화', '수', '목', '금', '토', '일']
        
        for row in reader[header_row_idx + 1:]:
            if not row: continue
            
            day_match = re.search(r'^(\d+)', str(row[0]).strip())
            if not day_match: continue
            day = int(day_match.group(1))
            
            for month, ev_col in month_cols.items():
                event = ""
                for check_col in [ev_col, ev_col - 1, ev_col + 1]:
                    if 0 <= check_col < len(row):
                        val = str(row[check_col]).strip()
                        if val and val not in days_of_week and not val.isdigit():
                            event = val
                            break 
                
                if event:
                    year = 2026 if month >= 3 else 2027
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    if date_str in academic_schedule:
                        academic_schedule[date_str] += f"\n{event}"
                    else:
                        academic_schedule[date_str] = event
    except: pass
    return academic_schedule

teachers_data = load_csv()
academic_data = load_academic_data() 
teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]
days = ["월", "화", "수", "목", "금"]

period_times = [
    ("학사일정", "\n"),
    ("조회", "07:40\n08:00"), ("1교시", "08:00\n08:50"), ("2교시", "09:00\n09:50"),
    ("3교시", "10:00\n10:50"), ("4교시", "11:00\n11:50"), ("점심", "11:50\n12:40"),
    ("5교시", "12:40\n13:30"), ("6교시", "13:40\n14:30"), ("7교시", "14:40\n15:30"),
    ("8교시", "16:00\n16:50"), ("9교시", "17:00\n17:50")
]
kst_tz = timezone(timedelta(hours=9))

def safe_fragment_rerun():
    if "scope" in inspect.signature(st.rerun).parameters: st.rerun(scope="fragment")
    else: st.rerun()

# 💡 글로벌 CSS 설정 (절대 불변 구역)
st.markdown(f"""
<style>
    html, body, .stApp {{ touch-action: auto !important; background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; }}
    * {{ animation-duration: 0s !important; transition-duration: 0s !important; }}
    .element-container, .stMarkdown, div[data-testid="stPopoverBody"] {{ animation: none !important; transition: none !important; }}
    .block-container {{ padding: 0.5rem 0.2rem !important; max-width: 100% !important; }}
    header {{ visibility: hidden; }}
    
    .header-container {{
        width: 100% !important; max-width: 450px !important; 
        margin: 0 auto 5px 0 !important; display: flex !important; align-items: center; padding-left: 2px; color: {t['text']} !important;
    }}
    
    div[data-testid="stHorizontalBlock"] {{
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important;
        background-color: {t['top']} !important; padding: 4px 4px !important; border-radius: 8px !important; margin-bottom: 10px !important;
        width: 100% !important; max-width: 450px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; gap: 2px !important;
    }}
    
    div[data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0px !important; 
        width: auto !important; min-width: 0px !important; max-width: none !important; 
        padding: 0 !important; margin: 0 !important; display: block !important;
    }}
    
    div[data-testid="stHorizontalBlock"] > div:nth-child(1),
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) {{
        flex: 0 0 32px !important; width: 32px !important; min-width: 32px !important;
    }}
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) {{
        flex: 0 0 65px !important; width: 65px !important; min-width: 65px !important;
    }}
    
    div[data-testid="stHorizontalBlock"] .stButton > button {{
        height: 34px !important; border-radius: 6px !important; font-size: 13px !important; font-weight: bold !important;
        padding: 0 !important; line-height: 1 !important; width: 100% !important; min-width: 0 !important; display: block !important;
    }}
    div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"] {{
        background-color: transparent !important; color: {t['text']} !important; border: none !important;
    }}
    div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {{
        background-color: {t['hl_per']} !important; color: #ffffff !important; border: none !important; box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
    }}
    div[data-testid="stHorizontalBlock"] .stButton > button:active {{ opacity: 0.6 !important; }}
    
    div[data-testid="stHorizontalBlock"] div[data-testid="stPopover"] > button {{
        font-size: 15px !important; height: 34px !important; padding: 0 !important; width: 100% !important;
        border: none !important; background-color: transparent !important; color: {t['text']} !important; min-width: 0 !important;
    }}
    div[data-testid="stPopover"] svg {{ display: none !important; }}
    
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 14px; }}
    .mobile-table th {{ border: 1px solid {t['grid']}; padding: 4px 1px; text-align: center; height: 45px; }}
    .mobile-table td {{ border: 1px solid {t['grid']}; padding: 0px; text-align: center; vertical-align: middle; height: 65px; word-break: keep-all; font-weight: bold; font-size: 14px; }}
    .hl-border-red {{ box-shadow: inset 0 0 0 3px {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ box-shadow: inset 0 0 0 3px {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; box-shadow: inset 0 0 0 3px #d4ac0d !important; }}

    .memo-container {{
        height: 300px; overflow-y: auto; border: 1px solid {t['grid']}; border-radius: 6px; padding: 6px;
        scrollbar-width: thin; scrollbar-color: rgba(150, 150, 150, 0.5) transparent;
    }}
    .memo-container::-webkit-scrollbar {{ width: 6px; }}
    .memo-container::-webkit-scrollbar-track {{ background: transparent; }}
    .memo-container::-webkit-scrollbar-thumb {{ background-color: rgba(150, 150, 150, 0.5); border-radius: 10px; }}
    .memo-container::-webkit-scrollbar-thumb:hover {{ background-color: rgba(150, 150, 150, 0.8); }}
</style>
""", unsafe_allow_html=True)

u = st.session_state.logged_in_user
st.markdown(f"<div class='header-container'><div style='font-size:16px; font-weight:800; white-space:nowrap;'>🏫 명덕외고 시간표 뷰어 <span style='font-size:13px; font-weight:normal;'>({u} 선생님)</span></div></div>", unsafe_allow_html=True)

@st.fragment
def display_dashboard():
    
    custom_data = {}
    memos_list = []
    try:
        r_cust = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}", headers=HEADERS)
        if r_cust.status_code == 200: custom_data = {row['date_key']: row['subject'] for row in r_cust.json()}
        r_memo = requests.get(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}&order=created_at.desc", headers=HEADERS)
        if r_memo.status_code == 200: memos_list = r_memo.json()
    except: pass

    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    with c1:
        if st.button("◀", use_container_width=True, key="prev"): 
            st.session_state.week_offset -= 1; safe_fragment_rerun()
    with c2:
        btn_type = "primary" if st.session_state.week_offset == 0 else "secondary"
        if st.button("이번주", use_container_width=True, type=btn_type, key="today"): 
            st.session_state.week_offset = 0; safe_fragment_rerun()
    with c3:
        if st.button("▶", use_container_width=True, key="next"): 
            st.session_state.week_offset += 1; safe_fragment_rerun()
    with c4:
        if st.button("🔄", use_container_width=True, key="refresh"): safe_fragment_rerun() 
    with c5:
        btn_type = "primary" if st.session_state.show_memo else "secondary"
        if st.button("📝", use_container_width=True, type=btn_type, key="memo_toggle"): 
            st.session_state.show_memo = not st.session_state.show_memo
            threading.Thread(target=update_db_bg, args=(SUPABASE_URL, HEADERS, st.session_state.logged_in_user, "show_memo", st.session_state.show_memo)).start()
            safe_fragment_rerun()
    with c6:
        btn_type = "primary" if st.session_state.show_zero else "secondary"
        if st.button("☀️", use_container_width=True, type=btn_type, key="zero_toggle"): 
            st.session_state.show_zero = not st.session_state.show_zero
            threading.Thread(target=update_db_bg, args=(SUPABASE_URL, HEADERS, st.session_state.logged_in_user, "show_zero", st.session_state.show_zero)).start()
            safe_fragment_rerun()
    with c7:
        btn_type = "primary" if st.session_state.show_extra else "secondary"
        if st.button("🌙", use_container_width=True, type=btn_type, key="extra_toggle"): 
            st.session_state.show_extra = not st.session_state.show_extra
            threading.Thread(target=update_db_bg, args=(SUPABASE_URL, HEADERS, st.session_state.logged_in_user, "show_extra", st.session_state.show_extra)).start()
            safe_fragment_rerun()
    with c8:
        with st.popover("⚙️", use_container_width=True):
            st.markdown("<div style='font-size:14px; font-weight:bold; margin-bottom:8px;'>📱 앱 설치 (전체화면)</div>", unsafe_allow_html=True)
            st.info("💡 **아이폰(Safari):** 하단 [공유(⍐)] ➔ **'홈 화면에 추가'**\n\n💡 **갤럭시(Chrome):** 상단 [점 3개(⋮)] ➔ **'홈 화면에 추가'**")
            st.markdown("---")
            new_theme = st.selectbox("🎨 테마 변경", [th['name'] for th in themes], index=st.session_state.theme_idx)
            if new_theme != themes[st.session_state.theme_idx]['name']:
                new_idx = [th['name'] for th in themes].index(new_theme)
                requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"theme_idx": new_idx})
                st.session_state.theme_idx = new_idx; st.rerun() 
            new_font = st.selectbox("A 폰트 변경", ["맑은 고딕", "바탕", "돋움", "굴림", "Arial"], index=["맑은 고딕", "바탕", "돋움", "굴림", "Arial"].index(st.session_state.font_name))
            if new_font != st.session_state.font_name:
                requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"font_name": new_font})
                st.session_state.font_name = new_font; st.rerun()
            st.markdown("---")
            if st.button("🔓 로그아웃", type="primary", use_container_width=True):
                st.session_state.logged_in_user = None; st.session_state.teacher = "표민호"; st.query_params.clear(); st.rerun()
            if st.session_state.logged_in_user == "표민호":
                st.markdown("<div style='font-size:12px; font-weight:bold; margin-top:10px;'>👨‍🏫 [관리자] 비번 1234 초기화</div>", unsafe_allow_html=True)
                try:
                    r_users = requests.get(f"{SUPABASE_URL}/rest/v1/users?select=teacher_name", headers=HEADERS, timeout=2)
                    registered_list = [row['teacher_name'] for row in r_users.json()] if r_users.status_code == 200 else teacher_list
                except: registered_list = teacher_list
                reset_target = st.selectbox("대상 선택", registered_list, key="reset_pw", label_visibility="collapsed")
                if st.button("초기화 실행", use_container_width=True):
                    requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{reset_target}", headers=HEADERS, json={"password": "1234"})
                    st.success("완료!")

    now_kst = datetime.now(kst_tz) 
    target_date = now_kst + timedelta(weeks=st.session_state.week_offset)
    monday = target_date - timedelta(days=target_date.weekday())
    is_current_week = (st.session_state.week_offset == 0)
    today_idx = now_kst.weekday() 
    now_mins = now_kst.hour * 60 + now_kst.minute 
    
    active_row, preview_row = None, None
    for row_idx, (period, time_range) in enumerate(period_times):
        if period == "학사일정": continue
        start_str, end_str = time_range.split('\n')
        h1, m1 = map(int, start_str.split(':'))
        h2, m2 = map(int, end_str.split(':'))
        start_m, end_m = h1 * 60 + m1, h2 * 60 + m2
        if start_m <= now_mins <= end_m:
            active_row = row_idx
            if period == "점심": preview_row = row_idx + 1 
            break
        elif now_mins < start_m:
            preview_row = row_idx
            break

    html_parts = []
    html_parts.append(f"<div style='width:100%; overflow-x:auto; background-color:{t['grid']}; border-radius:4px;'><table class='mobile-table'>")
    html_parts.append(f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']};'><th style='width: 13%; font-size:14px;'>교시</th>")

    for col, day in enumerate(days):
        date_str = (monday + timedelta(days=col)).strftime("%m/%d")
        th_class = "hl-border-red" if (is_current_week and col == today_idx) else ""
        th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
        th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
        html_parts.append(f"<th class='{th_class}' style='background-color:{th_bg}; color:{th_fg};'><div style='line-height: 1.1;'><span style='font-size:15px;'>{day}</span><br><span style='font-size:12px; font-weight:normal;'>{date_str}</span></div></th>")
    html_parts.append("</tr>")

    base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})
    
    for row_idx, (period, time_str) in enumerate(period_times):
        
        if period != "학사일정":
            if period == "조회" and not st.session_state.show_zero: continue
            if period in ["8교시", "9교시"] and not st.session_state.show_extra: continue

        td_period_class = "hl-border-red" if (is_current_week and (row_idx == active_row or row_idx == preview_row)) else ""
        html_parts.append("<tr>")
        
        if period == "학사일정":
            p_bg = t.get('acad_per_bg', t['per_bg'])
            p_fg = t.get('acad_per_fg', t['per_fg'])
        else:
            p_bg = t['hl_per'] if (is_current_week and active_row == row_idx) else t['per_bg']
            p_fg = 'white' if (is_current_week and active_row == row_idx and t['name'] != '웜 파스텔') else t['per_fg']
        
        time_html = ""
        if period != "학사일정":
            start_t, end_t = time_str.split('\n')
            time_html = f"<div style='line-height:1.0; width:100%; padding:0 2px;'><div style='text-align:left; font-size:11px; font-weight:normal;'>{start_t}~</div><div style='text-align:right; font-size:11px; font-weight:normal;'>{end_t}</div></div>"
        
        html_parts.append(f"<td class='{td_period_class}' style='background-color:{p_bg}; color:{p_fg};'><div style='line-height:1.1; font-size:14px; margin-bottom:2px;'><b>{period}</b></div>{time_html}</td>")
        
        for col, day in enumerate(days):
            row_num = row_idx + 1
            date_str = (monday + timedelta(days=col)).strftime('%Y-%m-%d')
            
            if row_num == 1: date_key = f"{date_str}_schedule"
            else: date_key = f"{date_str}_{row_num - 1}"
            
            subject = ""
            if period == "학사일정":
                subject = academic_data.get(date_str, "").replace(' / ', '\n')
            elif period != "점심" and period != "조회":
                s_idx = row_num - 3 if row_num < 7 else row_num - 4
                if s_idx >= 0 and s_idx < len(base_schedule.get(day, [])): subject = base_schedule[day][s_idx]
            
            is_strike, is_custom = False, False
            custom_color = None
            
            if date_key in custom_data:
                val = custom_data[date_key]
                if val == "__STRIKE__": 
                    is_strike, is_custom = True, True
                else: 
                    is_custom = True
                    m = re.match(r'^<span style=[\'"]color:([^"\']+)[\'"]>(.*)</span>$', val, re.DOTALL | re.IGNORECASE)
                    if m:
                        custom_color = m.group(1)
                        subject = m.group(2)
                    else:
                        subject = val
            
            if period == "학사일정":
                bg = t.get('acad_cell_bg', t['lunch_bg'])
                default_fg = t.get('acad_cell_fg', t['cell_fg'])
                fg = default_fg
                deco = "line-through" if is_strike else "none"
                if is_strike: fg = "#bdc3c7" if t['name'] == '모던 다크' else "#95a5a6"
                elif custom_color: fg = custom_color
            else:
                bg = t['lunch_bg'] if period in ["조회", "점심"] else t['cell_bg']
                fg = t['cell_fg']
                deco = "line-through" if is_strike else "none"
                if is_strike: fg = "#bdc3c7" if t['name'] == '모던 다크' else "#95a5a6"
                elif custom_color: fg = custom_color
                elif is_custom: fg = "#e74c3c"
            
            font_sz_str = "14px"
            line_height = "1.2"
            
            if period == "학사일정":
                font_sz = 12
                if subject:
                    lines = subject.split('\n')
                    num_lines = len(lines)
                    max_len = max([len(l) for l in lines] if lines else [0])
                    if num_lines >= 4 or max_len > 9: font_sz = 9
                    elif num_lines >= 3 or max_len > 6: font_sz = 10
                font_sz_str = f"{font_sz}px"
                line_height = "1.1"

            display = subject.replace('\n', '<br>') if subject else ""
            td_cell_class = ""
            if period != "학사일정":
                if is_current_week and col == today_idx and row_idx == active_row: td_cell_class = "hl-fill-yellow"
                elif is_current_week and col == today_idx and row_idx == preview_row: td_cell_class = "hl-border-yellow"
            
            html_parts.append(f"<td class='{td_cell_class}' style='background-color:{bg}; color:{fg};'><div style='text-decoration:{deco}; font-size:{font_sz_str}; width:100%; display:flex; align-items:center; justify-content:center; height:100%; line-height:{line_height}; word-break:keep-all; overflow-wrap:break-word; white-space:normal; padding:2px;'>{display}</div></td>")
        html_parts.append("</tr>")
    html_parts.append("</table></div>")

    if st.session_state.show_memo:
        html_parts.append(f"<div style='margin-top:10px;'><h3 style='margin:0; font-size:15px; margin-bottom:8px; color:{t['text']};'>📝 {st.session_state.teacher} 메모장 <span style='font-size:11px; font-weight:normal; opacity:0.6;'>(수정은 PC에서)</span></h3><div class='memo-container'>")
        if memos_list:
            for i, m in enumerate(memos_list): m['display_num'] = len(memos_list) - i
            active_memos = [m for m in memos_list if not m.get('is_strike', False)]
            completed_memos = [m for m in memos_list if m.get('is_strike', False)]
            sorted_memos = active_memos + completed_memos

            for m in sorted_memos:
                num = m['display_num']
                text, is_strike, is_imp = m['memo_text'], m.get('is_strike', False), m.get('is_important', False)
                raw_time = m.get('created_at', '')
                time_str = ""
                if raw_time:
                    try:
                        clean_time = raw_time.replace('Z', '+00:00')
                        dt_utc = datetime.fromisoformat(clean_time)
                        dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
                        time_str = dt_kst.strftime('%y.%m.%d %H:%M')
                    except: time_str = raw_time[:10]

                prefix = "⭐ " if is_imp else ""
                deco, color = ("line-through", "gray") if is_strike else ("none", t['text'])
                html_parts.append(f"<div style='color:{color}; text-decoration:{deco}; font-size:14px; font-weight:bold; line-height:1.4; padding: 6px 2px; border-bottom: 1px solid {t['grid']}; display:flex; justify-content:space-between; align-items:flex-start;'><div style='flex:1; word-break:break-word;'><b>{num}.</b> {prefix}{text}</div><div style='font-size:11px; font-weight:normal; opacity:0.6; white-space:nowrap; margin-left:8px; margin-top:2px;'>{time_str}</div></div>")
        else: 
            html_parts.append(f"<div style='font-size:13px; color:{t['text']}; opacity:0.7; padding:10px;'>저장된 메모가 없습니다.</div>")
        html_parts.append("</div></div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)

display_dashboard()