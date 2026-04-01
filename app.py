import os
# 🚀 gRPC 통신 지연 및 데드락 방지 환경변수
os.environ["GRPC_DNS_RESOLVER"] = "native"
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import csv
import base64
import json
import textwrap # 🔥 꼬인 비밀키를 복구하기 위한 모듈 추가
from datetime import datetime, timedelta, timezone

# 1. 페이지 기본 설정
st.set_page_config(page_title="모바일 시간표", page_icon="📅", layout="centered")

# 2. 모바일 최적화 CSS
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

status = st.empty()

# 3. CSV 데이터 로딩
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

# 4. 상태 관리 초기화
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0
if 'show_zero' not in st.session_state: st.session_state.show_zero = False
if 'show_extra' not in st.session_state: st.session_state.show_extra = False
if 'show_memo' not in st.session_state: st.session_state.show_memo = True
if 'teacher' not in st.session_state: st.session_state.teacher = "표민호"
if 'theme_idx' not in st.session_state: st.session_state.theme_idx = 0
if 'font_name' not in st.session_state: st.session_state.font_name = "맑은 고딕"

themes = [
    { 'name': '모던 다크', 'bg': '#2c3e50', 'top': '#1a252f', 'grid': '#34495e', 'head_bg': '#2c3e50', 'head_fg': 'white', 'per_bg': '#7f8c8d', 'per_fg': 'white', 'cell_bg': '#ecf0f1', 'lunch_bg': '#95a5a6', 'cell_fg': '#2c3e50', 'hl_per': '#e74c3c', 'hl_cell': '#f1c40f' },
    { 'name': '웜 파스텔', 'bg': '#fdf6e3', 'top': '#e4d5b7', 'grid': '#eee8d5', 'head_bg': '#d6caba', 'head_fg': '#333333', 'per_bg': '#e8e2d2', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#f0e6d2', 'cell_fg': '#4a4a4a', 'hl_per': '#ffb6b9', 'hl_cell': '#fae3d9' },
    { 'name': '클래식 블루', 'bg': '#e0eaf5', 'top': '#4a90e2', 'grid': '#d0dceb', 'head_bg': '#5c9ce6', 'head_fg': 'white', 'per_bg': '#a8c2e0', 'per_fg': '#333333', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e0f0', 'cell_fg': '#2c3e50', 'hl_per': '#f39c12', 'hl_cell': '#fde3a7' },
    { 'name': '포레스트', 'bg': '#e9ede7', 'top': '#2c5344', 'grid': '#d0d8d3', 'head_bg': '#3b6a57', 'head_fg': 'white', 'per_bg': '#8ba89a', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d0e8d7', 'cell_fg': '#1a3026', 'hl_per': '#d35400', 'hl_cell': '#f9e79f' },
    { 'name': '모노톤', 'bg': '#f5f5f5', 'top': '#333333', 'grid': '#e0e0e0', 'head_bg': '#555555', 'head_fg': 'white', 'per_bg': '#999999', 'per_fg': 'white', 'cell_bg': '#ffffff', 'lunch_bg': '#d4d4d4', 'cell_fg': '#000000', 'hl_per': '#d90429', 'hl_cell': '#edf2f4' }
]
t = themes[st.session_state.theme_idx]
st.markdown(f"<style>.stApp {{ background-color: {t['bg']} !important; font-family: '{st.session_state.font_name}', sans-serif; }}</style>", unsafe_allow_html=True)

# 💡 5. Firebase 초기화 (🔥 훼손된 비밀키 100% 원상복구 로직 🔥)
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["FIREBASE_KEY"])
        
        # Secrets에서 가져온 키 문자열
        raw_key = key_dict.get("private_key", "")
        
        # 키가 손상되었든, 줄바꿈이 없든, 공백이 섞였든 상관없이 완벽한 형태로 재조립합니다.
        if "BEGIN PRIVATE KEY" in raw_key:
            # 헤더와 푸터 사이의 '진짜 암호 본문'만 추출
            body = raw_key.split("BEGIN PRIVATE KEY-----")[1].split("-----END PRIVATE KEY")[0]
            # 쓸데없는 공백, 줄바꿈 기호 전부 삭제
            clean_body = body.replace(" ", "").replace("\\n", "").replace("\n", "")
            # 구글 서버가 원하는 완벽한 64글자 단위 줄바꿈으로 재포장
            key_dict["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{textwrap.fill(clean_body, 64)}\n-----END PRIVATE KEY-----\n"

        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        status.error(f"인증 초기화 오류: {e}")
        st.stop()

db = firestore.client()

# 6. 클라우드 데이터 선행 로드
custom_data = {}
memos_list = []
try:
    docs = db.collection('custom_data').get(timeout=5)
    for doc in docs: 
        custom_data[doc.id] = doc.to_dict()
    
    memo_doc = db.collection('memos').document(st.session_state.teacher).get(timeout=5)
    if memo_doc.exists: 
        memos_list = memo_doc.to_dict().get('memos_list', [])
    status.empty()
except Exception as e: 
    status.error(f"🚨 데이터 연결 실패: {e}")
    st.stop() # 에러 시 여기서 멈춤

t_custom = custom_data.get(st.session_state.teacher, {})
memo_count = len(memos_list)

# 7. 모달창 설정
@st.dialog("일정 수정")
def edit_modal(date_key, current_val):
    date_part, period_part = date_key.split('_')
    st.caption(f"{date_part} | {period_part}교시")
    input_val = current_val if current_val != "__STRIKE__" else ""
    input_val = input_val.replace('<br>', '\n')
    
    new_subj = st.text_area("내용 (줄바꿈 가능):", value=input_val, label_visibility="collapsed", height=80)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("✏️수정", use_container_width=True):
        if new_subj.strip(): db.collection('custom_data').document(st.session_state.teacher).set({date_key: new_subj.strip()}, merge=True)
        st.rerun()
    if c2.button("✔️완결", use_container_width=True):
        db.collection('custom_data').document(st.session_state.teacher).set({date_key: "__STRIKE__"}, merge=True)
        st.rerun()
    if c3.button("🗑️삭제", use_container_width=True):
        db.collection('custom_data').document(st.session_state.teacher).update({date_key: firestore.DELETE_FIELD})
        st.rerun()

@st.dialog("메모 관리")
def memo_modal(idx):
    idx = int(idx)
    if idx < 0 or idx >= len(memos_list): return
    current_memo = memos_list[idx]
    is_strike = current_memo.get('strike', False)
    
    new_text = st.text_area("메모 수정:", value=current_memo.get('text', ''), label_visibility="collapsed", height=80)
    
    c1, c2, c3 = st.columns(3)
    if c1.button("✏️수정", use_container_width=True):
        if new_text.strip():
            memos_list[idx]['text'] = new_text.strip()
            db.collection('memos').document(st.session_state.teacher).set({'memos_list': memos_list})
        st.rerun()
    if c2.button("✔️완결", use_container_width=True):
        memos_list[idx]['strike'] = not is_strike
        db.collection('memos').document(st.session_state.teacher).set({'memos_list': memos_list})
        st.rerun()
    if c3.button("🗑️삭제", use_container_width=True):
        memos_list.pop(idx)
        db.collection('memos').document(st.session_state.teacher).set({'memos_list': memos_list})
        st.rerun()

@st.dialog("새 메모 추가")
def add_memo_modal():
    new_text = st.text_area("메모 내용을 입력하세요:", height=80)
    if st.button("💾 저장", use_container_width=True):
        if new_text.strip():
            memos_list.insert(0, {'text': new_text.strip(), 'strike': False, 'important': False})
            db.collection('memos').document(st.session_state.teacher).set({'memos_list': memos_list})
        st.rerun()

@st.dialog("메모 다중 삭제")
def delete_memos_modal():
    st.markdown("<span style='font-size:13px;'>삭제할 메모를 선택하세요.</span>", unsafe_allow_html=True)
    to_delete = []
    for i, m in enumerate(memos_list):
        num = len(memos_list) - i
        short_text = m.get('text', '')
        if len(short_text) > 15: short_text = short_text[:15] + "..."
        if st.checkbox(f"{num}. {short_text}", key=f"del_cb_{i}"):
            to_delete.append(i)
    st.markdown("---")
    if st.button("🗑️ 확인 (선택 삭제)", use_container_width=True):
        if to_delete:
            for i in sorted(to_delete, reverse=True): memos_list.pop(i)
            db.collection('memos').document(st.session_state.teacher).set({'memos_list': memos_list})
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
    elif act == "del_memo": delete_memos_modal()

# 8. 로고 및 헤더 삽입
logo_html = "📅&nbsp;"
if os.path.exists("logo.jpg"):
    with open("logo.jpg", "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/jpeg;base64,{logo_b64}' width='22' style='border-radius:4px; margin-right:6px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);'>"

st.markdown(f"""
<div style='color:{t['head_fg']}; font-size:16px; font-weight:bold; margin-bottom:12px; display:flex; align-items:center;'>
    {logo_html} 2026학년도 1학기 시간표
</div>
""", unsafe_allow_html=True)

# 9. 상단 메뉴 구성
st.markdown(f"<div style='background-color:{t['top']}; padding:8px; border-radius:10px; margin-bottom:8px;'>", unsafe_allow_html=True)

r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns([1.8, 0.8, 0.8, 0.8, 0.8])
with r1_c1:
    teacher_list = list(teachers_data.keys()) if teachers_data else ["표민호"]
    selected = st.selectbox("교사", teacher_list, index=teacher_list.index(st.session_state.teacher) if st.session_state.teacher in teacher_list else 0, label_visibility="collapsed")
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
            st.session_state.theme_idx = [th['name'] for th in themes].index(new_theme)
            st.rerun()
        new_font = st.selectbox("A 폰트", ["맑은 고딕", "바탕", "돋움", "굴림", "Arial"], index=["맑은 고딕", "바탕", "돋움", "굴림", "Arial"].index(st.session_state.font_name))
        if new_font != st.session_state.font_name:
            st.session_state.font_name = new_font
            st.rerun()

r2_c1, r2_c2, r2_c3 = st.columns(3)
with r2_c1:
    m_icon = f"📝 메모({memo_count}) ON" if st.session_state.show_memo else f"📝 메모({memo_count}) OFF"
    if st.button(m_icon, use_container_width=True): st.session_state.show_memo = not st.session_state.show_memo; st.rerun()
with r2_c2:
    z_icon = "☀️ 조회 ON" if st.session_state.show_zero else "☀️ 조회 OFF"
    if st.button(z_icon, use_container_width=True): st.session_state.show_zero = not st.session_state.show_zero; st.rerun()
with r2_c3:
    e_icon = "🌙 8,9교시 ON" if st.session_state.show_extra else "🌙 8,9교시 OFF"
    if st.button(e_icon, use_container_width=True): st.session_state.show_extra = not st.session_state.show_extra; st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# 10. 시간 및 그리드 로직
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

# 11. HTML 표 렌더링
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
            if s_idx < len(base_schedule.get(day, [])):
                subject = base_schedule[day][s_idx]

        is_strike = False
        is_custom = False

        if date_key in t_custom:
            val = t_custom[date_key]
            if val == "__STRIKE__":
                is_strike = True; is_custom = True
            else:
                subject = val; is_custom = True

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
        if period not in ["점심", "조회"]:
            html += f"<a href='{link_href}' target='_self' class='cell-link'><div class='cell-content' style='text-decoration:{deco}; line-height:1.2;'>{display}</div></a>"
        else:
            html += f"<div class='cell-content' style='text-decoration:{deco}; line-height:1.2;'>{display}</div>"
        html += "</td>"
        
    html += "</tr>"
html += "</table></div>"

st.markdown(html, unsafe_allow_html=True)

# 12. 클릭 가능한 인터랙티브 메모장
if st.session_state.show_memo:
    memo_html = f"<div style='background-color:{t['bg']}; padding:8px; border: 2px solid {t['grid']}; border-top:none; border-bottom-left-radius:8px; border-bottom-right-radius:8px;'><div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 4px;'><div style='font-size:14px; font-weight:bold; color:{t['head_fg']};'>📝 메모</div><div style='display: flex; gap: 8px;'><a href='/?action=add_memo' target='_self' class='action-btn' style='background-color:{t['top']}; color:{t['head_fg']} !important; padding:4px 12px; border-radius:5px; font-size:12px; border:1px solid {t['grid']}; box-shadow: 0 1px 2px rgba(0,0,0,0.2);'>➕</a><a href='/?action=del_memo' target='_self' class='action-btn' style='background-color:{t['top']}; color:{t['head_fg']} !important; padding:4px 12px; border-radius:5px; font-size:12px; border:1px solid {t['grid']}; box-shadow: 0 1px 2px rgba(0,0,0,0.2);'>➖</a></div></div><div style='max-height:160px; overflow-y:auto;'>"
    if memos_list:
        for i, m in enumerate(memos_list):
            num = len(memos_list) - i
            text = m.get('text', '')
            is_strike = m.get('strike', False)
            is_imp = m.get('important', False)
            prefix = "⭐ " if is_imp else ""
            text_color = "#95a5a6" if is_strike else t['head_fg']
            deco = "line-through" if is_strike else "none"
            link_href = f"/?memo_idx={i}"
            memo_html += f"<a href='{link_href}' target='_self' class='memo-link'><div style='color:{text_color}; text-decoration:{deco}; font-size:clamp(12px, 3.8vw, 14px); margin-bottom:6px; line-height: 1.4; padding:6px; background-color:{t['top']}; border-radius:5px;'><b>{num}.</b> {prefix}{text}</div></a>"
    else:
        memo_html += f"<div style='font-size:12px; color:{t['head_fg']}; text-align:center; padding:10px;'>저장된 메모가 없습니다.</div>"
    
    memo_html += "</div></div>"
    st.markdown(memo_html, unsafe_allow_html=True)