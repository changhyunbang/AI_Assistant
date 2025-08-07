import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

def debug_storage():
    # Storage 연결 설정
    storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    storage_container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
    
    storage_connection_string = (
        os.getenv("AZURE_STORAGE_CONNECTION_STRING") or 
        f"DefaultEndpointsProtocol=https;AccountName={storage_account_name};AccountKey={storage_account_key};EndpointSuffix=core.windows.net"
    )
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
        container_client = blob_service_client.get_container_client(storage_container_name)
        
        print(f"=== Storage Container '{storage_container_name}' 분석 ===\n")
        
        # 모든 Blob 목록 가져오기
        all_blobs = list(container_client.list_blobs())
        print(f"전체 파일 수: {len(all_blobs)}")
        
        # 폴더별 분류
        folder_files = {}
        root_files = []
        
        print("\n=== 전체 파일 목록 (처음 20개) ===")
        for i, blob in enumerate(all_blobs[:20]):
            print(f"{i+1:2d}. {blob.name}")
            
            if '/' in blob.name:
                folder = blob.name.split('/')[0]
                if folder not in folder_files:
                    folder_files[folder] = []
                folder_files[folder].append(blob.name)
            else:
                root_files.append(blob.name)
        
        print(f"\n=== 폴더 구조 ===")
        if root_files:
            print(f"루트 디렉토리: {len(root_files)}개 파일")
            for file in root_files[:5]:
                print(f"  - {file}")
        
        print(f"\n발견된 폴더들:")
        for folder, files in folder_files.items():
            print(f"  📁 {folder}/: {len(files)}개 파일")
            # 각 폴더의 파일 예시 표시
            for file in files[:3]:
                print(f"     - {file}")
            if len(files) > 3:
                print(f"     ... 그 외 {len(files)-3}개 파일")
        
        # guide 폴더 특별 확인
        guide_files = [blob.name for blob in all_blobs if blob.name.startswith('guide/')]
        print(f"\n=== 'guide/' 폴더 상세 확인 ===")
        print(f"guide/로 시작하는 파일: {len(guide_files)}개")
        
        if guide_files:
            print("guide 폴더의 파일들:")
            for file in guide_files:
                print(f"  - {file}")
        else:
            print("❌ 'guide/' 폴더에 파일이 없습니다!")
            
            # 비슷한 이름의 폴더 찾기
            similar_folders = [folder for folder in folder_files.keys() if 'guide' in folder.lower()]
            if similar_folders:
                print(f"비슷한 이름의 폴더들: {similar_folders}")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    debug_storage()