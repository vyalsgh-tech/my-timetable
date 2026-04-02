import streamlit as st
import requests
import csv
import os
from datetime import datetime, timedelta, timezone

# 1. 페이지 설정
st.set_page_config(page_title="명덕외고 모바일 시간표", page_icon="🏫", layout="centered")

# 💡 영구 자동 로그인을 위한 URL 파라미터 감지
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

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'text': '#ffffff' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'text': '#333333' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'text': '#2c3e50' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'text': '#1a3026' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'text': '#222222' }
]
t = themes[st.session_state.theme_idx]

# 🚨 [완벽 종결] 스트림릿 640px 붕괴 로직을 원천 무력화하는 무적 CSS
st.markdown(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=10.0, user-scalable=yes">
    <style>
        html, body, .stApp {{ touch-action: auto !important; }}
        * {{ animation-duration: 0s !important; transition-duration: 0s !important; }}
        .element-container, .stMarkdown, .stButton, div[data-testid="stPopoverBody"] {{ animation: none !important; transition: none !important; }}
        
        .stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; color: {t['text']} !important; }}
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {{ color: {t['text']} !important; }}
        .block-container {{ padding: 0.5rem 0.2rem !important; max-width: 100% !important; }}
        header {{ visibility: hidden; }}
        
        /* 🔥 스트림릿의 미디어 쿼리를 전면 무시하는 글로벌 선언 */
        @media screen and (max-width: 9999px) {{
            /* 가로 배치 구역 무조건 1줄 강제 */
            div[data-testid="stHorizontalBlock"] {{
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important; /* 꺾임 절대 방지 */
                align-items: center !important;
                gap: 4px !important;
            }}
            div[data-testid="column"] {{
                min-width: 0 !important;
                width: auto !important; /* 모바일 강제 100% 폭 확장을 분쇄 */
                padding: 0 !important;
                margin: 0 !important;
            }}

            /* 💡 [1단계] 헤더 (컬럼 2개짜리 구역) */
            div[data-testid="column"]:first-child:nth-last-child(2) {{ flex: 1 1 auto !important; }}
            div[data-testid="column"]:first-child:nth-last-child(2) ~ div[data-testid="column"] {{ flex: 0 0 100px !important; width: 100px !important; max-width: 100px !important; }}

            /* 💡 [2단계] 조종석 (컬럼 7개짜리 구역) : 호환성을 위해 형제 개수 기반으로 픽셀 정밀 타격 */
            /* 1. ◀ 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
            /* 2. 이번주 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(2) {{ flex: 0 0 50px !important; width: 50px !important; max-width: 50px !important; }}
            /* 3. ▶ 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(3) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
            /* 4. 📝 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(4) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
            /* 5. ☀️ 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(5) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
            /* 6. 🌙 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(6) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
            /* 7. ⚙️ 설정 버튼 */
            div[data-testid="column"]:first-child:nth-last-child(7) ~ div[data-testid="column"]:nth-child(7) {{ flex: 0 0 32px !important; width: 32px !important; max-width: 32px !important; }}
        }}
        
        /* 초소형 드롭다운 박스 (이름선택바) */
        div[data-baseweb="select"] {{ font-size: 13px !important; font-weight: bold; height: 32px !important; width: 100% !important; min-width: 0 !important; }}
        div[data-baseweb="select"] > div {{ min-height: 32px !important; padding: 0 2px 0 6px !important; border: 1px solid {t['grid']} !important; border-radius: 4px; }}
        
        /* 버튼 공통 초소형 디자인 */
        .stButton>button {{ 
            height: 32px !important; 
            border-radius: 4px !important; 
            font-size: 13px !important; 
            font-weight: bold !important; 
            background-color: transparent !important; 
            color: {t['text']} !important; 
            border: 1px solid {t['grid']} !important; 
            padding: 0 !important; 
            line-height: 1 !important;
            width: 100% !important;
            min-width: 0 !important;
        }}
        
        /* ON 상태 하이라이트 */
        .stButton>button[data-testid="baseButton-primary"] {{ 
            background-color: {t['hl_per']} !important; 
            color: #ffffff !important; 
            border: 1px solid {t['hl_per']} !important; 
        }}
        
        /* 설정 팝오버 아이콘 (화살표 숨김) */
        div[data-testid="stPopover"] > button {{ font-size: 15px !important; padding: 0 !important; height: 32px !important; width: 100% !important; border: 1px solid {t['grid']} !important; background-color: transparent !important; color: {t['text']} !important; min-width: 0 !important; }}
        div[data-testid="stPopover"] svg {{ display: none !important; }}
        
        /* 알림창 폰트 색상 */
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

# --- 로그인 화면 (뷰어 전용) ---
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

# --- 메인 데이터 로드 (읽기 전용) ---
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


# ---------------------------------------------------------
# 🚨 CSS 작동을 위해 컬럼 선언 구조를 엄격하게 지킵니다.
# ---------------------------------------------------------

# 💡 [DOM 구역 1번] 상단 헤더: "제목(좌측) + 이름선택창(우측 아담하게 고정)"
col_h1, col_h2 = st.columns(2)
with col_h1:
    st.markdown(f"<div style='font-size:16px; font-weight:800; margin-top:2px;'>🏫 명덕외고 시간표 뷰어</div>", unsafe_allow_html=True)
with col_h2:
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사", teacher_list, index=idx, label_visibility="collapsed")
    if selected != st.session_state.teacher:
        st.session_state.teacher = selected
        st.rerun()

# 💡 [DOM 구역 2번] 7개 아이콘 조종석: 스트림릿의 모든 붕괴 로직을 무시하고 무조건 1줄로 고정
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

with c1:
    if st.button("◀", use_container_width=True): 
        st.session_state.week_offset -= 1
        st.rerun()
with c2:
    btn_type = "primary" if st.session_state.week_offset == 0 else "secondary"
    if st.button("이번주", use_container_width=True, type=btn_type): 
        st.session_state.week_offset = 0
        st.rerun()
with c3:
    if st.button("▶", use_container_width=True): 
        st.session_state.week_offset += 1
        st.rerun()
with c4:
    btn_type_memo = "primary" if st.session_state.show_memo else "secondary"
    if st.button("📝", use_container_width=True, type=btn_type_memo):
        new_val = not st.session_state.show_memo
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_memo": new_val})
        st.session_state.show_memo = new_val
        st.rerun()
with c5:
    btn_type_zero = "primary" if st.session_state.show_zero else "secondary"
    if st.button("☀️", use_container_width=True, type=btn_type_zero):
        new_val = not st.session_state.show_zero
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_zero": new_val})
        st.session_state.show_zero = new_val
        st.rerun()
with c6:
    btn_type_extra = "primary" if st.session_state.show_extra else "secondary"
    if st.button("🌙", use_container_width=True, type=btn_type_extra):
        new_val = not st.session_state.show_extra
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS, json={"show_extra": new_val})
        st.session_state.show_extra = new_val
        st.rerun()
with c7:
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
            
        st.markdown("---")
        # 💡 로그아웃 은닉화
        if st.button("🔓 로그아웃", type="primary", use_container_width=True):
            st.session_state.logged_in_user = None
            st.query_params.clear() 
            st.rerun()
            
        if st.session_state.logged_in_user == "표민호":
            st.markdown("<div style='font-size:12px; font-weight:bold; margin-top:10px;'>👨‍🏫 비번 초기화 (1234)</div>", unsafe_allow_html=True)
            reset_target = st.selectbox("대상", teacher_list, key="reset_pw", label_visibility="collapsed")
            if st.button("실행", use_container_width=True):
                requests.patch(f"{SUPABASE_URL}/rest/v1/users?teacher_name=eq.{reset_target}", headers=HEADERS, json={"password": "1234"})
                st.success("완료!")

# ---------------------------------------------------------

# --- 시간표 렌더링 (뷰어 전용) ---
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
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 14px; }}
    .mobile-table th {{ border: 1px solid {t['grid']}; padding: 4px 1px; text-align: center; height: 45px; }}
    .mobile-table td {{ border: 1px solid {t['grid']}; padding: 0px; text-align: center; vertical-align: middle; height: 65px; word-break: keep-all; font-weight: bold; font-size: 14px; }}
    
    .hl-border-red {{ box-shadow: inset 0 0 0 3px {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ box-shadow: inset 0 0 0 3px {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; box-shadow: inset 0 0 0 3px #d4ac0d !important; }}
</style>
<div style="width:100%; overflow-x:auto; background-color:{t['grid']}; border-radius:4px;">
<table class="mobile-table">
"""

html += f"<tr style='background-color:{t['head_bg']}; color:{t['head_fg']};'>"
html += f"<th style='width: 13%; font-size:14px;'>교시</th>"
for col, day in enumerate(days):
    date_str = (monday + timedelta(days=col)).strftime("%m/%d")
    th_class = "class='hl-border-red'" if (is_current_week and col == today_idx) else ""
    th_bg = t['hl_per'] if (is_current_week and col == today_idx) else t['head_bg']
    th_fg = 'white' if (is_current_week and col == today_idx and t['name'] != '웜 파스텔') else t['head_fg']
    html += f"<th {th_class} style='background-color:{th_bg}; color:{th_fg};'><div style='line-height: 1.1;'><span style='font-size:15px;'>{day}</span><br><span style='font-size:12px; font-weight:normal;'>{date_str}</span></div></th>"
html += "</tr>"

base_schedule = teachers_data.get(st.session_state.teacher, {d: [""]*9 for d in days})

for row_idx, (period, time_str) in enumerate(period_times):
    if period == "조회" and not st.session_state.show_zero: continue
    if period in ["8교시", "9교시"] and not st.session_state.show_extra: continue

    td_period_class = "class='hl-border-red'" if (is_current_week and (row_idx == active_row or row_idx == preview_row)) else ""
    html += "<tr>"
    
    p_bg = t['hl_per'] if (is_current_week and active_row == row_idx) else t['per_bg']
    p_fg = 'white' if (is_current_week and active_row == row_idx and t['name'] != '웜 파스텔') else t['per_fg']
    
    start_t, end_t = time_str.split('\n')
    html += f"<td {td_period_class} style='background-color:{p_bg}; color:{p_fg};'>"
    html += f"<div style='line-height:1.1; font-size:14px; margin-bottom:2px;'><b>{period}</b></div>"
    html += f"<div style='line-height:1.0; width:100%; padding:0 2px;'><div style='text-align:left; font-size:11px; font-weight:normal;'>{start_t}~</div><div style='text-align:right; font-size:11px; font-weight:normal;'>{end_t}</div></div>"
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
        html += f"<div style='text-decoration:{deco}; font-size:14px; width:100%; display:flex; align-items:center; justify-content:center; height:100%; line-height:1.2;'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)

# --- 프라이빗 메모장 (읽기 전용 뷰어) ---
if st.session_state.show_memo:
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin:0; font-size:15px; margin-bottom:8px; color:{t['text']};'>📝 {st.session_state.logged_in_user} 메모장 <span style='font-size:11px; font-weight:normal; opacity:0.6;'>(수정은 PC에서)</span></h3>", unsafe_allow_html=True)
    
    with st.container(height=300, border=True):
        if memos_list:
            for i, m in enumerate(memos_list):
                num = len(memos_list) - i
                text = m['memo_text']
                is_strike = m.get('is_strike', False)
                is_imp = m.get('is_important', False)
                
                prefix = "⭐ " if is_imp else ""
                deco = "line-through" if is_strike else "none"
                color = "gray" if is_strike else t['text']
                
                memo_line = f"""
                <div style="color:{color}; text-decoration:{deco}; font-size:14px; font-weight:bold; line-height:1.4; padding: 6px 2px; border-bottom: 1px solid {t['grid']};">
                    <b>{num}.</b> {prefix}{text}
                </div>
                """
                st.markdown(memo_line, unsafe_allow_html=True)
        else:
            st.info("저장된 메모가 없습니다.")