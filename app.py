import streamlit as st
import requests
import csv
import os
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

# 💡 URL 파라미터를 통한 상태 완벽 복구
params = st.query_params
if "user" in params and 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = params["user"]
if "t" in params:
    st.session_state.teacher = params["t"]
if "w" in params:
    st.session_state.week_offset = int(params["w"])

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

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}

def verify_and_load_user(user_id):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{user_id}", headers=HEADERS)
    if r.status_code == 200 and len(r.json()) > 0:
        u_data = r.json()[0]
        st.session_state.theme_idx = u_data.get('theme_idx', 0)
        st.session_state.font_name = u_data.get('font_name', '맑은 고딕')
        return u_data
    return None

if st.session_state.logged_in_user:
    verify_and_load_user(st.session_state.logged_in_user)

# --- ⚙️ 설정 모달창 ---
@st.dialog("⚙️ 설정 및 관리")
def settings_modal():
    teacher_list = list(teachers_data.keys()) if 'teachers_data' in locals() else [st.session_state.logged_in_user]
    new_theme = st.selectbox("🎨 테마 변경", [th['name'] for th in themes], index=st.session_state.theme_idx)
    if new_theme != themes[st.session_state.theme_idx]['name']:
        new_idx = [th['name'] for th in themes].index(new_theme)
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"theme_idx": new_idx})
        st.session_state.theme_idx = new_idx
        st.rerun()
    new_font = st.selectbox("A 폰트 변경", ["맑은 고딕", "바탕", "돋움", "굴림", "Arial"], index=["맑은 고딕", "바탕", "돋움", "굴림", "Arial"].index(st.session_state.font_name))
    if new_font != st.session_state.font_name:
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"font_name": new_font})
        st.session_state.font_name = new_font
        st.rerun()
    st.markdown("---")
    if st.button("🔓 로그아웃", type="primary", use_container_width=True):
        st.session_state.logged_in_user = None
        st.query_params.clear() 
        st.rerun()
    if st.session_state.logged_in_user == "표민호":
        st.markdown("<div style='font-size:12px; font-weight:bold; margin-top:10px;'>👨‍🏫 [관리자] 비번 1234 초기화</div>", unsafe_allow_html=True)
        reset_target = st.selectbox("대상 선택", teacher_list, key="reset_pw", label_visibility="collapsed")
        if st.button("초기화 실행", use_container_width=True):
            requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{reset_target}", headers=HEADERS, json={"password": "1234"})
            st.success("완료!")

# --- 데이터 로드 ---
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
teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]

custom_data = {}
memos_list = []
if st.session_state.logged_in_user:
    try:
        r_cust = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}", headers=HEADERS)
        if r_cust.status_code == 200: custom_data = {row['date_key']: row['subject'] for row in r_cust.json()}
        r_memo = requests.get(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}&order=created_at.desc", headers=HEADERS)
        if r_memo.status_code == 200: memos_list = r_memo.json()
    except: pass

# --- URL 액션 처리 ---
if "nav" in params:
    nav = params["nav"]
    if nav == "prev": st.session_state.week_offset -= 1
    elif nav == "next": st.session_state.week_offset += 1
    elif nav == "today": st.session_state.week_offset = 0
    st.query_params.clear()
    st.query_params["user"] = st.session_state.logged_in_user
    st.query_params["t"] = st.session_state.teacher
    st.query_params["w"] = st.session_state.week_offset
    st.rerun()

if "action" in params and params["action"] == "settings":
    st.query_params.clear()
    st.query_params["user"] = st.session_state.logged_in_user
    st.query_params["t"] = st.session_state.teacher
    st.query_params["w"] = st.session_state.week_offset
    settings_modal()

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
                        st.rerun()
                    else: st.error("비밀번호가 일치하지 않습니다.")
                else: st.error("등록되지 않은 선생님입니다.")
    st.stop()

# --- 날짜 및 시간표 로직 ---
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
is_current_week = (st.session_state.week_offset == 0)
today_idx = now_kst.weekday() 
now_mins = now_kst.hour * 60 + now_kst.minute 

# 💡 글로벌 CSS 설정 (헤더 및 툴바 460px 고정 및 이름창 120px 정렬)
st.markdown(f"""
<style>
    html, body, .stApp {{ touch-action: auto !important; }}
    * {{ animation-duration: 0s !important; transition-duration: 0s !important; }}
    .element-container, .stMarkdown, div[data-testid="stPopoverBody"] {{ animation: none !important; transition: none !important; }}
    .stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; color: {t['text']} !important; }}
    .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{ color: {t['text']} !important; }}
    .block-container {{ padding: 0.5rem 0.2rem !important; max-width: 100% !important; }}
    header {{ visibility: hidden; }}
    
    /* 🚨 1. 상단 헤더: 제목 옆에 이름창을 460px 툴바 끝선에 맞춰 고정 */
    @media screen and (max-width: 9999px) {{
        div[data-testid="stHorizontalBlock"]:first-of-type {{
            display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; align-items: center !important;
            justify-content: space-between !important;
            max-width: 460px !important; width: 100% !important; margin: 0 auto 5px 0 !important;
        }}
        div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(1) {{ flex: 1 1 auto !important; min-width: 0 !important; width: auto !important; }}
        /* 이름창 구역: 🌙 아이콘 시작위치에 맞춘 120px 폭 고정 */
        div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]:nth-child(2) {{ flex: 0 0 120px !important; min-width: 120px !important; width: 120px !important; }}
    }}
    div[data-baseweb="select"] {{ font-size: 13px !important; font-weight: bold; height: 32px !important; width: 100% !important; min-width: 0 !important; }}
    div[data-baseweb="select"] > div {{ min-height: 32px !important; padding: 0 2px 0 6px !important; border: 1px solid {t['grid']} !important; border-radius: 4px; }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. 상단 헤더 (제목 + 고정된 이름창)
# ---------------------------------------------------------
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown(f"<div style='font-size:16px; font-weight:800; margin-top:2px; white-space:nowrap;'>🏫 명덕외고 시간표 뷰어</div>", unsafe_allow_html=True)
with col_h2:
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사", teacher_list, index=idx, label_visibility="collapsed")
    if selected != st.session_state.teacher:
        st.session_state.teacher = selected
        st.rerun()

# ---------------------------------------------------------
# 2. 🔥 순수 HTML 툴바 (폭 460px 고정)
# ---------------------------------------------------------
u = st.session_state.logged_in_user
cur_w = st.session_state.week_offset
cur_t = st.session_state.teacher

link_prev = f"/?user={u}&w={cur_w - 1}&t={cur_t}"
link_next = f"/?user={u}&w={cur_w + 1}&t={cur_t}"
link_today = f"/?user={u}&w=0&t={cur_t}"
link_set = f"/?user={u}&w={cur_w}&t={cur_t}&action=settings"

bg_today = t['hl_per'] if (cur_w == 0) else "transparent"
fg_today = "#ffffff" if (cur_w == 0) else t['text']

chk_memo_attr = "checked='checked'" if st.session_state.show_memo else ""
chk_zero_attr = "checked='checked'" if st.session_state.show_zero else ""
chk_extra_attr = "checked='checked'" if st.session_state.show_extra else ""

html_parts = []
html_parts.append("<style>")
html_parts.append(f".pure-html-toolbar {{ display: flex; flex-direction: row; flex-wrap: nowrap; align-items: center; background-color: {t['top']}; padding: 4px 2px; border-radius: 6px; margin-bottom: 10px; width: 100%; max-width: 460px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); gap: 2px; }}")
html_parts.append(f".tb-btn {{ flex: 1 1 0; text-align: center; text-decoration: none !important; color: {t['text']}; font-size: 13px; font-weight: bold; padding: 8px 0; border-radius: 4px; background-color: transparent; line-height: 1; cursor: pointer; user-select: none; display: block; }}")
html_parts.append(".tb-btn-wide { flex: 1.5 1 0; }")
html_parts.append(".tb-btn:active { opacity: 0.6; }")
html_parts.append(".row-zero, .row-extra, #memo-section { display: none; }")
html_parts.append("#chk-zero:checked ~ .app-container .row-zero { display: table-row !important; }")
html_parts.append("#chk-extra:checked ~ .app-container .row-extra { display: table-row !important; }")
html_parts.append("#chk-memo:checked ~ .app-container #memo-section { display: block !important; }")
html_parts.append(f"#chk-zero:checked ~ .app-container label[for='chk-zero'], #chk-extra:checked ~ .app-container label[for='chk-extra'], #chk-memo:checked ~ .app-container label[for='chk-memo'] {{ background-color: {t['hl_per']} !important; color: #ffffff !important; }}")
html_parts.append(".mobile-table { width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 14px; }")
html_parts.append(f".mobile-table th {{ border: 1px solid {t['grid']}; padding: 4px 1px; text-align: center; height: 45px; }}")
html_parts.append(f".mobile-table td {{ border: 1px solid {t['grid']}; padding: 0px; text-align: center; vertical-align: middle; height: 65px; word-break: keep-all; font-weight: bold; font-size: 14px; }}")
html_parts.append(f".hl-border-red {{ box-shadow: inset 0 0 0 3px {t['hl_per']} !important; z-index: 10; }}")
html_parts.append(f".hl-border-yellow {{ box-shadow: inset 0 0 0 3px {t['hl_cell']} !important; z-index: 10; }}")
html_parts.append(f".hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; box-shadow: inset 0 0 0 3px #d4ac0d !important; }}")
html_parts.append("</style>")

html_parts.append(f"<input type='checkbox' id='chk-memo' style='display:none;' {chk_memo_attr} />")
html_parts.append(f"<input type='checkbox' id='chk-zero' style='display:none;' {chk_zero_attr} />")
html_parts.append(f"<input type='checkbox' id='chk-extra' style='display:none;' {chk_extra_attr} />")

html_parts.append("<div class='app-container'>")
html_parts.append("<div class='pure-html-toolbar'>")
html_parts.append(f"<a class='tb-btn' href='{link_prev}' target='_self'>◀</a>")
html_parts.append(f"<a class='tb-btn tb-btn-wide' style='background-color:{bg_today}; color:{fg_today};' href='{link_today}' target='_self'>이번주</a>")
html_parts.append(f"<a class='tb-btn' href='{link_next}' target='_self'>▶</a>")
html_parts.append("<label class='tb-btn' for='chk-memo'>📝</label>")
html_parts.append("<label class='tb-btn' for='chk-zero'>☀️</label>")
html_parts.append("<label class='tb-btn' for='chk-extra'>🌙</label>")
html_parts.append(f"<a class='tb-btn' href='{link_set}' target='_self'>⚙️</a>")
html_parts.append("</div>")

# 시간표 본문
html_parts.append(f"<div style='width:100%; overflow-x:auto; background-color:{t['grid']}; border-radius:4px;'>")
html_parts.append("<table class='mobile-table'>")
html_parts.append(f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']};'>")
html_parts.append("<th style='width: 13%; font-size:14px;'>교시</th>")

for col, day in enumerate(days):
    date_str = (monday + timedelta(days=col)).strftime("%m/%d")
    th_class = "hl-border-red" if (is_current_week and col == today_idx) else ""
    th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
    th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
    html_parts.append(f"<th class='{th_class}' style='background-color:{th_bg}; color:{th_fg};'><div style='line-height: 1.1;'><span style='font-size:15px;'>{day}</span><br><span style='font-size:12px; font-weight:normal;'>{date_str}</span></div></th>")
html_parts.append("</tr>")

# 시간표 데이터 매칭
active_row, preview_row = None, None
for row_idx, (period, time_range) in enumerate(period_times):
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

base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})
for row_idx, (period, time_str) in enumerate(period_times):
    row_class = "row-zero" if period == "조회" else ("row-extra" if period in ["8교시", "9교시"] else "")
    td_period_class = "hl-border-red" if (is_current_week and (row_idx == active_row or row_idx == preview_row)) else ""
    html_parts.append(f"<tr class='{row_class}'>")
    p_bg = t['hl_per'] if (is_current_week and active_row == row_idx) else t['per_bg']
    p_fg = 'white' if (is_current_week and active_row == row_idx and t['name'] != '웜 파스텔') else t['per_fg']
    start_t, end_t = time_str.split('\n')
    html_parts.append(f"<td class='{td_period_class}' style='background-color:{p_bg}; color:{p_fg};'><div style='line-height:1.1; font-size:14px; margin-bottom:2px;'><b>{period}</b></div><div style='line-height:1.0; width:100%; padding:0 2px;'><div style='text-align:left; font-size:11px; font-weight:normal;'>{start_t}~</div><div style='text-align:right; font-size:11px; font-weight:normal;'>{end_t}</div></div></td>")
    for col, day in enumerate(days):
        row_num = row_idx + 1
        date_key = f"{(monday + timedelta(days=col)).strftime('%Y-%m-%d')}_{row_num}"
        subject = ""
        if period != "점심":
            s_idx = row_num - 2 if row_num < 6 else row_num - 3
            if s_idx >= 0 and s_idx < len(base_schedule.get(day, [])): subject = base_schedule[day][s_idx]
        is_strike, is_custom = False, False
        if date_key in custom_data:
            val = custom_data[date_key]
            if val == "__STRIKE__": is_strike, is_custom = True, True
            else: subject, is_custom = val, True
        bg = t['lunch_bg'] if period in ["조회", "점심"] else t['cell_bg']
        fg = t['cell_fg']
        deco = "line-through" if is_strike else "none"
        if is_strike: fg = "#bdc3c7" if t['name'] == '모던 다크' else "#95a5a6"
        elif is_custom: fg = "#e74c3c"
        display = subject.replace('\n', '<br>') if subject else ""
        td_cell_class = "hl-fill-yellow" if (is_current_week and col == today_idx and row_idx == active_row) else ("hl-border-yellow" if (is_current_week and col == today_idx and row_idx == preview_row) else "")
        html_parts.append(f"<td class='{td_cell_class}' style='background-color:{bg}; color:{fg};'><div style='text-decoration:{deco}; font-size:14px; width:100%; display:flex; align-items:center; justify-content:center; height:100%; line-height:1.2;'>{display}</div></td>")
    html_parts.append("</tr>")
html_parts.append("</table></div>")

# 메모장
html_parts.append(f"<div id='memo-section' style='margin-top:10px;'><h3 style='margin:0; font-size:15px; margin-bottom:8px; color:{t['text']};'>📝 {st.session_state.teacher} 메모장 <span style='font-size:11px; font-weight:normal; opacity:0.6;'>(수정은 PC에서)</span></h3><div style='height:300px; overflow-y:auto; border:1px solid {t['grid']}; border-radius:6px; padding:6px;'>")
if memos_list:
    for i, m in enumerate(memos_list):
        num = len(memos_list) - i
        text, is_strike, is_imp = m['memo_text'], m.get('is_strike', False), m.get('is_important', False)
        prefix = "⭐ " if is_imp else ""
        deco, color = ("line-through", "gray") if is_strike else ("none", t['text'])
        html_parts.append(f"<div style='color:{color}; text-decoration:{deco}; font-size:14px; font-weight:bold; line-height:1.4; padding: 6px 2px; border-bottom: 1px solid {t['grid']};'><b>{num}.</b> {prefix}{text}</div>")
else: html_parts.append(f"<div style='font-size:13px; color:{t['text']}; opacity:0.7; padding:10px;'>저장된 메모가 없습니다.</div>")
html_parts.append("</div></div></div>")

st.markdown("".join(html_parts), unsafe_allow_html=True)