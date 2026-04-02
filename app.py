import streamlit as st
import requests
import csv
import os
import base64
from datetime import datetime, timedelta, timezone

# 1. 페이지 및 모바일 UI 기본 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

# 상태 초기화
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0
if 'show_zero' not in st.session_state: st.session_state.show_zero = False
if 'show_extra' not in st.session_state: st.session_state.show_extra = False
if 'show_memo' not in st.session_state: st.session_state.show_memo = True
if 'teacher' not in st.session_state: st.session_state.teacher = "표민호"
if 'theme_idx' not in st.session_state: st.session_state.theme_idx = 0
if 'font_name' not in st.session_state: st.session_state.font_name = "맑은 고딕"

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'text': '#ffffff' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'text': '#333333' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'text': '#2c3e50' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'text': '#1a3026' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'text': '#222222' }
]
t = themes[st.session_state.theme_idx]

# 💡 모바일 최적화 및 폰트 강제 키우기 CSS
st.markdown(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        .stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; color: {t['text']} !important; }}
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp div[data-testid="stMarkdownContainer"] {{ color: {t['text']} !important; }}
        .block-container {{ padding: 1rem 0.5rem !important; }}
        header {{ visibility: hidden; }}
        
        /* 탭 디자인 */
        .stTabs [data-baseweb="tab-list"] button {{ color: {t['text']} !important; opacity: 0.7; font-size: 16px; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ opacity: 1; border-bottom: 3px solid {t['hl_per']} !important; font-weight: bold; }}
        
        /* 버튼 둥글고 큼직하게 */
        .stButton>button {{ height: 42px !important; border-radius: 8px !important; font-size: 15px !important; font-weight: bold !important; background-color: {t['top']} !important; color: {t['text']} !important; border: 1px solid {t['grid']} !important; }}
        .stButton>button[data-testid="baseButton-primary"] {{ background-color: {t['hl_per']} !important; color: #ffffff !important; border: none !important; }}
        
        /* 알림창 */
        div[data-testid="stAlert"] {{ background-color: {t['top']} !important; color: {t['text']} !important; border: 1px solid {t['grid']} !important; border-radius: 10px !important; }}
    </style>
""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# --- 로그인 게이트웨이 ---
if st.session_state.logged_in_user is None:
    st.markdown(f"<div style='text-align:center; padding: 2rem 0 1rem 0;'><div style='font-size: 3rem;'>🏫</div><h1 style='font-size: 26px; font-weight: 800;'>명덕외고 스마트 시간표</h1></div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 로그인", "📝 새 계정 등록"])
    with tab1:
        login_id = st.text_input("아이디 (선생님 성함)", placeholder="예: 표민호")
        login_pw = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True, type="primary"):
            if login_id and login_pw:
                r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{login_id}", headers=HEADERS)
                if r.status_code == 200 and len(r.json()) > 0:
                    user_data = r.json()[0]
                    if user_data['password'] == login_pw:
                        st.session_state.logged_in_user = login_id
                        st.session_state.teacher = login_id
                        st.session_state.theme_idx = user_data.get('theme_idx', 0)
                        st.session_state.font_name = user_data.get('font_name', '맑은 고딕')
                        st.session_state.show_zero = user_data.get('show_zero', False)
                        st.session_state.show_extra = user_data.get('show_extra', False)
                        st.session_state.show_memo = user_data.get('show_memo', True)
                        st.rerun()
                    else: st.error("비밀번호가 일치하지 않습니다.")
                else: st.error("등록되지 않은 선생님입니다.")
    with tab2:
        new_id = st.text_input("사용할 아이디 (성함)", placeholder="예: 황혜령")
        new_pw = st.text_input("사용할 비밀번호", type="password")
        if st.button("계정 생성하기", use_container_width=True, type="primary"):
            if new_id and new_pw:
                r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{new_id}", headers=HEADERS)
                if r.status_code == 200 and len(r.json()) > 0: st.error("이미 등록된 이름입니다.")
                else:
                    r2 = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json={"teacher_name": new_id, "password": new_pw})
                    if r2.status_code in [200, 201]: st.success("✅ 계정 생성 완료! 로그인 탭에서 접속해주세요.")
                    else: st.error("생성 실패.")
    st.stop()

# --- 로그인 성공 후 메인 화면 ---

@st.cache_data
def load_csv():
    days = ["월", "화", "수", "목", "금"]
    t_data = {}
    if os.path.exists('data.csv'):
        try:
            with open('data.csv', 'r', encoding='utf-8-sig', errors='replace') as f:
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

teachers_data = load_csv()

# DB 데이터 로드
custom_data = {}
memos_list = []
try:
    r_cust = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}", headers=HEADERS)
    if r_cust.status_code == 200: custom_data = {row['date_key']: row['subject'] for row in r_cust.json()}
    
    r_memo = requests.get(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}&order=created_at.desc", headers=HEADERS)
    if r_memo.status_code == 200: memos_list = r_memo.json()
except: pass

# --- 스트림릿 네이티브 모달창 (URL 초기화 버그 100% 방지) ---
days = ["월", "화", "수", "목", "금"]
period_times = [
    ("조회", "07:40\n08:00"), ("1교시", "08:00\n08:50"), ("2교시", "09:00\n09:50"),
    ("3교시", "10:00\n10:50"), ("4교시", "11:00\n11:50"), ("점심", "11:50\n12:40"),
    ("5교시", "12:40\n13:30"), ("6교시", "13:40\n14:30"), ("7교시", "14:40\n15:30"),
    ("8교시", "16:00\n16:50"), ("9교시", "17:00\n17:50")
]

kst_tz = timezone(timedelta(hours=9))
now_kst = datetime.now(kst_tz) 
target_date = now_kst + timedelta(weeks=st.session_state.week_offset)
monday = target_date - timedelta(days=target_date.weekday())

@st.dialog("📅 내 시간표 수정하기")
def edit_timetable_modal():
    st.info("수정할 날짜와 교시를 선택하세요.")
    c1, c2 = st.columns(2)
    
    dates_this_week = [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]
    date_options = {d: f"{days[i]}요일 ({d[5:]})" for i, d in enumerate(dates_this_week)}
    sel_date = c1.selectbox("날짜", dates_this_week, format_func=lambda x: date_options[x])
    
    valid_periods = [(i+1, p[0]) for i, p in enumerate(period_times) if p[0] not in ["조회", "점심"]]
    p_options = {idx: name for idx, name in valid_periods}
    sel_period = c2.selectbox("교시", list(p_options.keys()), format_func=lambda x: p_options[x])
    
    date_key = f"{sel_date}_{sel_period}"
    
    current_val = custom_data.get(date_key)
    if current_val == "__STRIKE__": input_val = ""
    elif current_val: input_val = current_val.replace('<br>', '\n')
    else:
        day_name = days[dates_this_week.index(sel_date)]
        s_idx = sel_period - 2 if sel_period < 6 else sel_period - 3
        base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})
        input_val = base_schedule[day_name][s_idx].replace('<br>', '\n') if s_idx < len(base_schedule.get(day_name, [])) else ""
        
    new_subj = st.text_area("변경할 내용 (비워두면 삭제):", value=input_val, height=80)
    
    cb1, cb2, cb3 = st.columns(3)
    if cb1.button("💾 저장", use_container_width=True):
        chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
        if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": new_subj.strip()})
        else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": new_subj.strip()})
        st.rerun()
    if cb2.button("✔️ 취소선", use_container_width=True):
        chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
        if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": "__STRIKE__"})
        else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": "__STRIKE__"})
        st.rerun()
    if cb3.button("🗑️ 초기화", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS)
        st.rerun()

@st.dialog("📝 새 메모 작성")
def add_memo_modal():
    new_text = st.text_area("메모 내용을 입력하세요:", height=100)
    if st.button("💾 저장", use_container_width=True, type="primary"):
        if new_text.strip(): requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": st.session_state.logged_in_user, "memo_text": new_text.strip()})
        st.rerun()

@st.dialog("📝 메모 관리")
def edit_memo_modal(memo_id, current_text, is_strike):
    new_text = st.text_area("메모 수정:", value=current_text, height=100)
    c1, c2, c3 = st.columns(3)
    if c1.button("✏️ 수정", use_container_width=True):
        if new_text.strip(): requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"memo_text": new_text.strip()})
        st.rerun()
    if c2.button("✔️ 완료선", use_container_width=True):
        requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"is_strike": not is_strike})
        st.rerun()
    if c3.button("🗑️ 삭제", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS)
        st.rerun()


# --- 상단 헤더 및 메뉴 ---
col_h1, col_h2 = st.columns([7, 3])
with col_h1:
    st.markdown(f"<div style='font-size:18px; font-weight:800; margin-top:5px;'>🏫 명덕외고 시간표</div>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔓 로그아웃", use_container_width=True):
        st.session_state.logged_in_user = None
        st.rerun()

st.markdown(f"<div style='background-color:{t['top']}; padding:10px; border-radius:10px; margin-bottom:10px;'>", unsafe_allow_html=True)
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns([1.8, 0.8, 0.8, 0.8, 0.8])
with r1_c1:
    teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사 선택", teacher_list, index=idx, label_visibility="collapsed")
    if selected != st.session_state.teacher:
        st.session_state.teacher = selected
        st.rerun()
with r1_c2:
    if st.button("◀", use_container_width=True): st.session_state.week_offset -= 1
with r1_c3:
    if st.button("🏠", use_container_width=True): st.session_state.week_offset = 0
with r1_c4:
    if st.button("▶", use_container_width=True): st.session_state.week_offset += 1
with r1_c5:
    with st.popover("⚙️"):
        new_theme = st.selectbox("🎨 테마", [th['name'] for th in themes], index=st.session_state.theme_idx)
        if new_theme != themes[st.session_state.theme_idx]['name']:
            new_idx = [th['name'] for th in themes].index(new_theme)
            requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"theme_idx": new_idx})
            st.session_state.theme_idx = new_idx
            st.rerun()
        new_font = st.selectbox("A 폰트", ["맑은 고딕", "바탕", "돋움", "굴림", "Arial"], index=["맑은 고딕", "바탕", "돋움", "굴림", "Arial"].index(st.session_state.font_name))
        if new_font != st.session_state.font_name:
            requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"font_name": new_font})
            st.session_state.font_name = new_font
            st.rerun()

r2_c1, r2_c2, r2_c3 = st.columns(3)
with r2_c1:
    m_icon = f"📝 내 메모({len(memos_list)}) ON" if st.session_state.show_memo else f"📝 내 메모 OFF"
    if st.button(m_icon, use_container_width=True):
        new_val = not st.session_state.show_memo
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_memo": new_val})
        st.session_state.show_memo = new_val
        st.rerun()
with r2_c2:
    z_icon = "☀️ 조회 ON" if st.session_state.show_zero else "☀️ 조회 OFF"
    if st.button(z_icon, use_container_width=True):
        new_val = not st.session_state.show_zero
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_zero": new_val})
        st.session_state.show_zero = new_val
        st.rerun()
with r2_c3:
    e_icon = "🌙 8,9교시 ON" if st.session_state.show_extra else "🌙 8,9교시 OFF"
    if st.button(e_icon, use_container_width=True):
        new_val = not st.session_state.show_extra
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_extra": new_val})
        st.session_state.show_extra = new_val
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)


# --- 시간표 렌더링 (폰트 크기 확장 & 링크 제거) ---
is_current_week = (st.session_state.week_offset == 0)
today_idx = now_kst.weekday() 
now_mins = now_kst.hour * 60 + now_kst.minute 
active_row, preview_row = None, None

def time_to_mins(t_str):
    h, m = map(int, t_str.replace('\n', ':').split(':'))
    return h * 60 + m

for row_idx, (period, time_range) in enumerate(period_times):
    start_str, end_str = time_range.split('\n')
    start_m, end_m = time_to_mins(start_str), time_to_mins(end_str)
    if start_m <= now_mins <= end_m:
        active_row = row_idx
        if period == "점심": preview_row = row_idx + 1 
        break
    elif now_mins < start_m:
        preview_row = row_idx
        break

# 💡 모바일 최적화: 폰트를 14px~16px로 큼직하게 조정, 패딩 확대
html = f"""
<style>
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 15px; }}
    .mobile-table th {{ border: 1px solid {t['grid']}; padding: 6px 2px; text-align: center; font-size: 15px; height: 45px; }}
    .mobile-table td {{ border: 1px solid {t['grid']}; padding: 4px; text-align: center; vertical-align: middle; height: 65px; word-break: keep-all; font-weight: bold; font-size: 15px; }}
    .hl-border-red {{ border: 2.5px solid {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ border: 2.5px solid {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; border: 2px solid #d4ac0d !important; }}
    .cell-content {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; line-height: 1.3; }}
</style>
<div style="width:100%; overflow-x:auto; background-color:{t['grid']}; padding:2px; border-radius:8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
<table class="mobile-table">
"""

html += f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']};'>"
html += f"<th style='width: 14%;'>교시</th>"
for col, day in enumerate(days):
    date_str = (monday + timedelta(days=col)).strftime("%m/%d")
    th_class = "class='hl-border-red'" if (is_current_week and col == today_idx) else ""
    th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
    th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
    html += f"<th {th_class} style='background-color:{th_bg}; color:{th_fg};'>{day}<br><span style='font-size:0.85em; font-weight:normal;'>({date_str})</span></th>"
html += "</tr>"

base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})
is_my_schedule = (st.session_state.teacher == st.session_state.logged_in_user)

for row_idx, (period, time_str) in enumerate(period_times):
    if period == "조회" and not st.session_state.show_zero: continue
    if period in ["8교시", "9교시"] and not st.session_state.show_extra: continue

    td_period_class = "class='hl-border-red'" if (is_current_week and (row_idx == active_row or row_idx == preview_row)) else ""
    html += "<tr>"
    
    p_bg = t['hl_per'] if (is_current_week and active_row == row_idx) else t['per_bg']
    p_fg = 'white' if (is_current_week and active_row == row_idx and t['name'] != '웜 파스텔') else t['per_fg']
    
    start_t, end_t = time_str.split('\n')
    formatted_time = f"<div style='line-height:1; width:100%; padding:0 3px;'><div style='text-align:left;'>{start_t}~</div><div style='text-align:right;'>{end_t}</div></div>"
    html += f"<td {td_period_class} style='background-color:{p_bg}; color:{p_fg}; font-size:14px;'><b>{period}</b><br><span style='font-size:0.8em; font-weight:normal; display:inline-block; width:100%;'>{formatted_time}</span></td>"
    
    for col, day in enumerate(days):
        row_num = row_idx + 1
        date_key = f"{(monday + timedelta(days=col)).strftime('%Y-%m-%d')}_{row_num}"
        
        subject = ""
        if period not in ["점심", "조회"]:
            s_idx = row_num - 2 if row_num < 6 else row_num - 3
            if s_idx < len(base_schedule.get(day, [])): subject = base_schedule[day][s_idx]

        is_strike, is_custom = False, False

        if date_key in custom_data:
            val = custom_data[date_key]
            if val == "__STRIKE__": is_strike, is_custom = True, True
            else: subject, is_custom = val, True

        bg = t['lunch_bg'] if period == "점심" else t['cell_bg']
        fg = t['cell_fg']
        deco = "none"

        if is_strike:
            fg = "#bdc3c7" if t['name'] == '모던 다크' else "#95a5a6"
            deco = "line-through"
            subject = subject if subject else "-"
        elif is_custom: fg = "#e74c3c"
            
        display = subject.replace('\n', '<br>') if subject else ""
        
        td_cell_class = ""
        if is_current_week and col == today_idx:
            if row_idx == active_row: td_cell_class = "class='hl-fill-yellow'"
            elif row_idx == preview_row: td_cell_class = "class='hl-border-yellow'"

        # 💡 HTML의 <a> 링크 삭제 -> 표 터치 시 로그아웃되는 버그 완벽 차단!
        html += f"<td {td_cell_class} style='background-color:{bg}; color:{fg};'>"
        html += f"<div class='cell-content' style='text-decoration:{deco};'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)

# --- 💡 시간표 수정 버튼 (네이티브 방식) ---
st.markdown("<br>", unsafe_allow_html=True)
if is_my_schedule:
    if st.button("✏️ 이번 주 시간표 직접 수정하기", use_container_width=True, type="primary"):
        edit_timetable_modal()

# --- 💡 프라이빗 메모장 (네이티브 방식) ---
if st.session_state.show_memo:
    st.markdown("---")
    col_m1, col_m2 = st.columns([6, 4])
    col_m1.markdown(f"<h3 style='margin:0; font-size:18px;'>📝 {st.session_state.logged_in_user} 메모장</h3>", unsafe_allow_html=True)
    if col_m2.button("➕ 새 메모", type="primary", use_container_width=True):
        add_memo_modal()
        
    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    
    if memos_list:
        for m in memos_list:
            with st.container(border=True): # 테두리가 있는 깔끔한 카드 디자인
                mc1, mc2 = st.columns([8, 2])
                text = m['memo_text']
                if m.get('is_strike'): mc1.markdown(f"<span style='text-decoration: line-through; color: gray; font-size: 16px;'>{text}</span>", unsafe_allow_html=True)
                else: mc1.markdown(f"<span style='font-size: 16px; font-weight: bold;'>{text}</span>", unsafe_allow_html=True)
                
                if mc2.button("관리", key=f"btn_memo_{m['id']}", use_container_width=True):
                    edit_memo_modal(m['id'], text, m.get('is_strike'))
    else:
        st.info("저장된 메모가 없습니다. 첫 메모를 작성해 보세요!")