from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
file_path = "example.pdf"

# Blob client
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# 컨테이너 존재 여부 확인 후 생성
try:
    blob_service_client.get_container_client(container_name).get_container_properties()
    print(f"📦 컨테이너 '{container_name}' 존재함")
except:
    print(f"📦 컨테이너 '{container_name}' 없음 → 생성 중")
    blob_service_client.create_container(container_name)
    
blob_client = blob_service_client.get_blob_client(container=container_name, blob=os.path.basename(file_path))

with open(file_path, "rb") as data:
    blob_client.upload_blob(data, overwrite=True)

print(f"✅ Uploaded {file_path} to Azure Blob Storage.")
