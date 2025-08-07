import os
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    SearchIndexer,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    FieldMapping,
    FieldMappingFunction
)
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
import json
import time
from dotenv import load_dotenv

load_dotenv()

class AzureSearchIndexCreator:
    def __init__(self, search_service_name, search_admin_key, storage_account_name, storage_account_key, storage_container_name):
        """
        Azure Search 인덱스 생성기 초기화
        """
        
        self.search_service_name = search_service_name
        self.search_endpoint = f"https://{search_service_name}.search.windows.net"
        self.search_admin_key = search_admin_key
        self.storage_account_name = storage_account_name
        self.storage_account_key = storage_account_key
        self.storage_container_name = storage_container_name
        
        # 클라이언트 초기화
        self.search_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(search_admin_key)
        )
        
        self.indexer_client = SearchIndexerClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(search_admin_key)
        )
        
        # Storage 연결 문자열
        self.storage_connection_string = (
            os.getenv("AZURE_STORAGE_CONNECTION_STRING") or 
            f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={storage_account_key};EndpointSuffix=core.windows.net"
        )

    def create_data_source(self, data_source_name, folder_path=""):
        """
        Azure Search 데이터 소스 생성 - 폴더 기준 필터링 (OData 방식)
        """
        query = None
        if folder_path:
            # 폴더 경로 정규화
            folder_clean = folder_path.strip('/')
            
            # OData 방식으로 폴더 필터링 (startswith 함수 사용)
            query = f"startswith(metadata_storage_name, '{folder_clean}/')"
            print(f"폴더 필터 적용: {folder_clean}/ (OData 방식)")
        
        data_source = SearchIndexerDataSourceConnection(
            name=data_source_name,
            type="azureblob",
            connection_string=self.storage_connection_string,
            container=SearchIndexerDataContainer(name=self.storage_container_name, query=query)
        )
        
        try:
            result = self.indexer_client.create_or_update_data_source_connection(data_source)
            print(f"데이터 소스 '{data_source_name}' 생성 완료")
            if query:
                print(f"적용된 쿼리: {query}")
            return result
        except Exception as e:
            print(f"데이터 소스 생성 중 오류 발생: {str(e)}")
            return None

    def create_simple_index(self, index_name):
        """
        간단한 검색 인덱스 스키마 생성 - 기본 필드만
        """
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="ko.microsoft"),
            SimpleField(name="metadata_storage_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="metadata_storage_path", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="metadata_storage_file_extension", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="metadata_storage_size", type=SearchFieldDataType.Int64, filterable=True),
            SimpleField(name="metadata_storage_last_modified", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
        ]
        
        index = SearchIndex(
            name=index_name,
            fields=fields
        )
        
        try:
            result = self.search_client.create_or_update_index(index)
            print(f"인덱스 '{index_name}' 생성 완료")
            return result
        except Exception as e:
            print(f"인덱스 생성 중 오류 발생: {str(e)}")
            return None

    def create_simple_indexer(self, indexer_name, data_source_name, index_name):
        """
        스킬셋 없는 간단한 인덱서 생성
        """
        field_mappings = [
            FieldMapping(
                source_field_name="metadata_storage_path", 
                target_field_name="id",
                mapping_function=FieldMappingFunction(name="base64Encode")
            ),
            FieldMapping(source_field_name="content", target_field_name="content"),
        ]
        
        indexer = SearchIndexer(
            name=indexer_name,
            data_source_name=data_source_name,
            target_index_name=index_name,
            field_mappings=field_mappings,
            parameters={
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default"
                }
            }
        )
        
        try:
            result = self.indexer_client.create_or_update_indexer(indexer)
            print(f"인덱서 '{indexer_name}' 생성 완료")
            
            # 인덱서 실행
            self.indexer_client.run_indexer(indexer_name)
            print(f"인덱서 '{indexer_name}' 실행 시작")
            return result
        except Exception as e:
            print(f"인덱서 생성 중 오류 발생: {str(e)}")
            return None

    def check_indexer_status(self, indexer_name):
        """
        인덱서 실행 상태 확인
        """
        try:
            status = self.indexer_client.get_indexer_status(indexer_name)
            print(f"\n=== 인덱서 상태 상세 정보 ===")
            print(f"인덱서 상태: {status.status}")
            print(f"마지막 실행 결과: {status.last_result.status if status.last_result else 'N/A'}")
            
            if status.last_result:
                print(f"처리된 문서 수: {status.last_result.item_count}")
                print(f"성공한 문서 수: {status.last_result.item_count - len(status.last_result.errors) if status.last_result.errors else status.last_result.item_count}")
                print(f"실패한 문서 수: {len(status.last_result.errors) if status.last_result.errors else 0}")
                print(f"시작 시간: {status.last_result.start_time}")
                print(f"종료 시간: {status.last_result.end_time}")
                
                if status.last_result.errors:
                    print("\n오류 목록:")
                    for i, error in enumerate(status.last_result.errors):
                        print(f"  {i+1}. 키: {error.key}")
                        print(f"     메시지: {error.error_message}")
                        print(f"     상태코드: {error.status_code}")
                        print()
                
                if status.last_result.warnings:
                    print("\n경고 목록:")
                    for i, warning in enumerate(status.last_result.warnings):
                        print(f"  {i+1}. 키: {warning.key}")
                        print(f"     메시지: {warning.message}")
                        print()
            
            return status
        except Exception as e:
            print(f"인덱서 상태 확인 중 오류 발생: {str(e)}")
            return None

    def check_index_document_count(self, index_name):
        """
        인덱스의 문서 개수 확인
        """
        try:
            from azure.search.documents import SearchClient
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=index_name,
                credential=AzureKeyCredential(self.search_admin_key)
            )
            
            # 전체 문서 개수 조회
            results = search_client.search("*", include_total_count=True, top=0)
            document_count = results.get_count()
            
            print(f"\n=== 인덱스 정보 ===")
            print(f"인덱스 이름: {index_name}")
            print(f"문서 개수: {document_count}")
            
            # 샘플 문서 몇 개 조회
            if document_count > 0:
                sample_results = search_client.search("*", top=3)
                print("\n샘플 문서:")
                for i, doc in enumerate(sample_results):
                    print(f"  문서 {i+1}: {doc.get('metadata_storage_name', 'N/A')}")
                    print(f"    내용 미리보기: {doc.get('content', '')[:100]}...")
            
            return document_count
        except Exception as e:
            print(f"인덱스 문서 개수 확인 중 오류 발생: {str(e)}")
            return None

    def debug_folder_contents(self, folder_path=""):
        """
        폴더 내용 상세 디버깅
        """
        try:
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection_string)
            container_client = blob_service_client.get_container_client(self.storage_container_name)
            
            print(f"\n=== 폴더 '{folder_path}' 상세 분석 ===")
            
            # 모든 Blob 목록 가져오기
            all_blobs = list(container_client.list_blobs())
            print(f"전체 컨테이너의 파일 수: {len(all_blobs)}")
            
            # 폴더별 분류
            folder_files = {}
            root_files = []
            
            for blob in all_blobs:
                if '/' in blob.name:
                    folder = blob.name.split('/')[0]
                    if folder not in folder_files:
                        folder_files[folder] = []
                    folder_files[folder].append(blob.name)
                else:
                    root_files.append(blob.name)
            
            print(f"\n루트 디렉토리의 파일 수: {len(root_files)}")
            if root_files:
                print("루트 파일 예시:")
                for file in root_files[:5]:
                    print(f"  - {file}")
            
            print(f"\n발견된 폴더들:")
            for folder, files in folder_files.items():
                print(f"  {folder}/: {len(files)}개 파일")
                if folder == folder_path.strip('/'):
                    print(f"    타겟 폴더 '{folder_path}' 발견! 파일 목록:")
                    for file in files[:10]:
                        print(f"      - {file}")
            
            # 지정된 폴더의 파일만 필터링
            if folder_path:
                folder_clean = folder_path.strip('/')
                target_files = []
                for blob in all_blobs:
                    if blob.name.startswith(folder_clean + '/'):
                        target_files.append(blob.name)
                
                print(f"\n'{folder_clean}/' 으로 시작하는 파일들: {len(target_files)}개")
                for file in target_files[:10]:
                    print(f"  - {file}")
                
                return target_files
            
            return all_blobs
            
        except Exception as e:
            print(f"폴더 분석 중 오류: {str(e)}")
            return []

    def delete_existing_resources(self, base_name):
        """
        기존 리소스들 삭제
        """
        indexer_name = f"{base_name}-indexer"
        index_name = f"{base_name}-index"
        data_source_name = f"{base_name}-datasource"
        
        print(f"기존 리소스 삭제 중...")
        
        try:
            self.indexer_client.delete_indexer(indexer_name)
            print(f"기존 인덱서 '{indexer_name}' 삭제 완료")
        except Exception as e:
            print(f"인덱서 삭제 중 오류 (무시): {str(e)}")
        
        try:
            self.search_client.delete_index(index_name)
            print(f"기존 인덱스 '{index_name}' 삭제 완료")
        except Exception as e:
            print(f"인덱스 삭제 중 오류 (무시): {str(e)}")
        
        try:
            self.indexer_client.delete_data_source_connection(data_source_name)
            print(f"기존 데이터소스 '{data_source_name}' 삭제 완료")
        except Exception as e:
            print(f"데이터소스 삭제 중 오류 (무시): {str(e)}")

    def create_simple_pipeline(self, base_name, folder_path="guide"):
        """
        간단한 파이프라인 생성 - 특정 폴더 기준
        """
        print(f"=== 간단한 Azure Search 인덱스 파이프라인 생성 시작 ===")
        print(f"대상 폴더: {folder_path}")
        
        # 폴더 내용 상세 분석
        target_files = self.debug_folder_contents(folder_path)
        if not target_files:
            print(f"폴더 '{folder_path}'에서 처리할 파일이 없습니다.")
            return False
        
        # 기존 리소스 삭제
        self.delete_existing_resources(base_name)
        time.sleep(10)
        
        data_source_name = f"{base_name}-datasource"
        index_name = f"{base_name}-index"
        indexer_name = f"{base_name}-indexer"
        
        # 1. 데이터 소스 생성 (폴더 경로 포함)
        if not self.create_data_source(data_source_name, folder_path):
            return False
        
        # 2. 인덱스 생성
        if not self.create_simple_index(index_name):
            return False
        
        # 3. 인덱서 생성 및 실행
        if not self.create_simple_indexer(indexer_name, data_source_name, index_name):
            return False
        
        print(f"=== 파이프라인 생성 완료 ===")
        return True

    def diagnose_simple_indexing(self, base_name):
        """
        간단한 인덱싱 문제 진단
        """
        print(f"\n=== 간단한 인덱싱 문제 진단 시작 ===")
        
        indexer_name = f"{base_name}-indexer"
        index_name = f"{base_name}-index"
        data_source_name = f"{base_name}-datasource"
        
        # 1. 데이터소스 확인
        print(f"\n1. 데이터소스 확인...")
        try:
            datasource = self.indexer_client.get_data_source_connection(data_source_name)
            print(f"   데이터소스 존재: ✓")
            print(f"   컨테이너: {datasource.container.name}")
            print(f"   쿼리: {datasource.container.query if datasource.container.query else 'None (전체 컨테이너)'}")
        except Exception as e:
            print(f"   데이터소스 오류: {e}")
        
        # 2. 인덱스 확인
        print(f"\n2. 인덱스 확인...")
        try:
            index = self.search_client.get_index(index_name)
            print(f"   인덱스 존재: ✓")
            print(f"   필드 수: {len(index.fields)}")
        except Exception as e:
            print(f"   인덱스 오류: {e}")
        
        # 3. 인덱서 상태 확인
        print(f"\n3. 인덱서 상태 확인...")
        self.check_indexer_status(indexer_name)
        
        # 4. 인덱스 문서 개수 확인
        print(f"\n4. 인덱스 문서 개수 확인...")
        self.check_index_document_count(index_name)

def main():
    """
    폴더 기준 인덱싱 실행
    """
    config = {
        "search_service_name": os.getenv("AZURE_SEARCH_SERVICE_NAME"),
        "search_admin_key": os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"),
        "storage_account_name": os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
        "storage_account_key": os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
        "storage_container_name": os.getenv("AZURE_STORAGE_CONTAINER_NAME"),
    }
    
    missing_vars = [key for key, value in config.items() if not value]
    if missing_vars:
        print(f"다음 환경변수들이 설정되지 않았습니다: {', '.join([var.upper() for var in missing_vars])}")
        return
    
    creator = AzureSearchIndexCreator(**config)
    
    # 폴더 설정
    folder_path = "guide"  # 여기서 원하는 폴더명으로 변경
    base_name = f"folder-{folder_path}"
    
    print(f"타겟 폴더: {folder_path}")
    
    # 폴더 기준 파이프라인 실행
    success = creator.create_simple_pipeline(base_name, folder_path)
    
    if success:
        print(f"'{folder_path}' 폴더 인덱싱이 시작되었습니다.")
        
        # 잠시 후 상태 확인
        time.sleep(30)
        creator.diagnose_simple_indexing(base_name)
    else:
        print("인덱스 생성에 실패했습니다.")

if __name__ == "__main__":
    main()