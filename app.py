import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime

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

/* 헤더 */
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

/* 탭 */
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

/* 카드 */
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
.passage-card .grade-badge {
    display: inline-block;
    background: var(--accent-pale);
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 500;
    padding: 0.15rem 0.5rem;
    border-radius: 20px;
    margin-right: 0.5rem;
}

/* 추천 결과 */
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

/* 입력 필드 */
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

/* 버튼 */
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

/* 삭제 버튼 */
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

/* 구분선 */
hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
}

/* 알림 */
.stSuccess, .stError, .stWarning, .stInfo {
    border-radius: 6px !important;
}

/* 멀티셀렉트 */
.stMultiSelect [data-baseweb="tag"] {
    background: var(--accent) !important;
}

/* 숨기기 */
#MainMenu, footer, header {visibility: hidden;}
.stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# ── 데이터 파일 경로 ──────────────────────────────────────
DATA_FILE = "passages.json"

def load_passages():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_passages(passages):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(passages, f, ensure_ascii=False, indent=2)

# ── Gemini 설정 ───────────────────────────────────────────
def get_gemini_model():
    api_key = st.secrets.get("GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")

# ── 추천 프롬프트 생성 ────────────────────────────────────
def build_prompt(passages, career, interests, grade):
    passage_summary = ""
    for i, p in enumerate(passages, 1):
        passage_summary += f"{i}. [{p.get('grade','전체')}] {p['title']}\n"
        passage_summary += f"   핵심 키워드: {p['keywords']}\n"
        if p.get('summary'):
            passage_summary += f"   주제 요약: {p['summary']}\n"
        passage_summary += "\n"

    return f"""당신은 고등학교 영어 교과 세부능력 및 특기사항(세특) 작성을 돕는 전문가입니다.

[수업에서 다룬 지문 목록]
{passage_summary}

[학생 정보]
- 학년: {grade}
- 희망 진로/학과: {career}
- 관심 분야: {', '.join(interests) if interests else '없음'}

위 지문 내용을 바탕으로, 이 학생의 진로와 관심사에 연계할 수 있는 세특 주제를 3~5개 추천해주세요.

각 주제는 반드시 아래 형식으로 작성하세요:

**[주제 번호]. 주제명**
- 📚 연계 지문: (위 지문 목록에서 연결되는 지문 제목)
- 🔗 영어 교과 연계 근거: (지문의 어떤 내용이 이 주제와 연결되는지 1~2문장)
- 💡 추천 탐구 활동: (구체적인 활동 1~2개)
- 📖 추천 도서/자료: (제목과 한 줄 소개 1~2개)

주제는 실제로 고등학생이 수행할 수 있는 현실적인 수준으로 제안해주세요.
"""

# ── 세션 초기화 ───────────────────────────────────────────
if "passages" not in st.session_state:
    st.session_state.passages = load_passages()
if "result" not in st.session_state:
    st.session_state.result = None

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
        col1, col2 = st.columns([1, 1.2], gap="large")

        with col1:
            st.markdown("#### 내 정보 입력")
            grade = st.selectbox("학년", ["1학년", "2학년", "3학년"])
            career = st.text_input("희망 진로 / 학과", placeholder="예: 의대, 컴퓨터공학과, 환경공학...")
            
            interest_options = ["과학/공학", "사회/정치", "경제/경영", "의학/보건", "환경/생태", 
                                "문학/인문", "예술/문화", "교육", "법학", "심리학", "기타"]
            interests = st.multiselect("관심 분야 (복수 선택 가능)", interest_options)
            
            st.markdown("---")
            st.markdown("#### 수업 지문 목록")
            st.caption(f"총 {len(passages)}개 지문 등록됨")
            for p in passages:
                st.markdown(f"""
                <div class="passage-card">
                    <h4>{p['title']}</h4>
                    <span class="grade-badge">{p.get('grade', '전체')}</span>
                    <span class="keywords">🏷 {p['keywords']}</span>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### 세특 주제 추천")
            
            if st.button("✨ 추천 받기", use_container_width=True):
                if not career:
                    st.warning("희망 진로/학과를 입력해주세요!")
                else:
                    model = get_gemini_model()
                    if not model:
                        st.error("API 키가 설정되지 않았습니다. `.streamlit/secrets.toml`에 `GEMINI_API_KEY`를 추가해주세요.")
                    else:
                        with st.spinner("주제를 찾는 중..."):
                            prompt = build_prompt(passages, career, interests, grade)
                            response = model.generate_content(prompt)
                            st.session_state.result = response.text

            if st.session_state.result:
                st.markdown(st.session_state.result)
                
                st.download_button(
                    label="📥 결과 저장 (txt)",
                    data=st.session_state.result,
                    file_name=f"세특추천_{career}_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

# ════════════════════════════════════════════════════════
# 관리자 탭
# ════════════════════════════════════════════════════════
with tab_admin:
    # 간단한 비밀번호
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False

    if not st.session_state.admin_auth:
        st.markdown("#### 🔐 관리자 로그인")
        pw = st.text_input("비밀번호", type="password")
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "teacher1234")
        if st.button("로그인"):
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
            new_grade = st.selectbox("대상 학년", ["전체", "1학년", "2학년", "3학년"])
            new_keywords = st.text_input("핵심 키워드 *", placeholder="예: AI, 의료, 진단, 윤리")
            new_summary = st.text_area("주제 요약 (선택)", placeholder="이 지문이 다루는 내용을 2~3문장으로 요약해주세요.", height=100)

            if st.button("지문 추가", use_container_width=True):
                if not new_title or not new_keywords:
                    st.warning("제목과 키워드는 필수입니다!")
                else:
                    new_passage = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "title": new_title,
                        "grade": new_grade,
                        "keywords": new_keywords,
                        "summary": new_summary
                    }
                    st.session_state.passages.append(new_passage)
                    save_passages(st.session_state.passages)
                    st.success(f"✅ '{new_title}' 추가 완료!")
                    st.rerun()

            st.markdown("---")
            if st.button("🚪 로그아웃", use_container_width=True):
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
                            st.markdown(f"""
                            <div class="passage-card">
                                <h4>{p['title']}</h4>
                                <span class="grade-badge">{p.get('grade','전체')}</span>
                                <span class="keywords">🏷 {p['keywords']}</span>
                                {"<br><small style='color:#888'>" + p['summary'][:60] + "...</small>" if p.get('summary') else ""}
                            </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                            if st.button("삭제", key=f"del_{p['id']}"):
                                st.session_state.passages = [x for x in st.session_state.passages if x['id'] != p['id']]
                                save_passages(st.session_state.passages)
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
