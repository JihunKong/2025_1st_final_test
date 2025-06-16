import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="문학 학습 도우미",
    page_icon="📚",
    layout="wide"
)

# OpenAI 클라이언트 초기화 함수
def initialize_openai_client():
    """OpenAI 클라이언트를 안전하게 초기화"""
    try:
        # OpenAI 라이브러리 import 확인
        try:
            from openai import OpenAI
        except ImportError:
            st.error("OpenAI 라이브러리가 설치되지 않았습니다. requirements.txt를 확인하세요.")
            return None
        
        # API 키 확인
        api_key = None
        
        # 방법 1: Streamlit secrets 확인
        if "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
        # 방법 2: 환경변수 확인
        elif os.getenv("OPENAI_API_KEY"):
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            st.error("""
            OpenAI API 키가 설정되지 않았습니다.
            
            **Streamlit Cloud 설정 방법:**
            1. 앱 대시보드에서 Settings 클릭
            2. Secrets 탭 선택
            3. 다음 내용을 정확히 입력:
            ```
            OPENAI_API_KEY = "sk-여기에실제API키입력"
            ```
            4. Save 클릭 후 앱 재시작
            """)
            return None
        
        # API 키 유효성 검사
        if not api_key.startswith("sk-"):
            st.error("유효하지 않은 API 키입니다. 'sk-'로 시작하는 키여야 합니다.")
            return None
        
        # 환경변수 설정
        os.environ["OPENAI_API_KEY"] = api_key
        
        # 클라이언트 생성
        try:
            client = OpenAI(api_key=api_key)
            return client
        except Exception as e:
            # 환경변수만 사용하여 재시도
            try:
                client = OpenAI()
                return client
            except Exception as e2:
                st.error(f"OpenAI 클라이언트 생성 실패: {str(e2)}")
                return None
                
    except Exception as e:
        st.error(f"""
        OpenAI 초기화 중 오류: {str(e)}
        
        **확인사항:**
        1. requirements.txt에 'openai' 포함 확인
        2. API 키 형식 확인 (sk-로 시작)
        3. Streamlit Cloud에서 Secrets 설정 확인
        """)
        return None

# OpenAI 클라이언트 초기화
client = initialize_openai_client()
if not client:
    st.stop()

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# 대화 내역 제한 (메모리 관리)
MAX_MESSAGES = 20

# MD 파일 읽기 함수
@st.cache_data
def load_markdown_files():
    """MD 파일들을 읽어서 문자열로 반환"""
    content_dict = {}
    
    # 현재 스크립트의 디렉토리
    current_dir = Path(__file__).parent
    
    # 읽을 파일들
    files_to_read = {
        "dalguroot": "달러구트_지문.md",
        "yangban": "양반전.md",
        "worksheet": "문학이론적용_심화워크시트_교사용정답.md"
    }
    
    for key, filename in files_to_read.items():
        file_path = current_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content_dict[key] = f.read()
            except Exception as e:
                st.warning(f"{filename} 파일을 읽을 수 없습니다: {e}")
                content_dict[key] = ""
        else:
            st.warning(f"{filename} 파일이 없습니다.")
            content_dict[key] = ""
    
    return content_dict

# MD 파일 내용 로드
try:
    content_files = load_markdown_files()
    DALGUROOT_FULL_TEXT = content_files.get("dalguroot", "")
    YANGBAN_FULL_TEXT = content_files.get("yangban", "")
    WORKSHEET_FULL_TEXT = content_files.get("worksheet", "")
except Exception as e:
    st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
    DALGUROOT_FULL_TEXT = ""
    YANGBAN_FULL_TEXT = ""
    WORKSHEET_FULL_TEXT = ""

# 워크시트에서 주요 개념만 추출 (학생용 - 정답 제외)
WORKSHEET_CONCEPTS = """주요 학습 개념:
1. 소설의 5가지 특징: 허구성, 서사성, 개연성, 진실성, 산문성
2. 구성 단계: 발단-전개-위기-절정-결말
3. 인물 유형: 주동/반동, 평면적/입체적, 전형적/개성적
4. 갈등: 내적 갈등, 외적 갈등
5. 시점: 1인칭, 3인칭 관찰자, 전지적 작가
6. 비평 방법: 내재적 비평, 외재적 비평

워크시트 활동:
- 소설의 특징 적용하기
- 구성 단계와 유형 분석
- 인물 유형과 제시 방법 분석
- 갈등의 양상과 역할
- 배경의 종류와 기능
- 시점과 거리 분석
- 주제와 문체 분석
- 비평문 작성 실습"""

# 시스템 프롬프트
SYSTEM_PROMPT = f"""당신은 고등학교 문학 수업의 학습 도우미입니다. 
학생들이 '달러구트 꿈 백화점'과 '양반전'을 분석하고 워크시트를 완성하는 것을 도와주세요.

중요한 규칙:
1. 절대 정답을 직접 알려주지 마세요
2. 학생이 스스로 생각할 수 있도록 유도하는 질문을 하세요
3. 개념을 이해하도록 돕는 비계(scaffolding)를 제공하세요
4. 작품의 특정 부분을 다시 읽어보도록 안내하세요
5. 학생의 답변에 대해 긍정적인 피드백을 주고, 더 깊이 생각하도록 격려하세요
6. 필요한 경우 작품의 구체적인 문장을 인용하여 힌트를 제공하세요

=== 달러구트 꿈 백화점 전문 ===
{DALGUROOT_FULL_TEXT if DALGUROOT_FULL_TEXT else "(파일이 로드되지 않았습니다)"}

=== 양반전 전문 ===
{YANGBAN_FULL_TEXT if YANGBAN_FULL_TEXT else "(파일이 로드되지 않았습니다)"}

=== 학습 개념 및 워크시트 ===
{WORKSHEET_CONCEPTS}

참고: 워크시트의 정답은 제공하지 않습니다. 학생이 스스로 생각하도록 유도하세요.

대화 예시:
학생: "페니는 어떤 인물인가요?"
도우미: "좋은 질문이에요! 페니가 각 층을 돌아다니며 어떤 행동을 하는지 살펴볼까요? 특히 '그녀는 일부러 엘리베이터를 이용하지 않고 계단으로 천천히 내려갔다'는 부분에서 페니의 성격을 엿볼 수 있어요. 이 행동이 의미하는 것은 무엇일까요?"

토큰 정보:
- 달러구트: 약 7,000 토큰
- 양반전: 약 3,000 토큰  
- 워크시트: 약 3,000 토큰
- 총 컨텍스트: 약 15,000 토큰
- gpt-4o-mini 컨텍스트 윈도우: 128,000 토큰 (충분함)
"""

# CSS 스타일
st.markdown("""
<style>
    .stApp {
        background-color: #f5f5f5;
    }
    .main-header {
        background-color: #1e3d59;
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .chat-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .hint-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    .concept-box {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 메인 헤더
st.markdown("""
<div class="main-header">
    <h1>📚 문학 학습 도우미</h1>
    <p>달러구트 꿈 백화점 & 양반전 분석하기</p>
</div>
""", unsafe_allow_html=True)

# 파일 로드 상태 표시
with st.expander("📄 파일 로드 상태"):
    col1, col2, col3 = st.columns(3)
    with col1:
        if DALGUROOT_FULL_TEXT:
            st.success(f"✅ 달러구트_지문.md ({len(DALGUROOT_FULL_TEXT):,}자)")
        else:
            st.error("❌ 달러구트_지문.md 실패")
    with col2:
        if YANGBAN_FULL_TEXT:
            st.success(f"✅ 양반전.md ({len(YANGBAN_FULL_TEXT):,}자)")
        else:
            st.error("❌ 양반전.md 실패")
    with col3:
        if WORKSHEET_FULL_TEXT:
            st.success(f"✅ 워크시트.md ({len(WORKSHEET_FULL_TEXT):,}자)")
        else:
            st.error("❌ 워크시트.md 실패")

# 사이드바
with st.sidebar:
    st.header("학습 가이드")
    
    st.subheader("📖 학습 작품")
    st.write("- 달러구트 꿈 백화점 (이미예)")
    st.write("- 양반전 (박지원)")
    
    st.subheader("🎯 학습 목표")
    st.write("- 서사 갈래 이론 이해")
    st.write("- 작품 분석 능력 향상")
    st.write("- 비평문 작성 연습")
    
    st.subheader("💡 학습 팁")
    st.info("""
    1. 구체적인 질문을 해보세요
    2. 작품의 특정 장면을 언급하며 질문하세요
    3. 개념이 헷갈리면 설명을 요청하세요
    4. 스스로 생각한 답을 먼저 말해보세요
    """)
    
    st.subheader("🔍 작품 내 검색")
    search_term = st.text_input("검색어 입력")
    if search_term:
        st.write("검색 결과:")
        if search_term in DALGUROOT_FULL_TEXT:
            st.write("- 달러구트에서 발견됨")
        if search_term in YANGBAN_FULL_TEXT:
            st.write("- 양반전에서 발견됨")
    
    if st.button("대화 초기화"):
        st.session_state.messages = []
        st.session_state.conversation_started = False
        st.rerun()

# 메인 컨텐츠
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 주요 학습 개념")
    
    with st.expander("소설의 특징"):
        st.write("""
        - **허구성**: 작가의 상상력으로 창조된 세계
        - **서사성**: 인물, 사건, 배경의 시간적 전개
        - **개연성**: 현실에서 있을 법한 이야기
        - **진실성**: 삶의 의미와 가치 전달
        - **산문성**: 서술, 대화, 묘사의 조화
        """)
    
    with st.expander("인물 분석"):
        st.write("""
        - **평면적 vs 입체적**: 변화 여부
        - **전형적 vs 개성적**: 보편성 vs 독특함
        - **주동 vs 반동**: 사건을 이끄는 역할
        """)
    
    with st.expander("비평 방법"):
        st.write("""
        - **내재적 비평**: 작품 내부의 구조, 형식 분석
        - **외재적 비평**: 시대적 배경, 작가 사상 고려
        """)

with col2:
    st.subheader("💬 질문하기")
    
    # 예시 질문 버튼
    example_questions = [
        "페니는 왜 계단으로 내려갔을까요?",
        "양반전에서 풍자하는 것은 무엇인가요?",
        "내적 갈등과 외적 갈등의 차이는?",
        "3인칭 관찰자 시점의 특징은?"
    ]
    
    st.write("예시 질문:")
    cols = st.columns(2)
    for i, question in enumerate(example_questions):
        if cols[i % 2].button(question, key=f"example_{i}"):
            st.session_state.messages.append({"role": "user", "content": question})
            st.session_state.conversation_started = True

# 채팅 인터페이스
st.markdown("---")
st.subheader("🤖 AI 학습 도우미와 대화하기")

# 대화 시작 메시지
if not st.session_state.conversation_started:
    welcome_message = """안녕하세요! 저는 여러분의 문학 학습을 도와드리는 AI 도우미예요. 

달러구트 꿈 백화점과 양반전의 전체 텍스트, 그리고 워크시트 내용을 읽고 있어서, 
작품의 구체적인 부분을 인용하며 도움을 드릴 수 있어요.

궁금한 점을 자유롭게 질문해주세요. 예를 들어:
- "페니가 2층에서 만난 매니저의 성격은?"
- "양반 증서의 첫 번째와 두 번째의 차이점은?"
- "작품에서 '아무한테나 팔면 꿈값을 못 받아'라는 말의 의미는?"

정답을 직접 알려드리지는 않지만, 스스로 답을 찾을 수 있도록 도와드릴게요! 😊"""
    
    st.info(welcome_message)

# 채팅 컨테이너
chat_container = st.container()

with chat_container:
    # 대화 내역 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# 사용자 입력
user_input = st.chat_input("질문을 입력하세요...")

if user_input:
    st.session_state.conversation_started = True
    
    # 대화 내역이 너무 길면 오래된 것부터 삭제
    if len(st.session_state.messages) > MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-(MAX_MESSAGES-2):]
    
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.write(user_input)
    
    # AI 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                # 대화 내역 준비
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ] + st.session_state.messages
                
                # OpenAI API 호출
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800
                )
                
                ai_response = response.choices[0].message.content
                st.write(ai_response)
                
                # AI 응답 저장
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 페이지 하단 정보
st.markdown("---")
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.caption("💡 AI가 작품 전문을 읽고 있어 구체적인 인용이 가능합니다")

with col2:
    st.caption("📚 정답을 직접 제공하지 않고 스스로 생각하도록 도와줍니다")

with col3:
    loaded_texts = [DALGUROOT_FULL_TEXT, YANGBAN_FULL_TEXT, WORKSHEET_FULL_TEXT]
    total_chars = sum(len(text) for text in loaded_texts if text)
    if total_chars > 0:
        st.caption(f"📊 총 로드된 텍스트: {total_chars:,}자")
