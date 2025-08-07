import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import time

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="AI 문서 검색 챗봇",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS 스타일링 - 팝업 형태의 챗봇 UI
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .chat-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
    }
    
    .chat-header {
        text-align: center;
        color: white;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .user-message {
        background: #4CAF50;
        color: white;
        padding: 12px 18px;
        border-radius: 18px;
        margin: 10px 0;
        margin-left: 20%;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .bot-message {
        background: #2196F3;
        color: white;
        padding: 12px 18px;
        border-radius: 18px;
        margin: 10px 0;
        margin-right: 20%;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .system-message {
        background: #FF9800;
        color: white;
        padding: 8px 12px;
        border-radius: 12px;
        margin: 5px 0;
        font-size: 14px;
        text-align: center;
    }
    
    .document-info {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
        backdrop-filter: blur(5px);
    }
    
    .stTextInput > div > div > input {
        border-radius: 20px;
        border: 2px solid #667eea;
        padding: 10px 15px;
    }
    
    .stButton > button {
        border-radius: 20px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }
    
    .floating-chat {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
    }
</style>
""", unsafe_allow_html=True)

# Azure 클라이언트 초기화
@st.cache_resource
def initialize_clients(index_name):
    
    search_client = SearchClient(
        endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE_NAME')}.search.windows.net",
        index_name=index_name,
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"))
    )
    
    openai_client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version="2023-12-01-preview"
    )
    
    return search_client, openai_client

def get_document_count(search_client):
    """인덱스의 문서 수 확인"""
    try:
        results = search_client.search(search_text="*", top=1, include_total_count=True)
        return results.get_count()
    except Exception as e:
        st.error(f"문서 수 확인 실패: {e}")
        return 0

def get_best_content(doc):
    """문서에서 가장 좋은 텍스트 내용을 반환"""
    content = doc.get("content", "").strip()
    ocr_text = doc.get("ocr_text", "").strip()
    filename = doc.get("metadata_storage_name", "Unknown")
    
    if ocr_text:
        return ocr_text, f"{filename} (OCR)"
    elif content:
        return content, f"{filename} (원본)"
    else:
        return "", filename

def search_and_answer(search_client, openai_client, question):
    """질문에 대해 검색하고 GPT로 답변 생성"""
    try:
        # Azure Search로 관련 문서 검색
        with st.spinner("🔍 관련 문서를 검색하고 있습니다..."):
            results = search_client.search(
                search_text=question,
                top=3,
                search_mode="any"
            )
            
            # 검색된 문서의 내용 수집
            contexts = []
            sources = []
            
            for doc in results:
                text, source = get_best_content(doc)
                if text:
                    contexts.append(text)
                    sources.append(source)
            
            if not contexts:
                return "❌ 질문과 관련된 문서를 찾을 수 없습니다.", []
            
            # 모든 컨텍스트를 합치되, 너무 길면 자르기
            combined_context = "\n\n".join(contexts)
            if len(combined_context) > 8000:
                combined_context = combined_context[:8000] + "...[내용 일부 생략]"
        
        # GPT에게 질문과 컨텍스트 전달
        with st.spinner("🤖 AI가 답변을 생성하고 있습니다..."):
            response = openai_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                messages=[
                    {
                        "role": "system", 
                        "content": """당신은 제공된 문서를 바탕으로 정확하고 도움이 되는 답변을 제공하는 AI 어시스턴트입니다.

규칙:
1. 제공된 문서의 내용만을 바탕으로 답변하세요
2. 문서에 없는 내용은 추측하지 마세요  
3. 답변할 수 없다면 솔직히 말하세요
4. 가능한 한 구체적이고 정확한 정보를 제공하세요
5. 한국어로 자연스럽게 답변하세요
6. 답변의 근거가 되는 부분이 있다면 언급해주세요"""
                    },
                    {
                        "role": "user", 
                        "content": f"다음 문서들을 바탕으로 질문에 답변해주세요.\n\n문서 내용:\n{combined_context}\n\n질문: {question}"
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            answer = response.choices[0].message.content
            return answer, sources
            
    except Exception as e:
        return f"❌ 검색 또는 답변 생성 실패: {e}", []

def main():

    index_name = os.getenv('INDEX_NAME', 'azureblob-index')
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_active" not in st.session_state:
        st.session_state.chat_active = False
    if "processing" not in st.session_state:
        st.session_state.processing = False
    
    # 클라이언트 초기화
    try:
        search_client, openai_client = initialize_clients(index_name)
    except Exception as e:
        st.error(f"Azure 클라이언트 초기화 실패: {e}")
        st.stop()
    
    # 메인 컨테이너
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">🤖 AI 문서 검색 챗봇</div>', unsafe_allow_html=True)
    
    # 문서 상태 확인
    doc_count = get_document_count(search_client)
    
    if doc_count == 0:
        st.markdown("""
        <div class="system-message">
            ⚠️ 인덱스에 문서가 없습니다. 먼저 indexer를 실행해주세요.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # 문서 정보 표시
    st.markdown(f"""
    <div class="document-info">
        📚 현재 {doc_count}개의 문서가 검색 가능합니다.
        <br>💡 궁금한 것이 있으면 아래에 질문해보세요!
    </div>
    """, unsafe_allow_html=True)
    
    # 채팅 기록 표시
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="user-message">👤 {message["content"]}</div>', 
                          unsafe_allow_html=True)
            elif message["role"] == "assistant":
                st.markdown(f'<div class="bot-message">🤖 {message["content"]}</div>', 
                          unsafe_allow_html=True)
                if "sources" in message and message["sources"]:
                    sources_text = "📋 **참고 문서:** " + ", ".join(message["sources"])
                    st.markdown(f'<div class="system-message">{sources_text}</div>', 
                              unsafe_allow_html=True)
    
    # 입력 영역
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "질문을 입력하세요...", 
                placeholder="예: 문서에서 중요한 내용은 무엇인가요?",
                label_visibility="collapsed",
                disabled=st.session_state.processing
            )
        
        with col2:
            send_button = st.form_submit_button(
                "전송 📤", 
                disabled=st.session_state.processing
            )
    
    # 메시지 처리
    if send_button and user_input.strip() and not st.session_state.processing:
        st.session_state.processing = True
        
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # AI 응답 생성
        answer, sources = search_and_answer(search_client, openai_client, user_input)
        
        # AI 메시지 추가
        st.session_state.messages.append({
            "role": "assistant", 
            "content": answer,
            "sources": sources
        })
        
        st.session_state.processing = False
        st.rerun()
    
    # 채팅 기록 클리어 버튼
    if st.session_state.messages:
        if st.button("🗑️ 채팅 기록 삭제", key="clear_button"):
            st.session_state.messages = []
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 사이드바 - 추가 기능
    with st.sidebar:
        st.header("📋 시스템 정보")
        st.info(f"📚 검색 가능한 문서: {doc_count}개")
        
        if st.button("🔄 문서 상태 새로고침"):
            st.cache_resource.clear()
            st.rerun()
        
        st.header("💡 사용 팁")
        st.markdown("""
        - 구체적인 질문일수록 정확한 답변을 받을 수 있습니다
        - 문서에 없는 내용은 답변드릴 수 없습니다
        - 여러 문서에서 관련 정보를 찾아 종합적으로 답변합니다
        """)

if __name__ == "__main__":
    main()