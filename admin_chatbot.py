"""
챗봇 관리 시스템 메인 애플리케이션 (Container 기반)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
import subprocess
import sys
import webbrowser
import threading
import socket

# 로컬 모듈 임포트
from azure_blob_utils import (
    azure_manager,
    upload_files_to_azure,
    list_azure_files,
    get_azure_file_info,
    is_azure_configured,
    get_azure_config_status
)
from database_utils import (
    chatbot_db,
    add_chatbot,
    get_all_chatbots,
    update_chatbot_index,
    update_chatbot_container,
    delete_chatbot
)
# 새로운 파일 업로드 모듈 임포트
from azure_blob_utils import display_file_upload_popup

# 페이지 설정
st.set_page_config(
    page_title="챗봇 관리 시스템",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_file_size(size_bytes):
    """파일 크기를 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def create_index_for_container(container_name):
    """특정 컨테이너에 대한 인덱스 생성"""
    try:
        # 인덱스명 생성 (컨테이너명-index)
        index_name = f"{container_name}-index"
        
        # create_index_claud.py 실행
        env = os.environ.copy()
        env['CONTAINER_NAME'] = container_name
        env['INDEX_NAME'] = index_name
        
        # Python 스크립트 실행
        cmd = [sys.executable, "create_index_claud.py"]
        
        # 프로그레스 바 표시
        with st.spinner(f"📊 '{container_name}' 컨테이너에 대한 인덱스를 생성하고 있습니다..."):
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
        
        if result.returncode == 0:
            st.success(f"✅ 인덱스 '{index_name}'가 성공적으로 생성되었습니다!")
            if result.stdout:
                with st.expander("📋 인덱스 생성 로그"):
                    st.code(result.stdout)
            return index_name
        else:
            st.error(f"❌ 인덱스 생성 실패")
            if result.stderr:
                with st.expander("❌ 에러 로그"):
                    st.code(result.stderr)
            return None
            
    except Exception as e:
        st.error(f"❌ 인덱스 생성 중 오류 발생: {str(e)}")
        return None

def display_environment_status():
    """환경 설정 상태를 사이드바에 표시"""
    st.sidebar.header("🔧 환경 설정")
    
    # Azure Storage 설정 확인
    configured, missing = get_azure_config_status()
    
    if configured:
        st.sidebar.success("✅ Azure Storage 설정 완료")
    else:
        st.sidebar.error("❌ Azure Storage 설정 필요")
        st.sidebar.write("**누락된 환경변수:**")
        for item in missing:
            st.sidebar.write(f"- {item}")
        
        with st.sidebar.expander("💡 설정 방법", expanded=False):
            st.write("""
            `.env` 파일을 생성하고 다음 내용을 추가하세요:
            
            ```
            AZURE_STORAGE_CONNECTION_STRING=your_connection_string
            AZURE_SEARCH_SERVICE_NAME=your_search_service_name
            AZURE_SEARCH_SERVICE_ADMIN_KEY=your_search_admin_key
            ```
            
            각 챗봇은 별도의 컨테이너를 사용합니다.
            """)
    
    # 데이터베이스 정보
    st.sidebar.header("📊 데이터베이스 정보")
    total_chatbots = chatbot_db.get_chatbot_count()
    st.sidebar.write(f"등록된 챗봇: **{total_chatbots}개**")
    st.sidebar.write(f"DB 파일: `{chatbot_db.db_path}`")
    
    # 실행 중인 챗봇 정보 (세션 상태 기반)
    st.sidebar.header("🚀 실행 정보")
    if 'running_chatbots' in st.session_state:
        running_count = len(st.session_state.running_chatbots)
        st.sidebar.write(f"실행 중인 챗봇: **{running_count}개**")
        for chatbot in st.session_state.running_chatbots:
            st.sidebar.write(f"- {chatbot}")
    else:
        st.sidebar.write("실행 중인 챗봇: **0개**")

def display_chatbot_management():
    """챗봇 관리 메인 페이지 - 탭 기반으로 변경"""
    st.title("🤖 챗봇 관리 시스템")
    
    # 환경 설정 상태 표시
    display_environment_status()
    
    # 실행 중인 챗봇이 있으면 추가 탭 생성
    active_chatbot = st.session_state.get('active_chatbot', None)
    
    if active_chatbot:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 챗봇 목록", 
            "➕ 챗봇 등록", 
            "📦 컨테이너 관리", 
            f"💬 {active_chatbot['name']}"
        ])
        
        with tab4:
            # 챗봇 종료 버튼
            col1, col2 = st.columns([5, 1])
            with col2:
                if st.button("❌ 챗봇 종료", key="close_chatbot"):
                    del st.session_state['active_chatbot']
                    st.rerun()
            
            # 챗봇 UI를 여기에 임베드
            run_embedded_chatbot(active_chatbot)
    else:
        tab1, tab2, tab3 = st.tabs(["📋 챗봇 목록", "➕ 챗봇 등록", "📦 컨테이너 관리"])
    
    with tab1:
        display_chatbot_list()
    
    with tab2:
        display_chatbot_registration()
        
    with tab3:
        display_container_management()

def display_chatbot_list():
    """챗봇 목록 표시 및 관리"""
    st.header("📋 등록된 챗봇 목록")
    
    # 실행 중인 챗봇 목록 초기화
    if 'running_chatbots' not in st.session_state:
        st.session_state.running_chatbots = []
    
    # 챗봇 목록 조회
    chatbots = get_all_chatbots()
    
    if not chatbots:
        st.info("📝 등록된 챗봇이 없습니다. '챗봇 등록' 탭에서 새 챗봇을 추가하세요.")
        return
    
    # 데이터프레임 생성
    df = pd.DataFrame(chatbots)
    
    # 각 챗봇에 대한 액션 버튼과 정보 표시
    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.2, 1.2, 1.2, 1.2, 1])
            
            with col1:
                st.write(f"**🤖 {row['chatbotname']}**")
                st.write(f"📦 컨테이너: {row['containername'] or '미설정'}")
                if row['index_name']:
                    st.write(f"📊 인덱스: {row['index_name']}")
                st.write(f"📅 등록일: {row['created_at']}")
            
            with col2:
                if row['index_status']:
                    st.success("✅ 인덱스 완료")
                else:
                    st.warning("⏳ 인덱스 대기중")
            
            with col3:
                # 파일 업로드 버튼
                if st.button(f"📁 파일 업로드", key=f"upload_{row['id']}"):
                    st.session_state[f"show_upload_{row['id']}"] = True
            
            with col4:
                # 인덱스 업데이트 버튼
                if st.button(f"🔄 인덱스 갱신", key=f"index_{row['id']}"):
                    container_name = row['containername'] or row['chatbotname']
                    
                    if not container_name:
                        st.error("❌ 컨테이너명이 설정되지 않았습니다.")
                        continue
                    
                    # 인덱스 생성
                    created_index_name = create_index_for_container(container_name)
                    
                    if created_index_name:
                        # DB에 인덱스 상태와 이름 업데이트
                        success = update_chatbot_index(
                            row['id'], 
                            index_status=True, 
                            index_name=created_index_name
                        )
                        
                        if success:
                            st.success(f"✅ 인덱스가 성공적으로 갱신되었습니다!")
                            st.success(f"📊 생성된 인덱스: {created_index_name}")
                            st.rerun()
                        else:
                            st.error("❌ DB 업데이트 실패")
                    else:
                        # 인덱스 생성 실패 시 상태를 대기중으로 설정
                        update_chatbot_index(row['id'], index_status=False)
            
            with col5:
                # 챗봇 실행 버튼 - 탭 방식
                chatbot_name = row['chatbotname']
                disabled = not row['index_status']
                
                if st.button(
                    f"🚀 실행", 
                    key=f"run_{row['id']}",
                    disabled=disabled,
                    help="인덱스가 완료된 후 실행 가능합니다" if disabled else f"{chatbot_name} 챗봇을 실행합니다"
                ):
                    # 활성 챗봇으로 설정
                    st.session_state['active_chatbot'] = {
                        'name': row['chatbotname'],
                        'container': row['containername'],
                        'index': row['index_name']                    
                    }
                    
                    st.success(f"✅ {chatbot_name} 챗봇이 활성화되었습니다!")
                    st.rerun()
            
            with col6:
                # 삭제 버튼
                if st.button(
                    "🗑️", 
                    key=f"delete_{row['id']}",
                    help=f"{row['chatbotname']} 삭제",
                    type="secondary"
                ):
                    st.session_state[f"confirm_delete_{row['id']}"] = True

            # 삭제 확인 대화상자
            if st.session_state.get(f"confirm_delete_{row['id']}", False):
                st.warning(f"⚠️ **'{row['chatbotname']}'** 챗봇을 정말 삭제하시겠습니까?")
                
                col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 2])
                
                with col_confirm1:
                    if st.button("✅ 삭제", key=f"confirm_yes_{row['id']}", type="primary"):
                        success = delete_chatbot(row['id'])
                        if success:
                            st.success(f"✅ '{row['chatbotname']}' 챗봇이 삭제되었습니다!")
                            # 활성 챗봇이 삭제된 챗봇이면 제거
                            if (st.session_state.get('active_chatbot') and 
                                st.session_state['active_chatbot']['name'] == row['chatbotname']):
                                del st.session_state['active_chatbot']
                            st.rerun()
                        else:
                            st.error("❌ 삭제 실패")
                
                with col_confirm2:
                    if st.button("❌ 취소", key=f"confirm_no_{row['id']}"):
                        st.session_state[f"confirm_delete_{row['id']}"] = False
                        st.rerun()
        
        # 파일 업로드 팝업 표시
        if st.session_state.get(f"show_upload_{row['id']}", False):
            st.markdown("---")
            
            # 닫기 버튼
            col_close1, col_close2 = st.columns([6, 1])
            with col_close2:
                if st.button("❌ 닫기", key=f"close_upload_{row['id']}"):
                    st.session_state[f"show_upload_{row['id']}"] = False
                    st.rerun()
            
            # 파일 업로드 팝업 표시
            with st.container():
                upload_success = display_file_upload_popup(
                    chatbot_name=row['chatbotname'],
                    container_name=row['containername']
                )
                
                # 업로드 성공 시 컨테이너명 업데이트 및 팝업 닫기
                if upload_success:
                    # 컨테이너명이 변경된 경우 DB 업데이트
                    current_container = st.session_state.get(f"container_input_{row['id']}", row['containername'])
                    if current_container and current_container != row['containername']:
                        update_chatbot_container(row['id'], current_container)
                    
                    # 인덱스 상태를 대기중으로 변경 (새 파일이 업로드되었으므로)
                    update_chatbot_index(row['id'], index_status=False, index_name=None)
                    
                    st.balloons()
                    st.success("🎉 파일 업로드가 완료되었습니다! 인덱스를 갱신해주세요.")
                    
                    # 몇 초 후 팝업 자동 닫기
                    import time
                    time.sleep(2)
                    st.session_state[f"show_upload_{row['id']}"] = False
                    st.rerun()
            
            st.markdown("---")

def run_embedded_chatbot(chatbot_info):
    """챗봇을 현재 페이지에 임베드해서 실행"""
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from openai import AzureOpenAI
    import time
    
    # 환경 변수 설정
    index_name = chatbot_info['index']
    container_name = chatbot_info['container']
    
    st.header(f"💬 {chatbot_info['name']} 챗봇")
    
    # Azure 클라이언트 초기화
    try:
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
    except Exception as e:
        st.error(f"Azure 클라이언트 초기화 실패: {e}")
        return
    
    # 문서 상태 확인
    doc_count = get_document_count_embedded(search_client)
    
    if doc_count == 0:
        st.warning("⚠️ 인덱스에 문서가 없습니다. 먼저 인덱스를 갱신해주세요.")
        return
    
    st.info(f"📚 현재 {doc_count}개의 문서가 검색 가능합니다.")
    
    # 세션 상태 초기화 (챗봇별로 분리)
    chat_key = f"messages_{chatbot_info['name']}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    
    # 채팅 기록 표시
    for message in st.session_state[chat_key]:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        elif message["role"] == "assistant":
            with st.chat_message("assistant"):
                st.write(message["content"])
                if "sources" in message and message["sources"]:
                    st.caption(f"📋 참고 문서: {', '.join(message['sources'])}")
    
    # 입력 영역
    if prompt := st.chat_input(f"{chatbot_info['name']}에게 질문하세요..."):
        # 사용자 메시지 추가
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하고 있습니다..."):
                answer, sources = search_and_answer_embedded(search_client, openai_client, prompt)
                st.write(answer)
                if sources:
                    st.caption(f"📋 참고 문서: {', '.join(sources)}")
        
        # AI 메시지 추가
        st.session_state[chat_key].append({
            "role": "assistant", 
            "content": answer,
            "sources": sources
        })
    
    # 채팅 기록 클리어 버튼
    if st.session_state[chat_key]:
        if st.button("🗑️ 채팅 기록 삭제", key=f"clear_{chatbot_info['name']}"):
            st.session_state[chat_key] = []
            st.rerun()

def get_document_count_embedded(search_client):
    """인덱스의 문서 수 확인"""
    try:
        results = search_client.search(search_text="*", top=1, include_total_count=True)
        return results.get_count()
    except Exception as e:
        st.error(f"문서 수 확인 실패: {e}")
        return 0

def get_best_content_embedded(doc):
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

def search_and_answer_embedded(search_client, openai_client, question):
    """질문에 대해 검색하고 GPT로 답변 생성"""
    try:
        # Azure Search로 관련 문서 검색
        results = search_client.search(
            search_text=question,
            top=3,
            search_mode="any"
        )
        
        # 검색된 문서의 내용 수집
        contexts = []
        sources = []
        
        for doc in results:
            text, source = get_best_content_embedded(doc)
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

def display_chatbot_registration():
    """새 챗봇 등록"""
    st.header("➕ 새 챗봇 등록")
    
    with st.form("chatbot_registration"):
        chatbot_name = st.text_input(
            "🤖 챗봇 이름",
            placeholder="예: 고객지원봇, 제품안내봇 등",
            help="등록할 챗봇의 이름을 입력하세요."
        )
        
        container_name = st.text_input(
            "📦 컨테이너명 (선택사항)",
            placeholder="미입력 시 챗봇 이름과 동일하게 설정됩니다.",
            help="Azure Blob Storage에서 사용할 컨테이너명입니다. 컨테이너는 챗봇별로 독립적으로 관리됩니다."
        )
        
        description = st.text_area(
            "📝 설명 (선택사항)",
            placeholder="챗봇에 대한 간단한 설명을 입력하세요.",
            help="챗봇의 용도나 특징을 설명해주세요."
        )
        
        submitted = st.form_submit_button("🚀 챗봇 등록", type="primary")
        
        if submitted:
            if not chatbot_name.strip():
                st.error("❌ 챗봇 이름을 입력해주세요.")
            else:
                # 컨테이너명이 없으면 챗봇 이름 사용 (소문자로 변환)
                final_container_name = (container_name.strip() or chatbot_name.strip()).lower().replace(" ", "-")
                
                success = add_chatbot(
                    chatbot_name=chatbot_name.strip(),
                    container_name=final_container_name,
                    description=description.strip()
                )
                
                if success:
                    st.success(f"✅ '{chatbot_name}' 챗봇이 성공적으로 등록되었습니다!")
                    st.info(f"📦 컨테이너: {final_container_name}")
                    st.balloons()
                    
                    # 폼 초기화를 위한 페이지 새로고침
                    st.rerun()
                else:
                    st.error("❌ 챗봇 등록 중 오류가 발생했습니다.")

def display_container_management():
    """컨테이너 관리 페이지"""
    st.header("📦 컨테이너 관리")
    
    # Azure 설정 확인
    if not is_azure_configured():
        st.warning("⚠️ Azure Storage가 설정되지 않았습니다.")
        st.info("💡 사이드바의 환경 설정을 확인하세요.")
        return
    
    # 등록된 챗봇들의 컨테이너 목록 표시
    chatbots = get_all_chatbots()
    
    if not chatbots:
        st.info("📝 등록된 챗봇이 없습니다.")
        return
    
    st.write(f"**📊 총 {len(chatbots)}개의 챗봇 컨테이너가 있습니다.**")
    
    # 컨테이너별 파일 정보 표시
    for chatbot in chatbots:
        container_name = chatbot['containername']
        if not container_name:
            continue
        
        with st.expander(f"📦 {container_name} ({chatbot['chatbotname']})", expanded=False):
            try:
                # 해당 컨테이너의 파일 목록 조회
                files = list_azure_files(container_name=container_name)
                
                if files:
                    st.write(f"**파일 개수:** {len(files)}개")
                    
                    # 파일 목록을 데이터프레임으로 표시
                    file_data = []
                    for file_info in files:
                        file_data.append({
                            '파일명': file_info['name'],
                            '크기': format_file_size(file_info['size']),
                            '수정일': file_info['last_modified'].strftime('%Y-%m-%d %H:%M:%S') if file_info['last_modified'] else 'N/A'
                        })
                    
                    df_files = pd.DataFrame(file_data)
                    st.dataframe(df_files, use_container_width=True, hide_index=True)
                else:
                    st.info("📂 이 컨테이너에는 파일이 없습니다.")
                    
            except Exception as e:
                st.error(f"❌ 컨테이너 '{container_name}' 정보를 불러오는 중 오류가 발생했습니다: {str(e)}")

# 메인 실행부
def main():
    """메인 애플리케이션 실행"""
    
    # 세션 상태 초기화
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
    
    # 메인 페이지 표시
    display_chatbot_management()

if __name__ == "__main__":
    main()