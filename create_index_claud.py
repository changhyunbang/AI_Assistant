from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient, SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchFieldDataType, SimpleField, SearchableField,
    SearchIndexerDataSourceConnection, SearchIndexerDataContainer,
    SearchIndexerSkillset, SearchIndexer,
    InputFieldMappingEntry, OutputFieldMappingEntry,
    FieldMapping, OcrSkill, LanguageDetectionSkill, KeyPhraseExtractionSkill,
    MergeSkill, SplitSkill
)
from azure.search.documents import SearchClient
import os
from dotenv import load_dotenv
import time

load_dotenv()

# 환경 변수에서 폴더명과 인덱스명 가져오기
folder_name = os.getenv("FOLDER_NAME")
index_name = os.getenv("INDEX_NAME")

if not folder_name:
    print("❌ FOLDER_NAME 환경변수가 설정되지 않았습니다.")
    exit(1)

if not index_name:
    # 기본 인덱스명 생성 (폴더명-index)
    index_name = f"{folder_name}-index"

print(f"📂 대상 폴더: {folder_name}")
print(f"📊 생성할 인덱스: {index_name}")

# 환경 변수
endpoint = f"https://{os.getenv('AZURE_SEARCH_SERVICE_NAME')}.search.windows.net"
credential = AzureKeyCredential(os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"))

container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")
data_source_name = f"{folder_name}-datasource"
skillset_name = f"{folder_name}-skillset"
indexer_name = "azureblob-indexer"  # 기존 indexer 사용

# 클라이언트
index_client = SearchIndexClient(endpoint, credential)
indexer_client = SearchIndexerClient(endpoint, credential)

print("🔍 기존 리소스 상태 확인...")

# 기존 indexer 존재 여부 확인
try:
    existing_indexer = indexer_client.get_indexer(indexer_name)
    print(f"✅ 기존 Indexer '{indexer_name}' 발견")
except Exception as e:
    print(f"❌ 필수 Indexer '{indexer_name}'가 존재하지 않습니다.")
    print(f"❌ 오류 세부정보: {e}")
    print(f"💡 먼저 '{indexer_name}' 인덱서를 생성해야 합니다.")
    exit(1)

# 기존 리소스 정리 (indexer는 제외)
print("🧹 기존 리소스 정리 중...")
for resource_type, resource_name, delete_func in [
    ("skillset", skillset_name, indexer_client.delete_skillset),
    ("data source", data_source_name, indexer_client.delete_data_source_connection),
    ("index", index_name, index_client.delete_index)
]:
    try:
        delete_func(resource_name)
        print(f"✅ 기존 {resource_type} '{resource_name}' 삭제됨")
    except:
        print(f"ℹ️ {resource_type} '{resource_name}' 없음 (정상)")

time.sleep(2)  # 삭제 대기

print("\n🏗️ 새로운 리소스 생성 중...")

# 1. 향상된 인덱스 생성
index = SearchIndex(
    name=index_name,
    fields=[
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="content", type=SearchFieldDataType.String, 
                       searchable=True, retrievable=True, analyzer_name="ko.microsoft"),
        SearchableField(name="merged_content", type=SearchFieldDataType.String,
                       searchable=True, retrievable=True, analyzer_name="ko.microsoft"),
        SearchableField(name="text", type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                       searchable=True, retrievable=True),
        SimpleField(name="languageCode", type=SearchFieldDataType.String, 
                   filterable=True, retrievable=True),
        SearchableField(
            name="keyPhrases",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True, retrievable=True
        ),
        SimpleField(name="metadata_storage_name", type=SearchFieldDataType.String, 
                   filterable=True, retrievable=True, sortable=True),
        SimpleField(name="metadata_storage_path", type=SearchFieldDataType.String,
                   retrievable=True),
        SimpleField(name="metadata_storage_size", type=SearchFieldDataType.Int64,
                   filterable=True, retrievable=True, sortable=True),
        SimpleField(name="metadata_storage_last_modified", type=SearchFieldDataType.DateTimeOffset,
                   filterable=True, retrievable=True, sortable=True),
    ]
)

try:
    index_client.create_index(index)
    print(f"✅ Index '{index_name}' 생성 완료")
except Exception as e:
    print(f"❌ Index 생성 실패: {e}")
    exit(1)

# 2. 데이터 소스 생성 (특정 폴더만 대상)
data_source = SearchIndexerDataSourceConnection(
    name=data_source_name,
    type="azureblob",
    connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    container=SearchIndexerDataContainer(
        name=container_name,
        query=folder_name  # 특정 폴더만 인덱싱
    ),
    description=f"PDF files in folder '{folder_name}' for indexing"
)

try:
    indexer_client.create_data_source_connection(data_source)
    print(f"✅ Data source '{data_source_name}' 생성 완료 (폴더: {folder_name})")
except Exception as e:
    print(f"❌ Data source 생성 실패: {e}")
    exit(1)

# 3. 향상된 Skillset 생성
skillset = SearchIndexerSkillset(
    name=skillset_name,
    description=f"Enhanced PDF OCR and analysis for folder '{folder_name}'",
    skills=[
        # OCR Skill - 이미지에서 텍스트 추출
        OcrSkill(
            name="ocr-skill",
            description="Extract text from images in PDF",
            context="/document/normalized_images/*",
            inputs=[
                InputFieldMappingEntry(name="image", source="/document/normalized_images/*")
            ],
            outputs=[
                OutputFieldMappingEntry(name="text", target_name="text")
            ]
        ),
        
        # Merge Skill - 원본 텍스트와 OCR 텍스트 합치기
        MergeSkill(
            name="merge-skill",
            description="Merge original content with OCR text",
            context="/document",
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/content"),
                InputFieldMappingEntry(name="itemsToInsert", source="/document/normalized_images/*/text")
            ],
            outputs=[
                OutputFieldMappingEntry(name="mergedText", target_name="merged_content")
            ]
        ),
        
        # Language Detection - 합쳐진 텍스트 기준
        LanguageDetectionSkill(
            name="language-skill",
            description="Detect language from merged text",
            context="/document",
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/merged_content")
            ],
            outputs=[
                OutputFieldMappingEntry(name="languageCode", target_name="languageCode")
            ]
        ),
        
        # Key Phrase Extraction - 합쳐진 텍스트 기준
        KeyPhraseExtractionSkill(
            name="keyphrase-skill",
            description="Extract key phrases from merged text",
            context="/document",
            inputs=[
                InputFieldMappingEntry(name="text", source="/document/merged_content"),
                InputFieldMappingEntry(name="languageCode", source="/document/languageCode")
            ],
            outputs=[
                OutputFieldMappingEntry(name="keyPhrases", target_name="keyPhrases")
            ]
        )
    ]
)

try:
    indexer_client.create_skillset(skillset)
    print(f"✅ Skillset '{skillset_name}' 생성 완료")
except Exception as e:
    print(f"❌ Skillset 생성 실패: {e}")
    exit(1)

# 4. 기존 Indexer 설정 확인
print(f"🔍 기존 Indexer '{indexer_name}' 설정 확인...")

try:
    print(f"📋 현재 Indexer 설정:")
    print(f"  - Data Source: {existing_indexer.data_source_name}")
    print(f"  - Target Index: {existing_indexer.target_index_name}")
    print(f"  - Skillset: {existing_indexer.skillset_name}")
    print(f"  - Field Mappings: {len(existing_indexer.field_mappings or [])}개")
    print(f"  - Output Mappings: {len(existing_indexer.output_field_mappings or [])}개")
    
    print(f"💡 기존 Indexer '{indexer_name}'를 그대로 사용합니다.")
    print(f"⚠️ 주의: 현재 설정으로 인덱싱이 진행됩니다.")
    
except Exception as e:
    print(f"❌ Indexer 설정 확인 실패: {e}")
    exit(1)

# 5. Indexer 리셋 및 실행 (기존 설정으로)
print(f"\n🔄 Indexer '{indexer_name}' 리셋 및 실행...")
print(f"⚠️ 주의: 기존 인덱서 설정으로 실행됩니다.")
print(f"📊 새로 생성된 인덱스 '{index_name}'와 호환성을 확인하세요.")

try:
    # indexer 리셋 (기존 인덱싱 상태 초기화)
    indexer_client.reset_indexer(indexer_name)
    print(f"🔄 Indexer '{indexer_name}' 리셋 완료")
    
    time.sleep(3)  # 리셋 대기
    
    # indexer 실행
    indexer_client.run_indexer(indexer_name)
    print(f"🚀 Indexer '{indexer_name}' 실행 시작")
except Exception as e:
    print(f"❌ Indexer 리셋/실행 실패: {e}")
    print(f"💡 힌트: 기존 인덱서 설정이 새 인덱스와 호환되지 않을 수 있습니다.")

# 6. 향상된 상태 모니터링
print("⏳ Indexer 실행 상태 모니터링...")
max_wait_cycles = 30  # 최대 10분 대기 (20초 * 30)

for i in range(max_wait_cycles):
    time.sleep(20)  # 20초마다 체크
    
    try:
        status = indexer_client.get_indexer_status(indexer_name)
        current_status = status.status
        print(f"📊 상태 체크 {i+1}/{max_wait_cycles}: {current_status}")
        
        if status.last_result:
            print(f"  📅 시작: {status.last_result.start_time}")
            print(f"  📅 종료: {status.last_result.end_time}")
            print(f"  📄 처리된 문서: {status.last_result.item_count}")
            print(f"  ❌ 실패한 문서: {status.last_result.failed_item_count}")
            
            if status.last_result.end_time:
                if status.last_result.status == "success":
                    print("✅ Indexer 실행 성공!")
                    break
                else:
                    print(f"❌ Indexer 실패: {status.last_result.error_message}")
                    if status.last_result.errors:
                        for err in status.last_result.errors:
                            print(f"⚠️ 세부 에러: {err.name} - {err.error_message}")
                    break
        print("  " + "-" * 50)
    except Exception as e:
        print(f"⚠️ 상태 확인 실패: {e}")

# 7. 결과 확인 및 검증
print(f"\n🔍 Index '{index_name}' 내용 확인:")
search_client = SearchClient(
    endpoint=endpoint,
    index_name=index_name,
    credential=credential
)

try:
    # 전체 문서 수 확인
    results = search_client.search(search_text="*", top=5, include_total_count=True)
    total_count = results.get_count()
    print(f"📊 총 인덱싱된 문서 수: {total_count}")
    
    if total_count > 0:
        print(f"\n📋 상위 {min(5, total_count)}개 문서 미리보기:")
        
        for idx, doc in enumerate(results, 1):
            print(f"\n[문서 {idx}]")
            print(f"📄 ID: {doc['id']}")
            print(f"📁 파일명: {doc.get('metadata_storage_name', '없음')}")
            print(f"📏 파일크기: {doc.get('metadata_storage_size', 0):,} bytes")
            print(f"📅 수정일: {doc.get('metadata_storage_last_modified', '없음')}")
            
            # 원본 콘텐츠
            content = doc.get("content", "")
            if content:
                print(f"📝 원본 Content: {content[:150]}{'...' if len(content) > 150 else ''}")
            
            # 합쳐진 콘텐츠 (OCR + 원본)
            merged_content = doc.get("merged_content", "")
            if merged_content:
                print(f"🔗 합쳐진 Content: {merged_content[:150]}{'...' if len(merged_content) > 150 else ''}")
            
            # OCR 텍스트 배열
            ocr_texts = doc.get("text", [])
            if ocr_texts:
                print(f"🔍 OCR Text 개수: {len(ocr_texts)}")
                if ocr_texts:
                    first_ocr = ocr_texts[0] if isinstance(ocr_texts[0], str) else str(ocr_texts[0])
                    print(f"🔍 첫 번째 OCR: {first_ocr[:100]}{'...' if len(first_ocr) > 100 else ''}")
            
            print(f"🌍 Language: {doc.get('languageCode', '없음')}")
            key_phrases = doc.get('keyPhrases', [])
            if key_phrases:
                print(f"🔑 Key Phrases ({len(key_phrases)}개): {', '.join(key_phrases[:5])}{'...' if len(key_phrases) > 5 else ''}")
            
            print("=" * 80)
    else:
        print("⚠️ 인덱싱된 문서가 없습니다. 다음 사항을 확인해보세요:")
        print("  - 폴더 경로가 올바른지")
        print("  - 해당 폴더에 PDF 파일이 있는지")
        print("  - Azure Storage 연결이 정상인지")
        
except Exception as e:
    print(f"❌ 검색 실패: {e}")

print(f"\n🎉 설정 완료!")
print(f"📂 대상 폴더: {folder_name}")
print(f"📊 생성된 인덱스: {index_name}")
print(f"🔧 사용된 인덱서: {indexer_name}")
print(f"💡 이제 검색 스크립트에서 index_name '{index_name}'을 사용하세요.")

# 8. 간단한 테스트 검색 (문서가 있는 경우)
if total_count > 0:
    print(f"\n🔍 간단한 검색 테스트:")
    try:
        test_results = search_client.search(search_text="*", top=1)
        for doc in test_results:
            content = doc.get('merged_content', '') or doc.get('content', '')
            if content:
                # 첫 번째 단어로 검색 테스트
                first_words = ' '.join(content.split()[:2])
                if first_words.strip():
                    print(f"🔎 테스트 검색어: '{first_words}'")
                    search_results = search_client.search(search_text=first_words, top=3)
                    print(f"📊 검색 결과: {len(list(search_results))}개 문서 발견")
                    break
    except Exception as e:
        print(f"⚠️ 테스트 검색 실패: {e}")

print("\n✨ 스크립트 실행 완료!")