import streamlit as st
import requests
import csv
import os
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

# 💡 영구 자동 로그인을 위한 URL 파라미터 감지 및 복구
if "user" in st.query_params and 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = st.query_params["user"]
    st.session_state.teacher = st.query_params["user"]
elif 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# 상태 초기화
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0
if 'show_zero' not in st.session_state: st.session_state.show_zero = False
if 'show_extra' not in st.session_state: st.session_state.show_extra = False
if 'show_memo' not in st.session_state: st.session_state.show_memo = True
if 'teacher' not in st.session_state: st.session_state.teacher = "표민호"
if 'theme_idx' not in st.session_state: st.session_state.theme_idx = 0
if 'font_name' not in st.session_state: st.session_state.font_name = "맑은 고딕"
if 'memo_expanded' not in st.session_state: st.session_state.memo_expanded = False

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'text': '#ffffff' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'text': '#333333' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'text': '#2c3e50' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'text': '#1a3026' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'text': '#222222' }
]
t = themes[st.session_state.theme_idx]

# 💡 모바일 화면 밖으로 버튼이 밀려나는 현상 100% 방어 CSS
st.markdown(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        * {{ animation-duration: 0s !important; transition-duration: 0s !important; }}
        .element-container, .stMarkdown, .stButton, div[data-testid="stPopoverBody"] {{ animation: none !important; transition: none !important; }}
        
        .stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; color: {t['text']} !important; }}
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{ color: {t['text']} !important; }}
        .block-container {{ padding: 1rem 0.3rem !important; }}
        header {{ visibility: hidden; }}
        
        .stTabs [data-baseweb="tab-list"] button {{ color: {t['text']} !important; opacity: 0.7; font-size: 16px; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ opacity: 1; border-bottom: 3px solid {t['hl_per']} !important; font-weight: bold; }}
        
        /* 🚨 [핵심] 가로 블록(Horizontal Block)이 무조건 1줄에 꽉 차도록 강제 압축 */
        div[data-testid="stHorizontalBlock"] {{
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
            overflow: hidden !important;
        }}
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            width: 0 !important;         /* 스트림릿의 모바일 100% 강제 확대를 무력화 */
            min-width: 0 !important;     /* 글자가 길어도 뚫고 나가지 못하게 제한 */
            flex: 1 1 0% !important;     /* 모든 버튼이 동일한 비율로 1줄을 나눠가짐 */
            padding: 0 !important;
        }}
        /* 첫 번째 컬럼(교사 선택, 메모, 조회 버튼 등)은 글씨가 길어서 비율을 1.6배로 더 줌 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {{
            flex: 1.6 1 0% !important; 
        }}
        
        .stButton>button {{ height: 38px !important; border-radius: 6px !important; font-size: 13.5px !important; font-weight: bold !important; background-color: {t['top']} !important; color: {t['text']} !important; border: 1px solid {t['grid']} !important; padding: 0 2px !important; }}
        .stButton>button[data-testid="baseButton-primary"] {{ background-color: {t['hl_per']} !important; color: #ffffff !important; border: 2px solid #ffffff !important; box-shadow: 0 0 5px rgba(0,0,0,0.3) !important; }}
        
        div[data-testid="stPopover"] > button {{ font-size: 16px !important; padding: 0 !important; }}
        div[data-testid="stPopover"] svg {{ fill: {t['text']} !important; }}
        
        div[data-testid="stAlert"] {{ border-radius: 8px !important; }}
        div[data-testid="stAlert"] p {{ color: #111111 !important; font-weight: bold !important; }}
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

# --- DB 로그인 인증 함수 ---
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
    st.markdown(f"<div style='text-align:center; padding: 2rem 0 1rem 0;'><div style='font-size: 3rem;'>🏫</div><h1 style='font-size: 26px; font-weight: 800;'>명덕외고 스마트 시간표</h1></div>", unsafe_allow_html=True)
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
    with tab2:
        new_id = st.text_input("사용할 아이디 (성함)", placeholder="예: 표민호")
        new_pw = st.text_input("사용할 비밀번호", type="password")
        if st.button("계정 생성하기", use_container_width=True, type="primary"):
            if new_id and new_pw:
                r = requests.get(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{new_id}", headers=HEADERS)
                if r.status_code == 200 and len(r.json()) > 0: st.error("이미 등록된 이름입니다.")
                else:
                    r2 = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json={"teacher_name": new_id, "password": new_pw})
                    if r2.status_code in [200, 201]: st.success("계정 생성 완료! 로그인 탭에서 접속해주세요.")
                    else: st.error("생성 실패.")
    st.stop()

# --- 메인 데이터 로드 ---
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

custom_data = {}
memos_list = []
try:
    r_cust = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}", headers=HEADERS)
    if r_cust.status_code == 200: custom_data = {row['date_key']: row['subject'] for row in r_cust.json()}
    r_memo = requests.get(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}&order=created_at.desc", headers=HEADERS)
    if r_memo.status_code == 200: memos_list = r_memo.json()
except: pass

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

# --- 모달창 (팝업) ---
@st.dialog("📅 시간표 내용 수정")
def edit_timetable_modal(date_key, current_val):
    d_part, p_part = date_key.split('_')
    st.markdown(f"<div style='background-color:{t['top']}; padding:10px; border-radius:5px; margin-bottom:10px; text-align:center;'>선택: <b>{d_part} | {p_part}교시</b></div>", unsafe_allow_html=True)
    new_subj = st.text_area("변경할 내용:", value=current_val.replace('<br>', '\n') if current_val else "", height=80, label_visibility="collapsed")
    
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 저장", use_container_width=True, type="primary"):
        chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
        if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": new_subj.strip()})
        else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": new_subj.strip()})
        st.rerun()
    if c2.button("✔️ 취소선", use_container_width=True):
        chk = requests.get(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS).json()
        if chk: requests.patch(f"{SUPABASE_URL}/rest/v1/custom_schedule?id=eq.{chk[0]['id']}", headers=HEADERS, json={"subject": "__STRIKE__"})
        else: requests.post(f"{SUPABASE_URL}/rest/v1/custom_schedule", headers=HEADERS, json={"teacher_name": st.session_state.teacher, "date_key": date_key, "subject": "__STRIKE__"})
        st.rerun()
    if c3.button("🗑️ 삭제", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/custom_schedule?teacher_name=eq.{st.session_state.teacher}&date_key=eq.{date_key}", headers=HEADERS)
        st.rerun()

@st.dialog("📝 메모 관리")
def manage_memo_modal(memo_id):
    m = next((x for x in memos_list if x['id'] == int(memo_id)), None)
    if not m: return
    is_strike = m.get('is_strike', False)
    is_imp = m.get('is_important', False)
    
    new_text = st.text_area("메모 수정", value=m['memo_text'], height=100, label_visibility="collapsed")
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("💾 저장", type="primary", use_container_width=True):
        requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"memo_text": new_text.strip()})
        st.rerun()
    if c2.button("⭐ 중요", use_container_width=True):
        requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"is_important": not is_imp})
        st.rerun()
    if c3.button("✔️ 완료", use_container_width=True):
        requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS, json={"is_strike": not is_strike})
        st.rerun()
    if c4.button("🗑️ 삭제", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{memo_id}", headers=HEADERS)
        st.rerun()

# URL 파라미터 감지 및 모달 실행
if "edit_date" in st.query_params:
    d_key = st.query_params["edit_date"]
    c_val = st.query_params.get("edit_subj", "")
    st.query_params.pop("edit_date", None)
    st.query_params.pop("edit_subj", None)
    edit_timetable_modal(d_key, c_val)

if "action_memo" in st.query_params:
    m_id = st.query_params["action_memo"]
    st.query_params.pop("action_memo", None)
    manage_memo_modal(m_id)

# --- 상단 헤더 및 메뉴 ---
col_h1, col_h2 = st.columns([7, 3])
with col_h1:
    st.markdown(f"<div style='font-size:18px; font-weight:800; margin-top:5px;'>🏫 명덕외고 시간표</div>", unsafe_allow_html=True)
with col_h2:
    if st.button("🔓 로그아웃", use_container_width=True):
        st.session_state.logged_in_user = None
        st.query_params.clear() 
        st.rerun()

st.markdown(f"<div style='background-color:{t['top']}; padding:8px; border-radius:10px; margin-bottom:10px;'>", unsafe_allow_html=True)

# 💡 첫 번째 줄: 교사선택, 이전, 이번주, 다음 (비율 고정으로 1줄 완벽 렌더링)
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
with r1_c1:
    teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사", teacher_list, index=idx, label_visibility="collapsed")
    if selected != st.session_state.teacher:
        st.session_state.teacher = selected
        st.rerun()
with r1_c2:
    if st.button("◀", use_container_width=True): 
        st.session_state.week_offset -= 1
        st.rerun()
with r1_c3:
    btn_type = "primary" if st.session_state.week_offset == 0 else "secondary"
    if st.button("이번 주", use_container_width=True, type=btn_type): 
        st.session_state.week_offset = 0
        st.rerun()
with r1_c4:
    if st.button("▶", use_container_width=True): 
        st.session_state.week_offset += 1
        st.rerun()

st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

# 💡 두 번째 줄: 메모, 조회, 8/9교시, 설정
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
with r2_c1:
    btn_type_memo = "primary" if st.session_state.show_memo else "secondary"
    if st.button("📝 메모", use_container_width=True, type=btn_type_memo):
        new_val = not st.session_state.show_memo
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_memo": new_val})
        st.session_state.show_memo = new_val
        st.rerun()
with r2_c2:
    btn_type_zero = "primary" if st.session_state.show_zero else "secondary"
    if st.button("☀️ 조회", use_container_width=True, type=btn_type_zero):
        new_val = not st.session_state.show_zero
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_zero": new_val})
        st.session_state.show_zero = new_val
        st.rerun()
with r2_c3:
    btn_type_extra = "primary" if st.session_state.show_extra else "secondary"
    if st.button("🌙 8,9", use_container_width=True, type=btn_type_extra):
        new_val = not st.session_state.show_extra
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_extra": new_val})
        st.session_state.show_extra = new_val
        st.rerun()
with r2_c4:
    with st.popover("⚙️", use_container_width=True):
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
            
        # 💡 [요청사항 반영] 표민호 선생님 계정 전용 '비밀번호 관리자' 메뉴
        if st.session_state.logged_in_user == "표민호":
            st.markdown("---")
            st.markdown("<div style='font-size:14px; font-weight:bold; margin-bottom:5px;'>👨‍🏫 관리자 전용: 비밀번호 초기화</div>", unsafe_allow_html=True)
            reset_target = st.selectbox("초기화할 선생님 선택", teacher_list, key="reset_pw")
            if st.button(f"'{reset_target}' 비번 1234로 초기화", type="primary", use_container_width=True):
                requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{reset_target}", headers=HEADERS, json={"password": "1234"})
                st.success("초기화 완료! (비밀번호: 1234)")

st.markdown("</div>", unsafe_allow_html=True)

# --- 시간표 렌더링 ---
is_current_week = (st.session_state.week_offset == 0)
today_idx = now_kst.weekday() 
now_mins = now_kst.hour * 60 + now_kst.minute 
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

html = f"""
<style>
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 15px; }}
    .mobile-table th {{ border: 1px solid {t['grid']}; padding: 6px 2px; text-align: center; height: 50px; }}
    .mobile-table td {{ border: 1px solid {t['grid']}; padding: 0px; text-align: center; vertical-align: middle; height: 75px; word-break: keep-all; font-weight: bold; font-size: 15px; }}
    
    .hl-border-red {{ box-shadow: inset 0 0 0 3px {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ box-shadow: inset 0 0 0 3px {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; box-shadow: inset 0 0 0 3px #d4ac0d !important; }}
    
    .cell-link {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; text-decoration: none !important; color: inherit !important; cursor: pointer; }}
</style>
<div style="width:100%; overflow-x:auto; background-color:{t['grid']}; padding:2px; border-radius:8px;">
<table class="mobile-table">
"""

html += f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']};'>"
html += f"<th style='width: 14%;'>교시</th>"
for col, day in enumerate(days):
    date_str = (monday + timedelta(days=col)).strftime("%m/%d")
    th_class = "class='hl-border-red'" if (is_current_week and col == today_idx) else ""
    th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
    th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
    html += f"<th {th_class} style='background-color:{th_bg}; color:{th_fg};'><div style='line-height: 1.05;'><span style='font-size:16px;'>{day}</span><br><span style='font-size:15px; font-weight:normal;'>({date_str})</span></div></th>"
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
    html += f"<td {td_period_class} style='background-color:{p_bg}; color:{p_fg};'>"
    html += f"<div style='line-height:1.1; font-size:15px; margin-bottom:3px;'><b>{period}</b></div>"
    html += f"<div style='line-height:1.0; width:100%; padding:0 2px;'><div style='text-align:left; font-size:14px; font-weight:normal;'>{start_t}~</div><div style='text-align:right; font-size:14px; font-weight:normal;'>{end_t}</div></div>"
    html += "</td>"
    
    for col, day in enumerate(days):
        row_num = row_idx + 1
        date_key = f"{(monday + timedelta(days=col)).strftime('%Y-%m-%d')}_{row_num}"
        
        subject = ""
        if period != "점심":
            s_idx = row_num - 2 if row_num < 6 else row_num - 3
            if s_idx >= 0 and s_idx < len(base_schedule.get(day, [])): 
                subject = base_schedule[day][s_idx]

        is_strike, is_custom = False, False

        if date_key in custom_data:
            val = custom_data[date_key]
            if val == "__STRIKE__": is_strike, is_custom = True, True
            else: subject, is_custom = val, True

        # 💡 [요청사항 반영] '조회' 블록도 '점심'과 똑같은 살짝 어두운 톤 적용
        bg = t['lunch_bg'] if period in ["조회", "점심"] else t['cell_bg']
        fg = t['cell_fg']
        deco = "line-through" if is_strike else "none"

        if is_strike:
            fg = "#bdc3c7" if t['name'] == '모던 다크' else "#95a5a6"
            subject = subject if subject else "-"
        elif is_custom: fg = "#e74c3c"
            
        display = subject.replace('\n', '<br>') if subject else ""
        
        td_cell_class = ""
        if is_current_week and col == today_idx:
            if row_idx == active_row: td_cell_class = "class='hl-fill-yellow'"
            elif row_idx == preview_row: td_cell_class = "class='hl-border-yellow'"

        html += f"<td {td_cell_class} style='background-color:{bg}; color:{fg};'>"
        if is_my_schedule and period != "점심":
            link_href = f"/?user={st.session_state.logged_in_user}&edit_date={date_key}&edit_subj={subject}"
            html += f"<a href='{link_href}' target='_self' class='cell-link'><div style='text-decoration:{deco}; width:100%;'>{display}</div></a>"
        else:
            html += f"<div style='text-decoration:{deco}; width:100%; display:flex; align-items:center; justify-content:center; height:100%;'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)


# --- 💡 프라이빗 메모장 ---
if st.session_state.show_memo:
    st.markdown("---")
    c_m1, c_m2 = st.columns([7, 3])
    c_m1.markdown(f"<h3 style='margin:0; font-size:17px; margin-bottom:10px;'>📝 {st.session_state.logged_in_user} 메모장</h3>", unsafe_allow_html=True)
    
    if c_m2.button("➕ 새 메모", use_container_width=True, type="primary"):
        new_text = "새로운 메모"
        requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": st.session_state.logged_in_user, "memo_text": new_text})
        st.rerun()

    memo_height = 500 if st.session_state.memo_expanded else 250
    with st.container(height=memo_height, border=True):
        if memos_list:
            for i, m in enumerate(memos_list):
                num = len(memos_list) - i
                text = m['memo_text']
                is_strike = m.get('is_strike', False)
                is_imp = m.get('is_important', False)
                
                prefix = "⭐ " if is_imp else ""
                deco = "line-through" if is_strike else "none"
                color = "gray" if is_strike else t['text']
                
                link_href = f"/?user={st.session_state.logged_in_user}&action_memo={m['id']}"
                
                memo_line = f"""
                <a href="{link_href}" target="_self" style="text-decoration:none;">
                    <div style="color:{color}; text-decoration:{deco}; font-size:15px; font-weight:bold; line-height:1.3; padding: 8px 4px; border-bottom: 1px solid {t['grid']};">
                        <b>{num}.</b> {prefix}{text}
                    </div>
                </a>
                """
                st.markdown(memo_line, unsafe_allow_html=True)
        else:
            st.info("저장된 메모가 없습니다.")