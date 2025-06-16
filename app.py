import streamlit as st
import openai
from openai import OpenAI
import os
from datetime import datetime
import json

# 페이지 설정
st.set_page_config(
    page_title="문학 학습 도우미",
    page_icon="📚",
    layout="wide"
)

# OpenAI API 키 설정
if "OPENAI_API_KEY" not in st.secrets:
    st.error("OpenAI API 키가 설정되지 않았습니다. Streamlit secrets에 OPENAI_API_KEY를 추가해주세요.")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# 대화 내역 제한 (메모리 관리)
MAX_MESSAGES = 20

# 작품 내용 및 워크시트 정보
DALGUROOT_CONTENT = """달러구트 꿈 백화점 주요 내용:
- 주인공 페니는 꿈을 파는 백화점에 신입사원으로 입사
- 1층부터 5층까지 각기 다른 특성을 가진 층들을 견학
- 각 층의 매니저들(웨더, 마이어스, 모그베리, 스피도)을 만남
- 5층은 매니저 없이 자유롭게 운영됨
- 페니는 어느 층에서 일할지 고민하며 계단을 내려감"""

YANGBAN_CONTENT = """양반전 주요 내용:
- 가난한 양반이 환곡을 갚지 못해 곤경에 처함
- 부자가 양반의 빚을 대신 갚고 양반 신분을 사려 함
- 군수가 양반 증서를 작성해 줌
- 첫 번째 증서: 양반의 까다로운 생활 예절
- 두 번째 증서: 양반의 횡포와 특권
- 부자가 "도둑놈이 되라 하는군요"라며 거부"""

WORKSHEET_CONCEPTS = """주요 학습 개념:
1. 소설의 5가지 특징: 허구성, 서사성, 개연성, 진실성, 산문성
2. 구성 단계: 발단-전개-위기-절정-결말
3. 인물 유형: 주동/반동, 평면적/입체적, 전형적/개성적
4. 갈등: 내적 갈등, 외적 갈등
5. 시점: 1인칭, 3인칭 관찰자, 전지적 작가
6. 비평 방법: 내재적 비평, 외재적 비평"""

# 시스템 프롬프트
SYSTEM_PROMPT = f"""당신은 고등학교 문학 수업의 학습 도우미입니다. 
학생들이 '달러구트 꿈 백화점'과 '양반전'을 분석하고 워크시트를 완성하는 것을 도와주세요.

중요한 규칙:
1. 절대 정답을 직접 알려주지 마세요
2. 학생이 스스로 생각할 수 있도록 유도하는 질문을 하세요
3. 개념을 이해하도록 돕는 비계(scaffolding)를 제공하세요
4. 작품의 특정 부분을 다시 읽어보도록 안내하세요
5. 학생의 답변에 대해 긍정적인 피드백을 주고, 더 깊이 생각하도록 격려하세요

작품 정보:
{DALGUROOT_CONTENT}

{YANGBAN_CONTENT}

{WORKSHEET_CONCEPTS}

대화 예시:
학생: "페니는 어떤 인물인가요?"
도우미: "좋은 질문이에요! 페니가 각 층을 돌아다니며 어떤 행동을 하는지 살펴볼까요? 특히 마지막에 계단에서 무엇을 하고 있나요? 그 행동이 페니의 성격에 대해 무엇을 알려주나요?"

학생: "양반전의 주제가 뭔가요?"
도우미: "주제를 찾는 좋은 방법이 있어요. 부자가 마지막에 왜 양반 되기를 포기했을까요? '도둑놈이 되라 하시는군요'라는 말의 의미를 생각해보세요. 이것이 양반 제도에 대해 무엇을 비판하고 있나요?"
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

달러구트 꿈 백화점과 양반전을 분석하거나 워크시트를 완성하는 데 어려움이 있나요? 
궁금한 점을 자유롭게 질문해주세요. 

단, 정답을 직접 알려드리지는 않아요. 대신 여러분이 스스로 답을 찾을 수 있도록 
힌트와 생각할 거리를 제공해드릴게요! 😊"""
    
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
                    max_tokens=500
                )
                
                ai_response = response.choices[0].message.content
                st.write(ai_response)
                
                # AI 응답 저장
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 페이지 하단 정보
st.markdown("---")
st.caption("💡 이 도우미는 학습을 돕기 위한 것으로, 정답을 직접 제공하지 않습니다. 스스로 생각하고 분석하는 과정이 진정한 학습입니다!")