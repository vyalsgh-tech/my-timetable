import streamlit as st
import requests
import csv
import os
import base64
from datetime import datetime, timedelta, timezone

# 1. 페이지 및 모바일 UI 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        .stApp { max-width: 420px; margin: 0 auto; background-color: #2c3e50; }
        .block-container { padding: 1rem 0.5rem !important; }
        header { visibility: hidden; }
        div[data-baseweb="select"] { font-size: 14px !important; padding: 0px !important; height: 35px !important; }
        .stButton>button { height: 35px !important; padding: 0px 3px !important; font-size: 13px !important; line-height: 1 !important; }
        div[data-testid="stDialog"] { border-radius: 15px; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #bdc3c7; border-radius: 3px; }
        .cell-link { display: block; height: 100%; text-decoration: none !important; color: inherit !important; }
        .memo-link { display: block; text-decoration: none !important; color: inherit !important; }
        .action-btn { display: flex; align-items: center; justify-content: center; text-decoration: none !important; }
    </style>
""", unsafe_allow_html=True)

# 2. Supabase 통신 기본 설정
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# 3. 로그인 게이트웨이
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

if st.session_state.logged_in_user is None:
    st.title("🔒 명덕외고 시간표 접속")
    tab1, tab2 = st.tabs(["로그인", "새 계정 생성"])
    
    with tab1:
        st.info("선생님의 성함을 입력해 주세요. (예: 표민호)")
        login_id = st.text_input("아이디 (이름)", key="l_id")
        login_pw = st.text_input("비밀번호", type="password", key="l_pw")
        if st.button("로그인", use_container_width=True):
            r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{login_id}", headers=HEADERS)
            if r.status_code == 200 and len(r.json()) > 0:
                user_data = r.json()[0]
                if user_data['password'] == login_pw:
                    # 로그인 성공 시 개인 설정값 모두 불러오기
                    st.session_state.logged_in_user = login_id
                    st.session_state.teacher = login_id
                    st.session_state.theme_idx = user_data.get('theme_idx', 0)
                    st.session_state.font_name = user_data.get('font_name', '맑은 고딕')
                    st.session_state.show_zero = user_data.get('show_zero', False)
                    st.session_state.show_extra = user_data.get('show_extra', False)
                    st.session_state.show_memo = user_data.get('show_memo', True)
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
            else:
                st.error("등록되지 않은 선생님입니다.")
                
    with tab2:
        new_id = st.text_input("사용할 아이디 (이름)", key="n_id")
        new_pw = st.text_input("사용할 비밀번호", type="password", key="n_pw")
        if st.button("계정 생성", use_container_width=True):
            if not new_id.strip() or not new_pw.strip():
                st.warning("아이디와 비밀번호를 모두 입력하세요.")
            else:
                r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{new_id}", headers=HEADERS)
                if r.status_code == 200 and len(r.json()) > 0:
                    st.error("이미 등록된 이름입니다.")
                else:
                    payload = {"teacher_name": new_id, "password": new_pw}
                    r2 = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json=payload)
                    if r2.status_code in [200, 201]:
                        st.success("✅ 계정이 생성되었습니다! [로그인] 탭으로 이동해주세요.")
                    else:
                        st.error("생성 실패. 서버 연결을 확인하세요.")
    st.stop()

# --- 로그인 성공 후 메인 화면 ---

# 4. CSV 데이터 로딩
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

if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4' }
]
t = themes[st.session_state.theme_idx]
st.markdown(f"<style>.stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; }}</style>", unsafe_allow_html=True)

# 5. DB 데이터 실시간 연동
custom_data = {}
memos_list = []
try:
    r_cust = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}", headers=HEADERS)
    if r_cust.status_code == 200:
        custom_data = {row['date_key']: row['subject'] for row in r_cust.json()}
    
    r_memo = requests.get(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}&order=created_at.desc", headers=HEADERS)
    if r_memo.status_code == 200:
        memos_list = r_memo.json()
except Exception:
    pass

memo_count = len(memos_list)

# 6. 모달창 (본인 계정만 동작함)
@st.dialog("일정 수정")
def edit_modal(date_key, current_val):
    date_part, period_part = date_key.split('_')
    st.caption(f"[{st.session_state.teacher} 선생님] {date_part} | {period_part}교시")
    input_val = current_val if current_val != "__STRIKE__" else ""
    input_val = input_val.replace('<br>', '\n')
    
    new_subj = st.text_area("내용 (줄바꿈 가능):", value=input_val, label_visibility="collapsed", height=80)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("✏️수정", use_container_width=True):
        if new_subj.strip():
            chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
            if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": new_subj.strip()})
            else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": new_subj.strip()})
        st.rerun()
    if c2.button("✔️완결", use_container_width=True):
        chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
        if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": "__STRIKE__"})
        else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": "__STRIKE__"})
        st.rerun()
    if c3.button("🗑️복구", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS)
        st.rerun()

@st.dialog("메모 관리")
def memo_modal(memo_id):
    memo_id = int(memo_id)
    current_memo = next((m for m in memos_list if m['id'] == memo_id), None)
    if not current_memo: return
    is_strike = current_memo.get('is_strike', False)
    
    new_text = st.text_area("메모 수정:", value=current_memo.get('memo_text', ''), label_visibility="collapsed", height=80)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("✏️수정", use_container_width=True):
        if new_text.strip(): requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"memo_text": new_text.strip()})
        st.rerun()
    if c2.button("✔️완결", use_container_width=True):
        requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"is_strike": not is_strike})
        st.rerun()
    if c3.button("🗑️삭제", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS)
        st.rerun()

@st.dialog("새 메모 추가")
def add_memo_modal():
    new_text = st.text_area("메모 내용을 입력하세요:", height=80)
    if st.button("💾 저장", use_container_width=True):
        if new_text.strip(): requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": st.session_state.logged_in_user, "memo_text": new_text.strip()})
        st.rerun()

if "edit_key" in st.query_params:
    e_key = st.query_params["edit_key"]
    e_subj = st.query_params.get("edit_subj", "")
    st.query_params.clear()
    edit_modal(e_key, e_subj)
elif "memo_idx" in st.query_params:
    m_idx = st.query_params["memo_idx"]
    st.query_params.clear()
    memo_modal(m_idx)
elif "action" in st.query_params:
    act = st.query_params["action"]
    st.query_params.clear()
    if act == "add_memo": add_memo_modal()

# 7. 헤더 및 로그아웃
col_h1, col_h2 = st.columns([7, 3])
with col_h1:
    logo_html = "🏫&nbsp;"
    st.markdown(f"<div style='color:{t['head_fg']}; font-size:16px; font-weight:bold; margin-top:5px;'>{logo_html} 2026학년도 1학기 시간표</div>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔒 로그아웃", use_container_width=True):
        st.session_state.logged_in_user = None
        st.rerun()

# 8. 개인화된 상단 메뉴
st.markdown(f"<div style='background-color:{t['top']}; padding:8px; border-radius:10px; margin-bottom:8px;'>", unsafe_allow_html=True)
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns([1.8, 0.8, 0.8, 0.8, 0.8])
with r1_c1:
    teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사", teacher_list, index=idx, label_visibility="collapsed")
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
        # 설정 변경 시 DB에 즉시 업데이트
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
    m_icon = f"📝 내 메모({memo_count}) ON" if st.session_state.show_memo else f"📝 내 메모({memo_count}) OFF"
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

# 9. 시간 및 그리드 로직
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

# 10. HTML 표 렌더링
html = f"""
<style>
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: clamp(10px, 3vw, 13px); }}
    .mobile-table th, .mobile-table td {{ border: 1px solid {t['grid']}; padding: 0; text-align: center; vertical-align: middle; word-break: keep-all; height: clamp(40px, 10vw, 55px); }}
    .hl-border-red {{ border: 2.5px solid {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ border: 2.5px solid {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; border: 2px solid #d4ac0d !important; }}
    .cell-content {{ padding: 2px; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
</style>
<div style="width:100%; overflow-x:auto; background-color:{t['grid']}; padding:2px; border-top-left-radius:8px; border-top-right-radius:8px;">
<table class="mobile-table">
"""

html += f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']}; height: 35px;'>"
html += f"<th style='width: 14%;'>교시</th>"
for col, day in enumerate(days):
    date_str = (monday + timedelta(days=col)).strftime("%m/%d")
    th_class = "class='hl-border-red'" if (is_current_week and col == today_idx) else ""
    th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
    th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
    html += f"<th {th_class} style='background-color:{th_bg}; color:{th_fg};'>{day}<br><span style='font-size:0.95em; font-weight:normal;'>({date_str})</span></th>"
html += "</tr>"

base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})
# 🔥 다른 사람 시간표를 볼 때는 클릭(수정) 불가하도록 철저히 막음
is_my_schedule = (st.session_state.teacher == st.session_state.logged_in_user)

for row_idx, (period, time_str) in enumerate(period_times):
    if period == "조회" and not st.session_state.show_zero: continue
    if period in ["8교시", "9교시"] and not st.session_state.show_extra: continue

    td_period_class = "class='hl-border-red'" if (is_current_week and (row_idx == active_row or row_idx == preview_row)) else ""
    html += "<tr>"
    
    p_bg = t['hl_per'] if (is_current_week and active_row == row_idx) else t['per_bg']
    p_fg = 'white' if (is_current_week and active_row == row_idx and t['name'] != '웜 파스텔') else t['per_fg']
    
    start_t, end_t = time_str.split('\n')
    formatted_time = f"<div style='line-height:0.9; width:100%; padding:0 3px;'><div style='text-align:left;'>{start_t}~</div><div style='text-align:right;'>{end_t}</div></div>"
    html += f"<td {td_period_class} style='background-color:{p_bg}; color:{p_fg};'><b>{period}</b><br><span style='font-size:0.85em; font-weight:normal; display:inline-block; width:100%;'>{formatted_time}</span></td>"
    
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
        elif is_custom:
            fg = "#e74c3c"
            
        display = subject.replace('\n', '<br>') if subject else ""
        
        td_cell_class = ""
        if is_current_week and col == today_idx:
            if row_idx == active_row: td_cell_class = "class='hl-fill-yellow'"
            elif row_idx == preview_row: td_cell_class = "class='hl-border-yellow'"

        link_href = f"/?edit_key={date_key}&edit_subj={subject}"
        html += f"<td {td_cell_class} style='background-color:{bg}; color:{fg}; font-weight:bold;'>"
        
        # 💡 본인 시간표일 때만 터치(링크) 기능 활성화
        if is_my_schedule and period not in ["점심", "조회"]:
            html += f"<a href='{link_href}' target='_self' class='cell-link'><div class='cell-content' style='text-decoration:{deco}; line-height:1.2;'>{display}</div></a>"
        else:
            html += f"<div class='cell-content' style='text-decoration:{deco}; line-height:1.2;'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)

# 11. 개인 전용 메모장 (타인 열람 절대 불가)
if st.session_state.show_memo:
    memo_html = f"<div style='background-color:{t['bg']}; padding:8px; border: 2px solid {t['grid']}; border-top:none; border-bottom-left-radius:8px; border-bottom-right-radius:8px;'><div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 4px;'><div style='font-size:14px; font-weight:bold; color:{t['head_fg']};'>📝 {st.session_state.logged_in_user} 선생님의 프라이빗 메모장</div><div style='display: flex; gap: 8px;'><a href='/?action=add_memo' target='_self' class='action-btn' style='background-color:{t['top']}; color:{t['head_fg']} !important; padding:4px 12px; border-radius:5px; font-size:12px; border:1px solid {t['grid']}; box-shadow: 0 1px 2px rgba(0,0,0,0.2);'>➕ 메모 추가</a></div></div><div style='max-height:160px; overflow-y:auto;'>"
    if memos_list:
        for i, m in enumerate(memos_list):
            num = len(memos_list) - i
            text = m.get('memo_text', '')
            is_strike = m.get('is_strike', False)
            text_color = "#95a5a6" if is_strike else t['head_fg']
            deco = "line-through" if is_strike else "none"
            link_href = f"/?memo_idx={m['id']}"
            memo_html += f"<a href='{link_href}' target='_self' class='memo-link'><div style='color:{text_color}; text-decoration:{deco}; font-size:clamp(12px, 3.8vw, 14px); margin-bottom:6px; line-height: 1.4; padding:6px; background-color:{t['top']}; border-radius:5px;'><b>{num}.</b> {text}</div></a>"
    else:
        memo_html += f"<div style='font-size:12px; color:{t['head_fg']}; text-align:center; padding:10px;'>저장된 메모가 없습니다. 첫 메모를 작성해보세요!</div>"
    
    memo_html += "</div></div>"
    st.markdown(memo_html, unsafe_allow_html=True)