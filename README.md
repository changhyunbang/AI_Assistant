# 🤖 AI 챗봇 관리 시스템

> Azure Cognitive Search와 OpenAI를 활용한 문서 기반 지능형 챗봇 관리 플랫폼

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![Azure](https://img.shields.io/badge/Azure-Cognitive%20Search-0078d4.svg)](https://azure.microsoft.com/services/search/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-00a67e.svg)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 프로젝트 개요

AI 챗봇 관리 시스템은 기업이나 조직에서 여러 개의 문서 기반 AI 챗봇을 중앙에서 효율적으로 관리할 수 있도록 하는 통합 플랫폼입니다. Azure 클라우드 서비스와 OpenAI의 최신 언어 모델을 활용하여 고품질의 문서 검색 및 자연어 처리 기능을 제공합니다.

## 🎬 데모 영상
<video width="600" controls>
  <source src="./streamlit-admin_chatbot-2025-08-07-11-08-51.webm" type="video/webm">
  <p>WebM 비디오를 지원하지 않는 브라우저입니다.</p>
</video>

## ✨ 주요 기능

### 🎛️ 관리자 기능
| 기능 | 설명 |
|-----|------|
| 🤖 **멀티 챗봇 관리** | 여러 챗봇을 중앙에서 생성, 수정, 삭제 | 
| 📁 **파일 업로드** | 드래그 앤 드롭으로 다중 파일 업로드 | 
| 🔄 **자동 인덱싱** | 업로드된 문서의 자동 인덱스 생성 | 
| 📊 **실시간 모니터링** | 챗봇 상태 및 문서 수 실시간 확인 |
| 🗑️ **데이터 관리** | 챗봇 및 문서 삭제 기능 | 

### 💬 챗봇 기능
| 기능 | 설명 | 기술 스택 |
|-----|------|---------|
| 🔍 **지능형 검색** | 의미론적 문서 검색 | Azure Cognitive Search |
| 🤖 **자연어 처리** | GPT 기반 자연스러운 대화 | OpenAI GPT-4 |
| 📋 **출처 표시** | 답변의 근거가 된 문서 표시 | Custom Logic |
| 💾 **세션 관리** | 챗봇별 독립적인 대화 기록 | Streamlit Session |
| 🎨 **반응형 UI** | 모바일/데스크톱 최적화 | Streamlit + CSS |

### 🔧 기술적 특징
| 특징 | 구현 방식 | 장점 |
|-----|----------|------|
| 📄 **OCR 지원** | Azure Vision API | 이미지/PDF 텍스트 추출 |
| 🔄 **실시간 업데이트** | Streamlit 리렌더링 | 즉시 반영되는 변경사항 |
| 🎯 **정확성** | RAG 패턴 구현 | 문서 기반 정확한 답변 |

### 📋 시스템 요구사항
- **Python**: 3.8 이상
- **메모리**: 최소 4GB RAM
- **저장공간**: 최소 2GB 여유공간
- **Azure 계정**: Storage, Cognitive Search, OpenAI 서비스 필요

### 1️⃣ 저장소 클론
```bash
git clone https://github.com/changhyunbang/AI_Assistant).git
```

🌐 브라우저에서 `https://skan-webapp-002-d5ajcxbfgnhgehbb.westus-01.azurewebsites.net`로 접속

## 🚀 사용법

### 📝 단계별 가이드

#### 1단계: 챗봇 등록
1. **➕ 챗봇 등록** 탭 클릭
2. 챗봇 이름 입력 (예: "고객지원봇")
3. 폴더명 입력 (선택사항)
4. 설명 입력 (선택사항)
5. **🚀 챗봇 등록** 버튼 클릭

#### 2단계: 문서 업로드
1. **📋 챗봇 목록**에서 등록한 챗봇 찾기
2. **📁 파일 등록** 버튼 클릭
3. 파일 선택 (PDF, DOC, TXT 등)
4. **🚀 업로드 시작** 버튼 클릭

#### 3단계: 인덱스 생성
1. 파일 업로드 완료 후 **🔄 인덱스 갱신** 버튼 클릭
2. 인덱스 생성 과정 확인
3. **✅ 인덱스 완료** 상태 확인

#### 4단계: 챗봇 실행
1. **🚀 실행** 버튼 클릭
2. 새 탭에서 챗봇 인터페이스 열림
3. 질문 입력 후 **전송 📤** 버튼 클릭

## 📁 프로젝트 구조

```
ai-chatbot-management/
├── 📄 admin_chatbot.py          # 🎛️ 메인 관리자 애플리케이션
├── 📄 azure_blob_utils.py       # ☁️ Azure Storage 유틸리티
├── 📄 chatbot_popup.py          # 💬 챗봇 대화 인터페이스
├── 📄 database_utils.py         # 💾 SQLite 데이터베이스 관리
├── 📄 create_index_claud.py     # 🔍 Azure Search 인덱스 생성
├── 📄 requirements.txt          # 📦 Python 의존성 목록
├── 📄 .env\                     # 🔧 환경 변수 템플릿
├── 📂 chatbots.db               # SQLite 데이터베이스 파일
└── 📄 README.md                 # 📚 프로젝트 문서 (현재 파일)
```

### 🔍 주요 파일 설명

| 파일명 | 역할 | 주요 기능 |
|-------|------|----------|
| `admin_chatbot.py` | 메인 앱 | 챗봇 관리, UI 제어, 라우팅 |
| `azure_blob_utils.py` | 클라우드 연동 | 파일 업로드, 다운로드, 목록 조회 |
| `chatbot_popup.py` | 챗봇 UI | 사용자 대화 인터페이스 |
| `database_utils.py` | 데이터 관리 | CRUD 작업, 스키마 관리 |
| `create_index_claud.py` | 검색 엔진 | 문서 인덱싱, 검색 최적화 |

### 📅 현재 버전 (v1.0)
- ✅ 기본 챗봇 관리 기능
- ✅ 파일 업로드 및 인덱싱
- ✅ 실시간 채팅 인터페이스
- ✅ 다중 파일 형식 지원

</div>
