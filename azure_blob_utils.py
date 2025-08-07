"""
Azure Blob Storage 관리 유틸리티
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from dotenv import load_dotenv
import streamlit as st

try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logging.warning("Azure Storage SDK가 설치되지 않았습니다. pip install azure-storage-blob으로 설치하세요.")

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureBlobManager:
    """Azure Blob Storage 관리 클래스"""
    
    def __init__(self):
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
        self.blob_service_client = None
        
        if self.connection_string and AZURE_AVAILABLE:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                logger.info("Azure Blob Service 클라이언트 초기화 완료")
            except Exception as e:
                logger.error(f"Azure Blob Service 클라이언트 초기화 실패: {e}")
    
    def is_configured(self) -> bool:
        """Azure Storage 설정 확인"""
        return bool(
            self.connection_string and 
            self.container_name and 
            self.blob_service_client and
            AZURE_AVAILABLE
        )
    
    def get_config_status(self) -> Tuple[bool, List[str]]:
        """설정 상태와 누락된 항목 반환"""
        missing = []
        
        if not AZURE_AVAILABLE:
            missing.append("azure-storage-blob 패키지")
        
        if not self.connection_string:
            missing.append("AZURE_STORAGE_CONNECTION_STRING")
        
        if not self.container_name:
            missing.append("AZURE_STORAGE_CONTAINER_NAME")
        
        configured = len(missing) == 0
        return configured, missing
    
    def ensure_container_exists(self) -> bool:
        """컨테이너 존재 여부 확인 후 생성"""
        if not self.is_configured():
            return False
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.get_container_properties()
            logger.info(f"컨테이너 '{self.container_name}' 존재 확인")
            return True
        except Exception:
            try:
                self.blob_service_client.create_container(self.container_name)
                logger.info(f"컨테이너 '{self.container_name}' 생성 완료")
                return True
            except Exception as e:
                logger.error(f"컨테이너 생성 실패: {e}")
                return False
    
    def upload_file(self, file_data: bytes, blob_name: str, overwrite: bool = True) -> Tuple[bool, str]:
        """파일을 Azure Blob Storage에 업로드"""
        if not self.is_configured():
            return False, "Azure Storage가 설정되지 않았습니다."
        
        if not self.ensure_container_exists():
            return False, "컨테이너 생성/확인 실패"
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(file_data, overwrite=overwrite)
            logger.info(f"파일 업로드 완료: {blob_name}")
            return True, "업로드 성공"
            
        except Exception as e:
            error_msg = f"파일 업로드 실패: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def list_files(self, prefix: str = None) -> List[Dict]:
        """Blob 파일 목록 조회"""
        if not self.is_configured():
            return []
        
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            
            file_list = []
            for blob in blobs:
                file_info = {
                    'name': blob.name,
                    'size': blob.size,
                    'last_modified': blob.last_modified,
                    'content_type': blob.content_settings.content_type if blob.content_settings else 'application/octet-stream'
                }
                file_list.append(file_info)
            
            return file_list
            
        except Exception as e:
            logger.error(f"파일 목록 조회 실패: {e}")
            return []
    
    def get_file_info(self, blob_name: str) -> Optional[Dict]:
        """특정 파일 정보 조회"""
        if not self.is_configured():
            return None
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            properties = blob_client.get_blob_properties()
            
            return {
                'name': blob_name,
                'size': properties.size,
                'last_modified': properties.last_modified,
                'content_type': properties.content_settings.content_type if properties.content_settings else 'application/octet-stream',
                'etag': properties.etag
            }
            
        except Exception as e:
            logger.error(f"파일 정보 조회 실패: {e}")
            return None
    
    def delete_file(self, blob_name: str) -> Tuple[bool, str]:
        """파일 삭제"""
        if not self.is_configured():
            return False, "Azure Storage가 설정되지 않았습니다."
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"파일 삭제 완료: {blob_name}")
            return True, "삭제 성공"
            
        except Exception as e:
            error_msg = f"파일 삭제 실패: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def upload_multiple_files(self, files_data: List[Tuple[bytes, str]]) -> Tuple[int, List[str]]:
        """여러 파일 동시 업로드"""
        if not self.is_configured():
            return 0, ["Azure Storage가 설정되지 않았습니다."]
        
        success_count = 0
        errors = []
        
        for file_data, blob_name in files_data:
            success, message = self.upload_file(file_data, blob_name)
            if success:
                success_count += 1
            else:
                errors.append(f"{blob_name}: {message}")
        
        return success_count, errors

# 전역 Azure Manager 인스턴스
azure_manager = AzureBlobManager()

# 편의 함수들
def upload_files_to_azure(files_data: List[Tuple[bytes, str, str]]) -> Tuple[int, List[str]]:
    """
    파일들을 Azure에 업로드 (편의 함수)
    
    Args:
        files_data: (file_data, filename, folder_name) 튜플 리스트
    
    Returns:
        (성공한 파일 수, 오류 메시지 리스트)
    """
    if not azure_manager.is_configured():
        return 0, ["Azure Storage가 설정되지 않았습니다."]
    
    success_count = 0
    errors = []
    
    for file_data, filename, folder_name in files_data:
        blob_name = f"{folder_name}/{filename}" if folder_name else filename
        success, message = azure_manager.upload_file(file_data, blob_name)
        
        if success:
            success_count += 1
        else:
            errors.append(f"{filename}: {message}")
    
    return success_count, errors

def list_azure_files(prefix: str = None) -> List[Dict]:
    """Azure 파일 목록 조회 (편의 함수)"""
    return azure_manager.list_files(prefix)

def get_azure_file_info(blob_name: str) -> Optional[Dict]:
    """Azure 파일 정보 조회 (편의 함수)"""
    return azure_manager.get_file_info(blob_name)

def is_azure_configured() -> bool:
    """Azure 설정 여부 확인 (편의 함수)"""
    return azure_manager.is_configured()

def get_azure_config_status() -> Tuple[bool, List[str]]:
    """Azure 설정 상태 확인 (편의 함수)"""
    return azure_manager.get_config_status()

def delete_azure_file(blob_name: str) -> Tuple[bool, str]:
    """Azure 파일 삭제 (편의 함수)"""
    return azure_manager.delete_file(blob_name)

# Streamlit 파일 업로드 함수들
def format_file_size(size_bytes: int) -> str:
    """파일 크기를 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    
    i = int(math.floor(math.log(size_bytes, 1024)))
    if i >= len(size_names):
        i = len(size_names) - 1
    
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def upload_file_to_blob(
    file_data: bytes,
    file_name: str,
    folder_name: str,
    connection_string: str,
    container_name: str
) -> Tuple[bool, str]:
    """단일 파일을 Azure Blob Storage에 업로드"""
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # 컨테이너 확인/생성
        if not ensure_container_exists_direct(blob_service_client, container_name):
            return False, "컨테이너 생성 실패"
        
        # Blob 경로 생성 (폴더명/파일명)
        blob_name = f"{folder_name}/{file_name}" if folder_name else file_name
        
        # Blob 클라이언트 생성
        blob_client = blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        
        # 파일 업로드
        blob_client.upload_blob(file_data, overwrite=True)
        
        return True, f"✅ {file_name} 업로드 완료"
        
    except Exception as e:
        return False, f"❌ 업로드 실패: {str(e)}"

def ensure_container_exists_direct(blob_service_client: BlobServiceClient, container_name: str) -> bool:
    """컨테이너 존재 여부 확인 후 없으면 생성 (직접 호출용)"""
    try:
        blob_service_client.get_container_client(container_name).get_container_properties()
        return True
    except Exception:
        try:
            blob_service_client.create_container(container_name)
            return True
        except Exception as e:
            st.error(f"❌ 컨테이너 생성 실패: {str(e)}")
            return False

def display_file_upload_popup(chatbot_name: str, folder_name: str = None) -> bool:
    """파일 업로드 팝업 표시"""
    
    # Azure 연결 정보 확인
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    
    if not connection_string or not container_name:
        st.error("❌ Azure Storage 설정이 필요합니다.")
        st.info("💡 .env 파일에서 AZURE_STORAGE_CONNECTION_STRING과 AZURE_STORAGE_CONTAINER_NAME을 설정하세요.")
        return False
    
    st.subheader(f"📁 {chatbot_name} - 파일 업로드")
    
    # 폴더명 입력
    if not folder_name:
        folder_name = chatbot_name
    
    folder_input = st.text_input(
        "📂 폴더명",
        value=folder_name,
        help="Azure Blob Storage에 생성될 폴더명입니다."
    )
    
    # 파일 업로드 위젯
    uploaded_files = st.file_uploader(
        "📄 업로드할 파일들을 선택하세요",
        accept_multiple_files=True,
        type=None,  # 모든 파일 타입 허용
        help="여러 파일을 동시에 선택할 수 있습니다."
    )
    
    # 업로드 버튼과 진행 상황
    if uploaded_files and st.button("🚀 업로드 시작", type="primary"):
        return process_file_upload(uploaded_files, folder_input, connection_string, container_name)
    
    return False

def process_file_upload(
    uploaded_files: List,
    folder_name: str,
    connection_string: str,
    container_name: str
) -> bool:
    """파일 업로드 처리"""
    
    if not uploaded_files:
        st.warning("⚠️ 업로드할 파일을 선택해주세요.")
        return False
    
    if not folder_name.strip():
        st.warning("⚠️ 폴더명을 입력해주세요.")
        return False
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(uploaded_files)
    success_count = 0
    error_messages = []
    
    # 각 파일 업로드 처리
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            # 진행률 업데이트
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"📤 업로드 중... ({i + 1}/{total_files}) - {uploaded_file.name}")
            
            # 파일 데이터 읽기
            file_data = uploaded_file.read()
            
            # 파일 크기 확인
            file_size = len(file_data)
            if file_size == 0:
                error_messages.append(f"❌ {uploaded_file.name}: 빈 파일입니다.")
                continue
            
            # 파일 업로드
            success, message = upload_file_to_blob(
                file_data=file_data,
                file_name=uploaded_file.name,
                folder_name=folder_name.strip(),
                connection_string=connection_string,
                container_name=container_name
            )
            
            if success:
                success_count += 1
                st.success(f"✅ {uploaded_file.name} ({format_file_size(file_size)}) 업로드 완료")
            else:
                error_messages.append(f"❌ {uploaded_file.name}: {message}")
                
        except Exception as e:
            error_messages.append(f"❌ {uploaded_file.name}: 처리 중 오류 발생 - {str(e)}")
    
    # 최종 결과 표시
    progress_bar.progress(1.0)
    status_text.text("✅ 업로드 완료!")
    
    # 결과 요약
    st.info(f"📊 업로드 결과: 성공 {success_count}개, 실패 {len(error_messages)}개")
    
    # 오류 메시지 표시
    if error_messages:
        with st.expander("⚠️ 오류 상세 내용", expanded=True):
            for error in error_messages:
                st.error(error)
    
    return success_count > 0

# 테스트용 함수
if __name__ == "__main__":
    print("🧪 Azure Blob Utils 테스트 시작")
    
    # 설정 상태 확인
    configured, missing = get_azure_config_status()
    print(f"Azure 설정 상태: {configured}")
    if missing:
        print(f"누락된 항목: {missing}")
    
    if configured:
        # 파일 목록 조회 테스트
        files = list_azure_files()
        print(f"저장된 파일 수: {len(files)}")
        
        if files:
            print("파일 목록:")
            for file_info in files[:5]:  # 처음 5개만 표시
                print(f"  - {file_info['name']} ({file_info['size']} bytes)")
    
    print("✅ Azure Blob Utils 테스트 완료")