import streamlit as st
import anthropic
import os
import hashlib
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="세특 주제 추천",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── 스타일 ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

:root {
    --bg: #F7F4EE;
    --surface: #FFFFFF;
    --border: #E0D9CC;
    --accent: #2D5016;
    --accent-light: #4A7C2F;
    --accent-pale: #EBF2E4;
    --text: #1A1A1A;
    --text-muted: #6B6458;
    --danger: #C0392B;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    font-family: 'Noto Sans KR', sans-serif;
    color: var(--text);
}

.main-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 2rem;
}
.main-header h1 {
    font-family: 'Noto Serif KR', serif;
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    margin: 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-top: 0.4rem;
    font-weight: 300;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: var(--surface);
    border-radius: 8px 8px 0 0;
    border: 1px solid var(--border);
    border-bottom: none;
    padding: 0;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Noto Sans KR', sans-serif;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.75rem 1.5rem;
    color: var(--text-muted);
    border-radius: 0;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 1.5rem;
}

.passage-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    position: relative;
}
.passage-card h4 {
    font-family: 'Noto Serif KR', serif;
    font-size: 1rem;
    color: var(--accent);
    margin: 0 0 0.3rem;
}
.passage-card .keywords {
    font-size: 0.8rem;
    color: var(--text-muted);
}

.result-card {
    background: var(--accent-pale);
    border: 1px solid #C5DBA8;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.result-card h3 {
    font-family: 'Noto Serif KR', serif;
    color: var(--accent);
    font-size: 1.05rem;
    margin: 0 0 0.6rem;
}

.stTextInput input, .stTextArea textarea, .stSelectbox select {
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    background: var(--bg) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(45, 80, 22, 0.1) !important;
}

.stButton button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.5rem !important;
    transition: background 0.2s !important;
}
.stButton button:hover {
    background: var(--accent-light) !important;
}

.delete-btn button {
    background: transparent !important;
    color: var(--danger) !important;
    border: 1px solid var(--danger) !important;
    font-size: 0.8rem !important;
    padding: 0.25rem 0.75rem !important;
}
.delete-btn button:hover {
    background: var(--danger) !important;
    color: white !important;
}

hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 6px !important;
}

.stMultiSelect [data-baseweb="tag"] {
    background: var(--accent) !important;
}

#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# ── 유틸리티 ─────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    """비밀번호 SHA-256 해싱"""
    return hashlib.sha256(pw.strip().encode()).hexdigest()

def make_cache_key(career, major, interests, passage_ids) -> str:
    """API 캐시 키 생성 (동일 입력이면 같은 키)"""
    raw = f"{career.strip()}|{major.strip()}|{interests.strip()}|{sorted(passage_ids)}"
    return hashlib.md5(raw.encode()).hexdigest()

# ── Google Sheets 연동 ───────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def get_gspread_client():
    """gspread 클라이언트를 한 번만 생성"""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def _get_spreadsheet():
    client = get_gspread_client()
    return client.open_by_key(st.secrets["SHEET_ID"])

def _get_or_create_sheet(name, cols, rows=500):
    spreadsheet = _get_spreadsheet()
    try:
        return spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=name, rows=rows, cols=len(cols))
        sheet.append_row(cols)
        return sheet

def get_sheet():
    return _get_or_create_sheet("지문", ["id", "title", "summary"])

def get_auth_sheet():
    return _get_or_create_sheet("학생인증", ["학번", "이름", "비밀번호"])

def get_log_sheet():
    return _get_or_create_sheet("사용기록", ["날짜", "학번", "이름", "진로", "관심분야", "결과"])

def get_cache_sheet():
    return _get_or_create_sheet("캐시", ["key", "result", "created"])

def get_bonus_sheet():
    return _get_or_create_sheet("추가횟수", ["학번", "횟수", "적용월"])

# ── 지문 CRUD (TTL 캐시 적용) ────────────────────────────
@st.cache_data(ttl=300)
def load_passages():
    """지문 목록을 5분 캐시로 로드 (Sheets API 호출 최소화)"""
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        return rows
    except Exception as e:
        st.error(f"시트 로드 실패: {e}")
        return []

def save_passage(passage):
    try:
        sheet = get_sheet()
        sheet.append_row([
            passage["id"],
            passage["title"],
            passage["summary"]
        ])
        # 지문 변경 시 관련 캐시 무효화
        load_passages.clear()
        clear_result_cache()
    except Exception as e:
        st.error(f"저장 실패: {e}")

def delete_passage(passage_id):
    try:
        sheet = get_sheet()
        all_values = sheet.get_all_values()
        for i, row in enumerate(all_values):
            if row and str(row[0]) == str(passage_id):
                sheet.delete_rows(i + 1)
                break
        load_passages.clear()
        clear_result_cache()
    except Exception as e:
        st.error(f"삭제 실패: {e}")

# ── 학생 인증 ────────────────────────────────────────────
def find_student(student_id):
    try:
        sheet = get_auth_sheet()
        rows = sheet.get_all_records()
        for row in rows:
            if str(row.get("학번", "")) == str(student_id):
                return row
        return None
    except Exception:
        return None

def register_student(student_id, name, password):
    try:
        sheet = get_auth_sheet()
        sheet.append_row([student_id, name, hash_pw(password)])
        return True
    except Exception:
        return False

def verify_password(stored_hash, input_pw):
    """해싱된 비밀번호와 입력값 비교. 평문 레거시 데이터도 호환."""
    if stored_hash == hash_pw(input_pw):
        return True
    # 기존 평문 데이터 호환 (마이그레이션 전)
    if stored_hash == input_pw:
        return True
    return False

def reset_student_password(student_id, new_password):
    """관리자가 학생 비밀번호를 초기화"""
    try:
        sheet = get_auth_sheet()
        all_values = sheet.get_all_values()
        for i, row in enumerate(all_values):
            if row and str(row[0]) == str(student_id):
                sheet.update_cell(i + 1, 3, hash_pw(new_password))
                return True
        return False
    except Exception:
        return False

BASE_MONTHLY_LIMIT = 4

def get_student_limit(student_id):
    """학생의 이번 달 제한 횟수 반환 (기본 4 + 이번 달 추가횟수)"""
    this_month = datetime.now().strftime("%Y-%m")
    try:
        sheet = get_bonus_sheet()
        rows = sheet.get_all_records()
        extra = 0
        for row in rows:
            if str(row.get("학번", "")) == str(student_id) and str(row.get("적용월", "")) == this_month:
                try:
                    extra += int(row.get("횟수", 0) or 0)
                except (ValueError, TypeError):
                    pass
        return BASE_MONTHLY_LIMIT + extra
    except Exception:
        return BASE_MONTHLY_LIMIT

def grant_extra_usage(student_id, extra_count):
    """특정 학생에게 이번 달 추가 횟수 부여"""
    this_month = datetime.now().strftime("%Y-%m")
    try:
        sheet = get_bonus_sheet()
        sheet.append_row([str(student_id), extra_count, this_month])
        return True, get_student_limit(student_id) - BASE_MONTHLY_LIMIT
    except Exception:
        return False, 0

def reset_extra_usage(student_id):
    """특정 학생의 이번 달 추가 횟수 전부 삭제"""
    this_month = datetime.now().strftime("%Y-%m")
    try:
        sheet = get_bonus_sheet()
        all_values = sheet.get_all_values()
        # 뒤에서부터 삭제해야 인덱스가 안 밀림
        rows_to_delete = []
        for i, row in enumerate(all_values):
            if i == 0:  # 헤더 스킵
                continue
            if row and str(row[0]) == str(student_id) and len(row) > 2 and str(row[2]) == this_month:
                rows_to_delete.append(i + 1)
        for row_idx in reversed(rows_to_delete):
            sheet.delete_rows(row_idx)
        return True
    except Exception:
        return False

# ── 사용 기록 ────────────────────────────────────────────
@st.cache_data(ttl=120)
def check_monthly_usage(student_id):
    try:
        sheet = get_log_sheet()
        rows = sheet.get_all_records()
        this_month = datetime.now().strftime("%Y-%m")
        count = sum(1 for row in rows
                    if str(row.get("학번", "")) == str(student_id)
                    and str(row.get("날짜", ""))[:7] == this_month)
        return count
    except Exception:
        return 0

def save_usage_log(student_id, name, career, major, interests, result_text):
    try:
        sheet = get_log_sheet()
        # 결과도 함께 저장 (나중에 학생/교사가 다시 확인 가능)
        truncated = result_text[:3000] if result_text else ""
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            student_id,
            name,
            f"{career} / {major}",
            interests if interests else "",
            truncated
        ])
        check_monthly_usage.clear()
    except Exception as e:
        st.error(f"기록 저장 실패: {e}")

# ── 결과 캐싱 (동일 진로+지문 조합 재활용) ──────────────
def get_cached_result(cache_key):
    """캐시 시트에서 이전 결과 조회"""
    try:
        sheet = get_cache_sheet()
        rows = sheet.get_all_records()
        for row in rows:
            if str(row.get("key", "")) == cache_key:
                return row.get("result", "")
        return None
    except Exception:
        return None

def save_cached_result(cache_key, result_text):
    """결과를 캐시 시트에 저장"""
    try:
        sheet = get_cache_sheet()
        sheet.append_row([
            cache_key,
            result_text[:10000],
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ])
    except Exception:
        pass  # 캐시 저장 실패는 무시

def clear_result_cache():
    """지문 변경 시 캐시 전체 초기화"""
    try:
        sheet = get_cache_sheet()
        # 헤더만 남기고 전부 삭제
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            sheet.delete_rows(2, len(all_values))
    except Exception:
        pass

# ── Claude API ────────────────────────────────────────────
def get_claude_client():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

# ── 프롬프트 (지문 30개 이상 대응) ───────────────────────
MAX_SUMMARY_LEN = 80  # 지문당 요약 최대 글자수

def build_prompt(passages, career, major, interests):
    passage_text = ""
    for i, p in enumerate(passages, 1):
        summary = p.get("summary", "")
        # 지문이 많으면 요약을 잘라서 입력 토큰 절약
        if len(passages) > 15 and len(summary) > MAX_SUMMARY_LEN:
            summary = summary[:MAX_SUMMARY_LEN] + "…"
        passage_text += f"{i}. {p['title']}\n"
        passage_text += f"   요약: {summary}\n\n"

    return f"""당신은 고등학교 영어 교과 세부능력 및 특기사항(세특) 작성을 돕는 전문가입니다.

[수업에서 다룬 지문 목록]
{passage_text}

[학생 정보]
- 희망 진로: {career if career else '미입력'}
- 희망 학과: {major if major else '미입력'}
- 관심 분야: {interests if interests else '미입력'}

위 지문 중 학생의 진로·관심사에 가장 잘 연계되는 세특 주제를 정확히 3개만 추천하세요.

각 주제는 아래 형식으로 작성:

**[주제 번호]. 주제명**
- 📚 연계 지문: (위 목록에서 연결되는 지문 제목)
- 🔗 영어 교과 연계 근거: (지문의 어떤 내용이 이 주제와 연결되는지 1~2문장)
- 💡 추천 탐구 활동: (구체적 활동 1~2개)
- 📖 추천 도서/자료: (아래 도서 추천 규칙을 반드시 따를 것)

[도서 추천 규칙]
- 실제로 존재하는 도서만 추천하세요. 제목, 저자명 모두 정확해야 합니다.
- 한국어 번역본이 있는 경우 한국어 제목과 저자를 병기하세요.
- 도서명이 확실하지 않으면 절대 지어내지 말고, 대신 구체적인 검색 키워드를 제안하세요. (예: "○○○ 관련 도서는 '키워드1 + 키워드2'로 검색해보세요")
- 논문, TED 강연, 다큐멘터리 등 도서 외 자료도 추천 가능합니다.

주제는 고등학생이 실제 수행 가능한 현실적 수준으로 제안하세요."""

# ── 세션 초기화 ───────────────────────────────────────────
if "passages" not in st.session_state:
    st.session_state.passages = load_passages()
if "result" not in st.session_state:
    st.session_state.result = None
if "auth_student" not in st.session_state:
    st.session_state.auth_student = None

# ── 헤더 ─────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📖 영어 세특 주제 추천</h1>
    <p>수업 지문을 바탕으로 나만의 세특 주제를 찾아보세요</p>
</div>
""", unsafe_allow_html=True)

# ── 탭 구성 ──────────────────────────────────────────────
tab_student, tab_admin = st.tabs(["📝 주제 추천받기", "⚙️ 지문 관리 (선생님)"])

# ════════════════════════════════════════════════════════
# 학생용 탭
# ════════════════════════════════════════════════════════
with tab_student:
    passages = st.session_state.passages

    if not passages:
        st.info("📌 아직 등록된 지문이 없어요. 선생님께 지문을 등록해달라고 요청하세요!")
    else:
        # ── 로그인/등록 ──
        if not st.session_state.auth_student:
            st.markdown("#### 🔐 로그인 / 최초 등록")
            auth_mode = st.radio("", ["로그인", "최초 등록"], horizontal=True, label_visibility="collapsed")

            aid = st.text_input("학번", placeholder="예: 20101")
            apw = st.text_input("비밀번호", type="password", placeholder="본인이 설정한 비밀번호")

            if auth_mode == "최초 등록":
                aname = st.text_input("이름", placeholder="예: 홍길동")
                apw2 = st.text_input("비밀번호 확인", type="password")
                if st.button("등록하기", use_container_width=True):
                    if not aid or not aname or not apw:
                        st.warning("모든 항목을 입력해주세요.")
                    elif apw != apw2:
                        st.error("비밀번호가 일치하지 않습니다.")
                    elif find_student(aid):
                        st.error("이미 등록된 학번입니다. 로그인을 이용해주세요.")
                    else:
                        if register_student(aid, aname, apw):
                            st.session_state.auth_student = {"학번": aid, "이름": aname}
                            st.success(f"✅ {aname}님 등록 완료!")
                            st.rerun()
                        else:
                            st.error("등록 실패. 다시 시도해주세요.")
            else:
                if st.button("로그인", use_container_width=True):
                    if not aid or not apw:
                        st.warning("학번과 비밀번호를 입력해주세요.")
                    else:
                        student = find_student(aid)
                        if not student:
                            st.error("등록되지 않은 학번입니다. 최초 등록을 먼저 해주세요.")
                        elif not verify_password(str(student.get("비밀번호", "")), apw):
                            st.error("비밀번호가 틀렸습니다.")
                        else:
                            st.session_state.auth_student = {"학번": aid, "이름": student.get("이름", "")}
                            st.session_state.result = None
                            st.rerun()

        # ── 로그인 후 메인 화면 ──
        else:
            student = st.session_state.auth_student
            monthly = check_monthly_usage(student["학번"])
            limit = get_student_limit(student["학번"])

            col1, col2 = st.columns([1, 1.2], gap="large")

            with col1:
                st.markdown(f"#### 👋 {student['이름']}님 환영해요")
                st.caption(f"이번 달 {monthly}/{limit}회 사용")

                st.markdown(f"""
                <div style="background: var(--accent-pale); border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 1rem;">
                    <span style="font-size: 0.95rem;">📚 수업 지문 <strong>{len(passages)}개</strong>가 등록되어 있습니다.</span><br>
                    <span style="font-size: 0.82rem; color: var(--text-muted);">진로와 관심사를 입력하면 지문에서 맞춤 세특 주제를 추천해드려요.</span>
                </div>
                """, unsafe_allow_html=True)

                career = st.text_input("희망 진로", placeholder="예: 의사, 개발자, 교사...")
                major = st.text_input("희망 학과", placeholder="예: 의대, 컴퓨터공학과, 교육학과...")
                interests = st.text_input("관심 분야", placeholder="예: AI, 환경, 심리학, 경제...")

                if st.button("🚪 로그아웃", use_container_width=True):
                    st.session_state.auth_student = None
                    st.session_state.result = None
                    st.rerun()

            with col2:
                st.markdown("#### 세특 주제 추천")

                if st.button("✨ 추천 받기", use_container_width=True):
                    if not career and not major:
                        st.warning("희망 진로 또는 학과를 입력해주세요!")
                    elif monthly >= limit:
                        st.error(f"⚠️ 이번 달 사용 횟수({monthly}/{limit}회)를 초과했습니다. 다음 달에 다시 이용해주세요.")
                    else:
                        # 캐시 확인
                        passage_ids = [p.get("id", "") for p in passages]
                        cache_key = make_cache_key(career, major, interests, passage_ids)
                        cached = get_cached_result(cache_key)

                        if cached:
                            st.session_state.result = cached
                            save_usage_log(student["학번"], student["이름"], career, major, interests, cached)
                            st.caption(f"💡 이번 달 {monthly + 1}/{limit}회 사용 (캐시 활용)")
                        else:
                            client = get_claude_client()
                            if not client:
                                st.error("API 키가 설정되지 않았습니다.")
                            else:
                                with st.spinner("주제를 찾는 중..."):
                                    try:
                                        prompt = build_prompt(passages, career, major, interests)
                                        message = client.messages.create(
                                            model="claude-sonnet-4-6",
                                            max_tokens=2500,
                                            messages=[{"role": "user", "content": prompt}]
                                        )
                                        result_text = message.content[0].text
                                        st.session_state.result = result_text

                                        # 캐시 & 로그 저장
                                        save_cached_result(cache_key, result_text)
                                        save_usage_log(
                                            student["학번"], student["이름"],
                                            career, major, interests, result_text
                                        )
                                        st.caption(f"💡 이번 달 {monthly + 1}/{limit}회 사용했습니다.")

                                    except anthropic.RateLimitError:
                                        st.error("⏳ 요청이 많아요. 30초 후 다시 시도해주세요.")
                                    except anthropic.AuthenticationError:
                                        st.error("🔑 API 키에 문제가 있습니다. 선생님께 문의하세요.")
                                    except anthropic.APIError as e:
                                        if "overloaded" in str(e).lower() or "529" in str(e):
                                            st.error("⏳ 서버가 일시적으로 바빠요. 1~2분 후 다시 시도해주세요.")
                                        else:
                                            st.error(f"API 오류가 발생했습니다: {e}")
                                    except Exception as e:
                                        st.error(f"예상치 못한 오류: {e}")

                if st.session_state.result:
                    st.markdown(st.session_state.result)
                    st.download_button(
                        label="📥 결과 저장 (txt)",
                        data=st.session_state.result,
                        file_name=f"세특추천_{student['이름']}_{datetime.now().strftime('%Y%m%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

# ════════════════════════════════════════════════════════
# 관리자 탭
# ════════════════════════════════════════════════════════
with tab_admin:
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False

    if not st.session_state.admin_auth:
        st.markdown("#### 🔐 관리자 로그인")
        pw = st.text_input("비밀번호", type="password", key="admin_pw_input")
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "teacher1234")
        if st.button("로그인", key="admin_login_btn"):
            if pw == admin_pw:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    else:
        col_form, col_list = st.columns([1, 1.2], gap="large")

        with col_form:
            st.markdown("#### ➕ 지문 추가")

            new_title = st.text_input("지문 제목 *", placeholder="예: The Future of AI in Healthcare")
            new_summary = st.text_area(
                "지문 내용 요약 *",
                placeholder="예: AI가 의료 진단에 활용되는 방식과 윤리적 문제를 다룬 지문. 알고리즘 편향, 의사결정 책임, 환자 데이터 보호 등을 논의함.",
                height=150
            )
            st.caption("💡 지문의 핵심 주제와 다루는 개념을 2~4문장으로 요약해주세요.")

            if st.button("💾 지문 저장", use_container_width=True):
                if not new_title or not new_summary:
                    st.warning("제목과 요약은 필수입니다!")
                else:
                    new_passage = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "title": new_title,
                        "summary": new_summary
                    }
                    save_passage(new_passage)
                    st.session_state.passages = load_passages()
                    st.success(f"✅ '{new_title}' 추가 완료!")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### 🎫 학생 추가 횟수 부여")
            st.caption("이번 달에만 적용됩니다. 다음 달에는 자동으로 기본 4회로 돌아갑니다.")

            bonus_id = st.text_input("학번", placeholder="예: 20101", key="bonus_student_id")
            bonus_count = st.number_input("추가할 횟수", min_value=1, max_value=20, value=2, key="bonus_count")

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("➕ 횟수 부여", use_container_width=True, key="grant_btn"):
                    if not bonus_id:
                        st.warning("학번을 입력해주세요.")
                    else:
                        target = find_student(bonus_id)
                        if not target:
                            st.error("등록되지 않은 학번입니다.")
                        else:
                            ok, total = grant_extra_usage(bonus_id, bonus_count)
                            if ok:
                                this_month = datetime.now().strftime("%Y년 %m월")
                                new_limit = get_student_limit(bonus_id)
                                st.success(f"✅ {target.get('이름', '')}({bonus_id}) — {this_month} 총 {new_limit}회 사용 가능")
                            else:
                                st.error("부여 실패. 다시 시도해주세요.")
            with bc2:
                if st.button("🔄 추가분 초기화", use_container_width=True, key="reset_btn"):
                    if not bonus_id:
                        st.warning("학번을 입력해주세요.")
                    else:
                        target = find_student(bonus_id)
                        if not target:
                            st.error("등록되지 않은 학번입니다.")
                        else:
                            if reset_extra_usage(bonus_id):
                                st.success(f"✅ {target.get('이름', '')}({bonus_id}) — 이번 달 기본 {BASE_MONTHLY_LIMIT}회로 초기화")
                            else:
                                st.error("초기화 실패.")

            st.markdown("---")
            st.markdown("#### 🔑 학생 비밀번호 초기화")
            reset_id = st.text_input("학번", placeholder="예: 20101", key="reset_pw_student_id")
            reset_pw = st.text_input("새 비밀번호", type="password", key="reset_pw_new")
            if st.button("🔑 비밀번호 초기화", use_container_width=True, key="reset_pw_btn"):
                if not reset_id or not reset_pw:
                    st.warning("학번과 새 비밀번호를 입력해주세요.")
                else:
                    target = find_student(reset_id)
                    if not target:
                        st.error("등록되지 않은 학번입니다.")
                    else:
                        if reset_student_password(reset_id, reset_pw):
                            st.success(f"✅ {target.get('이름', '')}({reset_id}) 비밀번호가 초기화되었습니다.")
                        else:
                            st.error("초기화 실패. 다시 시도해주세요.")

            st.markdown("---")
            if st.button("🚪 로그아웃", use_container_width=True, key="admin_logout"):
                st.session_state.admin_auth = False
                st.rerun()

        with col_list:
            st.markdown(f"#### 📋 등록된 지문 ({len(st.session_state.passages)}개)")

            if not st.session_state.passages:
                st.info("등록된 지문이 없습니다.")
            else:
                for i, p in enumerate(st.session_state.passages):
                    with st.container():
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            summary_preview = str(p.get('summary', ''))[:60]
                            st.markdown(f"""
                            <div class="passage-card">
                                <h4>{p['title']}</h4>
                                {"<br><small style='color:#888;margin-top:4px;display:block'>" + summary_preview + "...</small>" if summary_preview else ""}
                            </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                            if st.button("삭제", key=f"del_{p['id']}"):
                                delete_passage(p['id'])
                                st.session_state.passages = [x for x in st.session_state.passages if x['id'] != p['id']]
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
