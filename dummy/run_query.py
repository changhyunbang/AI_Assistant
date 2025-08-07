from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

search_client = SearchClient(
    endpoint=f"https://{os.getenv('AZURE_SEARCH_SERVICE_NAME')}.search.windows.net",
    index_name="pdf-index-simple",
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_SERVICE_ADMIN_KEY"))
)

results = search_client.search(search_text="*", top=5)

# 결과 출력

for doc in results:
    print(f"📄 Document ID: {doc['id']}")
    content = doc.get("content")
    if content:
        print(f"📝 Content: {content[:200]}...")
    else:
        print("📝 Content: 없음")
    print(f"🌍 Language: {doc.get('languageCode', '없음')}")
    print(f"🔑 Key Phrases: {doc.get('keyPhrases', [])}")
    print("------")

openai_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2023-12-01-preview"
)

while True:
    question = input("\n❓ 질문을 입력하세요 (종료하려면 'exit' 또는 'quit' 입력): ").strip()
    if question.lower() in ("exit", "quit"):
        print("👋 프로그램을 종료합니다.")
        break

    # Azure Search 검색
    results = search_client.search(question)
    docs = [doc["content"] for doc in results][:3]
    context = "\n\n".join(docs)

    # GPT에 전달
    response = openai_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        messages=[
            {"role": "system", "content": "You are an assistant that answers based on the following documents."},
            {"role": "user", "content": f"Document:\n{context}\n\nQuestion: {question}"}
        ]
    )

    print("\n🤖 GPT의 답변:")
    print(response.choices[0].message.content)
