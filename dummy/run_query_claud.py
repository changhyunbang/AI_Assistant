from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# 새로운 simple index 사용
INDEX_NAME = "pdf-index-simple"

search_client = SearchClient(
    endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE_NAME')}.search.windows.net",
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"))
)

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2023-12-01-preview"
)

def display_documents():
    """인덱스의 모든 문서를 표시"""
    print("🔍 인덱스 내용 확인:")
    print("=" * 80)
    
    try:
        results = search_client.search(search_text="*", top=10, include_total_count=True)
        total_count = results.get_count()
        print(f"📊 총 문서 수: {total_count}")
        
        if total_count == 0:
            print("⚠️ 인덱스에 문서가 없습니다. 먼저 indexer를 실행해주세요.")
            return False
        
        for i, doc in enumerate(results, 1):
            print(f"\n📄 Document {i}:")
            print(f"   ID: {doc.get('id', '없음')}")
            print(f"   파일명: {doc.get('metadata_storage_name', '없음')}")
            
            # 원본 content 확인
            content = doc.get("content", "")
            if content and content.strip():
                print(f"   📝 원본 Content: {content[:150]}...")
            else:
                print("   📝 원본 Content: 없음")
            
            # OCR text 확인  
            ocr_text = doc.get("ocr_text", "")
            if ocr_text and ocr_text.strip():
                print(f"   🔍 OCR Text: {ocr_text[:150]}...")
            else:
                print("   🔍 OCR Text: 없음")
            
            print(f"   🌍 Language: {doc.get('languageCode', '없음')}")
            
            key_phrases = doc.get('keyPhrases', [])
            if key_phrases:
                print(f"   🔑 Key Phrases: {key_phrases[:5]}")  # 상위 5개만
            else:
                print("   🔑 Key Phrases: 없음")
            
            print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 문서 조회 실패: {e}")
        return False

def get_best_content(doc):
    """문서에서 가장 좋은 텍스트 내용을 반환"""
    content = doc.get("content", "").strip()
    ocr_text = doc.get("ocr_text", "").strip()
    filename = doc.get("metadata_storage_name", "Unknown")
    
    # OCR 텍스트가 있으면 우선 사용 (PDF 이미지에서 추출된 텍스트)
    if ocr_text:
        return ocr_text, f"{filename} (OCR)"
    # 원본 텍스트가 있으면 사용 (텍스트 기반 PDF)
    elif content:
        return content, f"{filename} (원본)"
    else:
        return "", filename

def search_and_answer(question):
    """질문에 대해 검색하고 GPT로 답변 생성"""
    print(f"\n🔍 검색 중: '{question}'")
    
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
            text, source = get_best_content(doc)
            if text:
                contexts.append(text)
                sources.append(source)
        
        if not contexts:
            return "❌ 질문과 관련된 문서를 찾을 수 없습니다."
        
        print(f"📚 {len(contexts)}개 문서에서 정보를 찾았습니다:")
        for i, source in enumerate(sources, 1):
            print(f"   {i}. {source}")
        
        # 모든 컨텍스트를 합치되, 너무 길면 자르기
        combined_context = "\n\n".join(contexts)
        if len(combined_context) > 8000:  # 토큰 제한을 고려하여 자르기
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
        return f"🤖 답변:\n{answer}\n\n📋 참고 문서: {', '.join(sources)}"
        
    except Exception as e:
        return f"❌ 검색 또는 답변 생성 실패: {e}"

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 Azure AI Search + OpenAI 통합 검색 시스템")
    print("=" * 80)
    
    # 먼저 인덱스 상태 확인
    has_documents = display_documents()
    
    if not has_documents:
        print("\n⚠️ 문서가 없어서 검색을 진행할 수 없습니다.")
        print("💡 먼저 indexer 스크립트를 실행하여 PDF 파일들을 인덱싱해주세요.")
        return
    
    print(f"\n💡 '{INDEX_NAME}' 인덱스를 사용하여 검색합니다.")
    print("💡 'show'를 입력하면 다시 문서 목록을 확인할 수 있습니다.")
    print("💡 종료하려면 'exit' 또는 'quit'를 입력하세요.\n")
    
    while True:
        question = input("❓ 질문을 입력하세요: ").strip()
        
        if question.lower() in ("exit", "quit"):
            print("👋 프로그램을 종료합니다.")
            break
        elif question.lower() == "show":
            display_documents()
            continue
        elif not question:
            print("⚠️ 질문을 입력해주세요.")
            continue
        
        # 검색 및 답변 생성
        answer = search_and_answer(question)
        print(answer)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()