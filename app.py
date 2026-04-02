import streamlit as st
import requests
import csv
import os
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
if 'memo_expanded' not in st.session_state: st.session_state.memo_expanded = False # 메모장 늘이기/축소 상태

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f', 'text': '#ffffff' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9', 'text': '#333333' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7', 'text': '#2c3e50' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f', 'text': '#1a3026' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4', 'text': '#222222' }
]
t = themes[st.session_state.theme_idx]

# 💡 모바일 최적화 CSS (가독성 및 표 디자인 완전 개선)
st.markdown(f"""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        .stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; color: {t['text']} !important; }}
        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp div[data-testid="stMarkdownContainer"] {{ color: {t['text']} !important; }}
        .block-container {{ padding: 1rem 0.5rem !important; }}
        header {{ visibility: hidden; }}
        
        .stTabs [data-baseweb="tab-list"] button {{ color: {t['text']} !important; opacity: 0.7; font-size: 16px; }}
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{ opacity: 1; border-bottom: 3px solid {t['hl_per']} !important; font-weight: bold; }}
        
        .stButton>button {{ height: 42px !important; border-radius: 8px !important; font-size: 15px !important; font-weight: bold !important; background-color: {t['top']} !important; color: {t['text']} !important; border: 1px solid {t['grid']} !important; }}
        .stButton>button[data-testid="baseButton-primary"] {{ background-color: {t['hl_per']} !important; color: #ffffff !important; border: none !important; }}
        
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

# --- 모달창 모음 (가독성 개선 및 새로운 메모 기능들) ---
@st.dialog("📅 내 시간표 직접 수정")
def edit_timetable_modal():
    # 💡 모달창 안내문구 가독성 100% 보장 디자인
    st.markdown(f"<div style='color:{t['text']}; background-color:{t['top']}; padding:12px; border-radius:8px; margin-bottom:15px; font-weight:bold; border-left:4px solid {t['hl_per']};'>💡 수정할 날짜와 교시를 선택하세요.</div>", unsafe_allow_html=True)
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
    if cb1.button("💾 저장", use_container_width=True, type="primary"):
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

@st.dialog("➕ 새 메모 작성")
def add_memo_modal():
    new_text = st.text_area("메모 내용을 입력하세요:", height=100)
    if st.button("💾 저장", use_container_width=True, type="primary"):
        if new_text.strip(): requests.post(f"{SUPABASE_URL}/rest/v1/memos", headers=HEADERS, json={"teacher_name": st.session_state.logged_in_user, "memo_text": new_text.strip()})
        st.rerun()

@st.dialog("✏️ 메모 개별 수정")
def edit_memos_modal():
    st.markdown(f"<div style='color:{t['text']}; background-color:{t['top']}; padding:10px; border-radius:5px; margin-bottom:10px;'>수정할 메모를 선택하세요.</div>", unsafe_allow_html=True)
    if not memos_list:
        st.info("저장된 메모가 없습니다.")
        return
    memo_opts = {m['id']: m['memo_text'][:20] + ("..." if len(m['memo_text'])>20 else "") for m in memos_list}
    sel_id = st.selectbox("메모 선택", list(memo_opts.keys()), format_func=lambda x: memo_opts[x], label_visibility="collapsed")
    curr_text = next(m['memo_text'] for m in memos_list if m['id'] == sel_id)
    new_text = st.text_area("내용 수정:", value=curr_text, height=100)
    if st.button("💾 저장하기", type="primary", use_container_width=True):
        if new_text.strip(): requests.patch(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{sel_id}", headers=HEADERS, json={"memo_text": new_text.strip()})
        st.rerun()

@st.dialog("➖ 다중 선택 삭제")
def delete_memos_modal():
    st.markdown(f"<div style='color:{t['text']}; background-color:{t['top']}; padding:10px; border-radius:5px; margin-bottom:10px;'>삭제할 메모를 모두 체크하세요.</div>", unsafe_allow_html=True)
    to_delete = []
    for m in memos_list:
        if st.checkbox(m['memo_text'], key=f"del_{m['id']}"):
            to_delete.append(m['id'])
    if st.button("🗑️ 확인 (선택 삭제)", type="primary", use_container_width=True):
        if to_delete:
            for mid in to_delete: requests.delete(f"{SUPABASE_URL}/rest/v1/memos?id=eq.{mid}", headers=HEADERS)
        st.rerun()

@st.dialog("🗑️ 메모 전체 삭제")
def delete_all_memos_modal():
    st.warning("정말로 모든 메모를 비우시겠습니까? (복구 불가)")
    if st.button("🚨 네, 모두 삭제합니다.", type="primary", use_container_width=True):
        requests.delete(f"{SUPABASE_URL}/rest/v1/memos?teacher_name=eq.{st.session_state.logged_in_user}", headers=HEADERS)
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
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns([2.1, 1.2, 1.4, 1.2, 1.0])
with r1_c1:
    teacher_list = list(teachers_data.keys()) if teachers_data else [st.session_state.logged_in_user]
    idx = teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0
    selected = st.selectbox("교사 선택", teacher_list, index=idx, label_visibility="collapsed")
    if selected != st.session_state.teacher:
        st.session_state.teacher = selected
        st.rerun()
with r1_c2:
    if st.button("◀ 이전", use_container_width=True): st.session_state.week_offset -= 1
with r1_c3:
    # 💡 이번 주일 때는 Primary 컬러로 강조!
    btn_type = "primary" if st.session_state.week_offset == 0 else "secondary"
    if st.button("이번 주", use_container_width=True, type=btn_type): st.session_state.week_offset = 0
with r1_c4:
    if st.button("다음 ▶", use_container_width=True): st.session_state.week_offset += 1
with r1_c5:
    # 💡 팝오버를 use_container_width로 사용하여 가운데 꽉 차고 예쁘게 정렬
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


# --- 시간표 렌더링 ---
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

# 💡 모바일 최적화: 날짜 14px, 시간 13px로 확대 / 셀 테두리 깨짐 방지(box-shadow: inset 적용)
html = f"""
<style>
    .mobile-table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 15px; }}
    .mobile-table th {{ border: 1px solid {t['grid']}; padding: 6px 2px; text-align: center; font-size: 16px; height: 50px; }}
    .mobile-table td {{ border: 1px solid {t['grid']}; padding: 4px; text-align: center; vertical-align: middle; height: 70px; word-break: keep-all; font-weight: bold; font-size: 15px; }}
    
    /* 테두리 대신 안쪽 그림자를 써서 표가 우그러지거나 칸을 벗어나는 것을 100% 방지 */
    .hl-border-red {{ box-shadow: inset 0 0 0 3px {t['hl_per']} !important; z-index: 10; }}
    .hl-border-yellow {{ box-shadow: inset 0 0 0 3px {t['hl_cell']} !important; z-index: 10; }}
    .hl-fill-yellow {{ background-color: {t['hl_cell']} !important; color: black !important; box-shadow: inset 0 0 0 3px #d4ac0d !important; }}
    
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
    html += f"<th {th_class} style='background-color:{th_bg}; color:{th_fg};'>{day}<br><span style='font-size:14px; font-weight:normal;'>({date_str})</span></th>"
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
    formatted_time = f"<div style='line-height:1.1; width:100%; padding:0 3px;'><div style='text-align:left;'>{start_t}~</div><div style='text-align:right;'>{end_t}</div></div>"
    html += f"<td {td_period_class} style='background-color:{p_bg}; color:{p_fg}; font-size:15px;'><b>{period}</b><br><span style='font-size:13px; font-weight:normal; display:inline-block; width:100%;'>{formatted_time}</span></td>"
    
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

        html += f"<td {td_cell_class} style='background-color:{bg}; color:{fg};'>"
        html += f"<div class='cell-content' style='text-decoration:{deco};'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)

# --- 시간표 수정 버튼 ---
st.markdown("<br>", unsafe_allow_html=True)
if is_my_schedule:
    if st.button("✏️ 이번 주 시간표 직접 수정하기", use_container_width=True, type="primary"):
        edit_timetable_modal()

# --- 💡 전면 개편된 프라이빗 메모장 (가독성/기능 끝판왕) ---
if st.session_state.show_memo:
    st.markdown("---")
    st.markdown(f"<h3 style='margin:0; font-size:18px; margin-bottom:8px;'>📝 {st.session_state.logged_in_user} 메모장</h3>", unsafe_allow_html=True)
    
    # 💡 조종석 패널 (5개의 버튼)
    cb1, cb2, cb3, cb4, cb5 = st.columns(5)
    if cb1.button("➕추가", use_container_width=True): add_memo_modal()
    if cb2.button("✏️수정", use_container_width=True): edit_memos_modal()
    if cb3.button("➖선택", use_container_width=True): delete_memos_modal()
    if cb4.button("🗑️전체", use_container_width=True): delete_all_memos_modal()
    exp_text = "🔼축소" if st.session_state.memo_expanded else "🔽펼침"
    if cb5.button(exp_text, use_container_width=True): 
        st.session_state.memo_expanded = not st.session_state.memo_expanded
        st.rerun()
        
    st.markdown("<div style='margin-bottom:5px;'></div>", unsafe_allow_html=True)
    
    # 💡 메모 출력 구역 (넘버링 + 완벽한 줄간격 통제)
    max_h = "500px" if st.session_state.memo_expanded else "150px"
    memo_html = f"<div style='background-color:{t['top']}; padding:15px; border-radius:8px; max-height:{max_h}; overflow-y:auto; box-shadow:inset 0 2px 4px rgba(0,0,0,0.05);'>"
    if memos_list:
        for i, m in enumerate(memos_list):
            num = len(memos_list) - i
            deco = "line-through" if m.get('is_strike') else "none"
            color = "#95a5a6" if m.get('is_strike') else t['text']
            
            # PC버전과 동일하게 번호 매기기 + 적절한 줄간격(line-height 1.4)
            memo_html += f"<div style='color:{color}; text-decoration:{deco}; font-size:15px; margin-bottom:8px; line-height:1.4; border-bottom:1px solid {t['grid']}; padding-bottom:8px;'><b>{num}.</b> {m['memo_text']}</div>"
    else:
        memo_html += f"<div style='font-size:14px; opacity:0.7; text-align:center;'>저장된 메모가 없습니다. [+추가] 버튼을 눌러보세요!</div>"
    
    memo_html += "</div>"
    st.markdown(memo_html, unsafe_allow_html=True)