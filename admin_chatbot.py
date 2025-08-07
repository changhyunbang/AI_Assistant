"""
챗봇 관리 시스템 메인 애플리케이션
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
    update_chatbot_folder
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

def find_available_port(start_port=8502):
    """사용 가능한 포트 찾기"""
    port = start_port
    while port < start_port + 100:  # 최대 100개 포트 확인
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return None

def launch_chatbot_popup(chatbot_name, folder_name, index_name):
    """챗봇 팝업 실행"""
    try:
        # 사용 가능한 포트 찾기
        port = find_available_port()
        if not port:
            st.error("사용 가능한 포트를 찾을 수 없습니다.")
            return
        
        # 환경 변수 설정 (필요한 경우)
        env = os.environ.copy()
        env['CHATBOT_NAME'] = chatbot_name
        env['FOLDER_NAME'] = folder_name or chatbot_name
        env['INDEX_NAME'] = index_name or chatbot_name
        
        # streamlit 명령어 구성
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "chatbot_popup.py",
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--theme.base", "light"
        ]
        
        # 백그라운드에서 프로세스 실행
        def run_chatbot():
            try:
                subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                # 잠시 대기 후 브라우저에서 열기
                import time
                time.sleep(2)
                webbrowser.open(f'http://localhost:{port}')
            except Exception as e:
                print(f"챗봇 실행 오류: {e}")
        
        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=run_chatbot, daemon=True)
        thread.start()
        
        # 성공 메시지 표시
        st.success(f"🚀 '{chatbot_name}' 챗봇이 새 창에서 실행됩니다! (포트: {port})")
        st.info("💡 챗봇이 열리지 않으면 브라우저에서 팝업을 허용해주세요.")
        
    except Exception as e:
        st.error(f"챗봇 실행 중 오류 발생: {str(e)}")

def create_index_for_folder(folder_name):
    """특정 폴더에 대한 인덱스 생성"""
    try:
        # 인덱스명 생성 (폴더명-index)
        index_name = f"{folder_name}-index"
        
        # create_index_claud.py 실행
        env = os.environ.copy()
        env['FOLDER_NAME'] = folder_name
        env['INDEX_NAME'] = index_name
        
        # Python 스크립트 실행
        cmd = [sys.executable, "create_index_claud.py"]
        
        # 프로그레스 바 표시
        with st.spinner(f"📊 '{folder_name}' 폴더에 대한 인덱스를 생성하고 있습니다..."):
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
        if azure_manager.container_name:
            st.sidebar.write(f"📦 컨테이너: {azure_manager.container_name}")
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
            AZURE_STORAGE_CONTAINER_NAME=your_container_name
            AZURE_SEARCH_SERVICE_NAME=your_search_service_name
            AZURE_SEARCH_SERVICE_ADMIN_KEY=your_search_admin_key
            ```
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
    """챗봇 관리 메인 페이지"""
    st.title("🤖 챗봇 관리 시스템")
    
    # 환경 설정 상태 표시
    display_environment_status()
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📋 챗봇 목록", "➕ 챗봇 등록", "📁 파일 관리"])
    
    with tab1:
        display_chatbot_list()
    
    with tab2:
        display_chatbot_registration()
        
    with tab3:
        display_file_management()

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
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
            
            with col1:
                st.write(f"**🤖 {row['chatbotname']}**")
                st.write(f"📂 폴더: {row['foldername'] or '미설정'}")
                if row['index_name']:
                    st.write(f"📊 인덱스: {row['index_name']}")
                st.write(f"📅 등록일: {row['created_at']}")
            
            with col2:
                if row['index_status']:
                    st.success("✅ 인덱스 완료")
                else:
                    st.warning("⏳ 인덱스 대기중")
            
            with col3:
                # 파일 등록 버튼
                if st.button(f"📁 파일 등록", key=f"upload_{row['id']}"):
                    st.session_state[f"show_upload_{row['id']}"] = True
            
            with col4:
                # 인덱스 업데이트 버튼
                if st.button(f"🔄 인덱스 갱신", key=f"index_{row['id']}"):
                    folder_name = row['foldername'] or row['chatbotname']
                    
                    if not folder_name:
                        st.error("❌ 폴더명이 설정되지 않았습니다.")
                        continue
                    
                    # 인덱스 생성
                    created_index_name = create_index_for_folder(folder_name)
                    
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
                # 챗봇 실행 버튼
                chatbot_name = row['chatbotname']
                disabled = not row['index_status']  # 인덱스가 완료되지 않으면 비활성화
                
                if st.button(
                    f"🚀 실행", 
                    key=f"run_{row['id']}",
                    disabled=disabled,
                    help="인덱스가 완료된 후 실행 가능합니다" if disabled else f"{chatbot_name} 챗봇을 새 창에서 실행합니다"
                ):
                    # 실행 중인 챗봇 목록에 추가
                    if chatbot_name not in st.session_state.running_chatbots:
                        st.session_state.running_chatbots.append(chatbot_name)
                    
                    # 챗봇 팝업 실행
                    launch_chatbot_popup(chatbot_name, row['foldername'], row['index_name'])
        
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
                    folder_name=row['foldername']
                )
                
                # 업로드 성공 시 폴더명 업데이트 및 팝업 닫기
                if upload_success:
                    # 폴더명이 변경된 경우 DB 업데이트
                    current_folder = st.session_state.get(f"folder_input_{row['id']}", row['foldername'])
                    if current_folder and current_folder != row['foldername']:
                        update_chatbot_folder(row['id'], current_folder)
                    
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

def display_chatbot_registration():
    """새 챗봇 등록"""
    st.header("➕ 새 챗봇 등록")
    
    with st.form("chatbot_registration"):
        chatbot_name = st.text_input(
            "🤖 챗봇 이름",
            placeholder="예: 고객지원봇, 제품안내봇 등",
            help="등록할 챗봇의 이름을 입력하세요."
        )
        
        folder_name = st.text_input(
            "📂 폴더명 (선택사항)",
            placeholder="미입력 시 챗봇 이름과 동일하게 설정됩니다.",
            help="Azure Blob Storage에서 사용할 폴더명입니다."
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
                # 폴더명이 없으면 챗봇 이름 사용
                final_folder_name = folder_name.strip() or chatbot_name.strip()
                
                success = add_chatbot(
                    chatbot_name=chatbot_name.strip(),
                    folder_name=final_folder_name,
                    description=description.strip()
                )
                
                if success:
                    st.success(f"✅ '{chatbot_name}' 챗봇이 성공적으로 등록되었습니다!")
                    st.balloons()
                    
                    # 폼 초기화를 위한 페이지 새로고침
                    st.rerun()
                else:
                    st.error("❌ 챗봇 등록 중 오류가 발생했습니다.")

def display_file_management():
    """파일 관리 페이지"""
    st.header("📁 파일 관리")
    
    # Azure 설정 확인
    if not is_azure_configured():
        st.warning("⚠️ Azure Storage가 설정되지 않았습니다.")
        st.info("💡 사이드바의 환경 설정을 확인하세요.")
        return
    
    try:
        # Azure 파일 목록 조회
        files = list_azure_files()
        
        if not files:
            st.info("📂 Azure Blob Storage에 파일이 없습니다.")
            return
        
        st.write(f"**📊 총 {len(files)}개의 파일이 저장되어 있습니다.**")
        
        # 파일 목록을 데이터프레임으로 변환
        file_data = []
        for file_info in files:
            file_data.append({
                '파일명': file_info['name'],
                '크기': format_file_size(file_info['size']),
                '수정일': file_info['last_modified'].strftime('%Y-%m-%d %H:%M:%S') if file_info['last_modified'] else 'N/A',
                '타입': file_info.get('content_type', 'N/A')
            })
        
        df_files = pd.DataFrame(file_data)
        
        # 파일 목록 표시 (페이지네이션)
        st.dataframe(
            df_files,
            use_container_width=True,
            hide_index=True
        )
        
        # 폴더별 파일 개수 통계
        st.subheader("📊 폴더별 통계")
        folder_stats = {}
        for file_info in files:
            folder = file_info['name'].split('/')[0] if '/' in file_info['name'] else 'root'
            folder_stats[folder] = folder_stats.get(folder, 0) + 1
        
        stats_data = [{'폴더': k, '파일 개수': v} for k, v in folder_stats.items()]
        st.dataframe(pd.DataFrame(stats_data), hide_index=True)
        
    except Exception as e:
        st.error(f"❌ 파일 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")

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