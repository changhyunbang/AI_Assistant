from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient, SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchFieldDataType, SimpleField,
    SearchIndexerDataSourceConnection, SearchIndexerDataContainer,
    SearchIndexerSkillset, SearchIndexer,
    InputFieldMappingEntry, OutputFieldMappingEntry,
    FieldMapping, OcrSkill, LanguageDetectionSkill, KeyPhraseExtractionSkill
)
from azure.search.documents.indexes.models import SearchableField
import os
from dotenv import load_dotenv

load_dotenv()

# 환경 변수
endpoint = f"https://{os.getenv('AZURE_SEARCH_SERVICE_NAME')}.search.windows.net"
credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"))

container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
index_name = "pdf-index"
data_source_name = "pdf-datasource"
skillset_name = "pdf-skillset"
indexer_name = "pdf-indexer"

# 클라이언트
index_client = SearchIndexClient(endpoint, credential)
indexer_client = SearchIndexerClient(endpoint, credential)

# 1. 인덱스 생성
index = SearchIndex(
    name=index_name,
    fields=[
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, retrievable=True),  # ✅ 핵심 수정
        SimpleField(name="languageCode", type=SearchFieldDataType.String, filterable=True),
        SearchableField(  # 🔄 이것도 변경해도 좋음
            name="keyPhrases",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            retrievable=True
        ),
        SimpleField(name="metadata_storage_name", type=SearchFieldDataType.String, filterable=True),
    ]
)
index_client.create_or_update_index(index)

# 2. 데이터 소스
data_source = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    container=SearchIndexerDataContainer(name=container_name)
)
indexer_client.create_or_update_data_source_connection(data_source)

# 3. Skillset
skillset = SearchIndexerSkillset(
    name=skillset_name,
    description="PDF AI 분석",
    skills=[
        OcrSkill(
            name="ocr-skill",
            description="이미지에서 텍스트 추출",
            context="/document",
            inputs=[InputFieldMappingEntry(name="image", source="/document/content")],
            outputs=[OutputFieldMappingEntry(name="text", target_name="ocrText")]
        ),
        LanguageDetectionSkill(
            name="language-skill",
            context="/document",
            inputs=[InputFieldMappingEntry(name="text", source="/document/ocrText")],
            outputs=[OutputFieldMappingEntry(name="languageCode", target_name="languageCode")]
        ),
        KeyPhraseExtractionSkill(
            name="keyphrase-skill",
            context="/document",
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/ocrText"),
                InputFieldMappingEntry(name="languageCode", source="/document/languageCode"),
            ],
            outputs=[OutputFieldMappingEntry(name="keyPhrases", target_name="keyPhrases")]
        ),
    ]
)
indexer_client.create_or_update_skillset(skillset)

# 4. Indexer
indexer = SearchIndexer(
    name=indexer_name,
    data_source_name=data_source_name,
    target_index_name=index_name,
    skillset_name=skillset_name,
    field_mappings=[
        FieldMapping(source_field_name="metadata_storage_name", target_field_name="metadata_storage_name"),
    ],
    output_field_mappings=[
        FieldMapping(source_field_name="/document/ocrText", target_field_name="content"),
        FieldMapping(source_field_name="/document/languageCode", target_field_name="languageCode"),
        FieldMapping(source_field_name="/document/keyPhrases", target_field_name="keyPhrases"),
    ]
)
indexer_client.create_or_update_indexer(indexer)

# 실행
indexer_client.run_indexer(indexer_name)
print("✅ Indexer 실행 완료!")

status = indexer_client.get_indexer_status(indexer_name)
print(f"📄 Indexer 상태: {status.status}")
print(f"📅 마지막 시작 시간: {status.last_result.start_time}")
print(f"📅 마지막 종료 시간: {status.last_result.end_time}")
print(f"❌ 에러 메시지: {status.last_result.error_message or '없음'}")

if status.last_result.errors:
    for err in status.last_result.errors:
        print(f"⚠️ 에러: {err.name} - {err.error_message}")
else:
    print("✅ 에러 없음")
