# TestscenarioMaker

Git 저장소 변경사항을 분석하여 한국어 테스트 시나리오를 Excel 형식으로 자동 생성하는 AI 기반 도구입니다.

## 📋 프로젝트 개요

TestscenarioMaker는 Git 저장소 변경사항을 분석하고 AI를 사용하여 고품질의 한국어 테스트 시나리오를 자동으로 생성하는 풀스택 애플리케이션입니다. 이 프로젝트는 현대적인 React 프론트엔드, FastAPI 백엔드를 특징으로 하며, RAG(Retrieval-Augmented Generation) 기능과 지속적인 개선을 위한 피드백 시스템을 포함합니다.

## 🏗️ 아키텍처

### 풀스택 아키텍처
- **프론트엔드**: React 18 + TypeScript + Material-UI + Vite
- **백엔드**: FastAPI + Python (모듈형 라우터)
- **AI/LLM**: Ollama 통합 (qwen3:8b 모델)
- **벡터 데이터베이스**: RAG 시스템을 위한 ChromaDB
- **저장소**: 피드백 데이터용 SQLite, 출력용 Excel 파일
- **테스팅**: Jest + Playwright (E2E) + pytest (백엔드)

### 주요 구성 요소
- **레거시 `src/` 모듈**: 핵심 분석 로직 (git_analyzer, llm_handler, excel_writer 등)
- **백엔드 API**: 시나리오 생성, 피드백, RAG, 파일 관리를 위한 FastAPI 라우터
- **프론트엔드 SPA**: 실시간 WebSocket 업데이트가 있는 React 컴포넌트
- **RAG 시스템**: 컨텍스트 향상 생성을 위한 벡터 데이터베이스 통합

## 🎯 주요 기능

### 🔍 **AI 기반 시나리오 생성**
- **Git 분석**: 커밋 메시지 및 코드 diff 자동 추출
- **LLM 통합**: 지능형 생성을 위한 Ollama 기반 qwen3:8b 모델
- **Excel 출력**: 템플릿이 있는 표준화된 테스트 시나리오 형식
- **한국어 특화**: 자연스러운 한국어 테스트 시나리오 생성
- **실시간 업데이트**: 생성 중 WebSocket 기반 진행률 추적

### 🧠 **RAG (검색 증강 생성) 시스템**
- **벡터 데이터베이스**: 지능형 문서 검색을 위한 ChromaDB
- **한국어 임베딩**: 정확한 유사도 검색을 위한 ko-sroberta-multitask 모델
- **컨텍스트 향상**: 개선된 시나리오 생성을 위한 과거 분석 결과
- **문서 인덱싱**: 다양한 형식(DOCX, TXT, PDF)의 자동 처리
- **동적 컨텍스트**: 생성 중 관련 과거 데이터 검색

### 📊 **피드백 시스템**
- **사용자 평가**: 생성된 시나리오에 대한 5점 척도 평가 시스템
- **자동 개선**: 피드백 기반 프롬프트 최적화
- **분석 대시보드**: 통계 분석 및 개선 패턴 시각화
- **백업 시스템**: 데이터 안전을 위한 자동 데이터 백업
- **내보내기 기능**: 피드백 데이터의 JSON 및 Excel 내보내기

### 🌐 **현대적인 웹 인터페이스**
- **React SPA**: Material-UI 컴포넌트가 있는 단일 페이지 애플리케이션
- **실시간 진행률**: 라이브 생성 업데이트를 위한 WebSocket 통합
- **파일 관리**: 드래그 앤 드롭 파일 업로드 및 다운로드 기능
- **반응형 디자인**: 적응형 레이아웃이 있는 모바일 친화적 인터페이스
- **오류 처리**: 사용자 친화적 메시지가 있는 포괄적인 오류 처리

### 🧪 **포괄적인 테스팅**
- **단위 테스팅**: Testing Library가 있는 Jest 기반 프론트엔드 테스트
- **API 테스팅**: 모의 지원이 있는 pytest 기반 백엔드 API 테스트
- **E2E 테스팅**: 브라우저 간 Playwright 기반 엔드투엔드 테스트
- **통합 테스팅**: 데이터베이스 격리가 있는 전체 워크플로우 테스트

## 🚀 빠른 시작

### 사전 요구사항
- **Python 3.8+** (pip 포함)
- **Node.js 16+** (npm 포함)
- **Ollama** (qwen3:8b 모델 설치됨)
- **Git** (저장소 분석용)

### 설치

1. **저장소 클론**:
   ```bash
   git clone <repository-url>
   cd TestscenarioMaker
   ```

2. **백엔드 설정**:
   ```bash
   # Python 의존성 설치
   pip install -r requirements.txt
   
   # 설정 구성
   cp config.example.json config.json
   # config.json을 설정에 맞게 편집
   ```

3. **프론트엔드 설정**:
   ```bash
   # Node.js 의존성 설치
   npm install
   ```

4. **한국어 임베딩 모델 다운로드**:
   ```bash
   python scripts/download_embedding_model.py
   ```

### 애플리케이션 실행

#### 개발 모드

1. **백엔드 서버 시작** (포트 8000):
   ```bash
   cd backend
   python -m uvicorn main:app --reload --port 8000
   ```

2. **프론트엔드 서버 시작** (포트 3000):
   ```bash
   npm run dev
   ```

3. **애플리케이션 접속**:
   - 프론트엔드: http://localhost:3000
   - 백엔드 API: http://localhost:8000
   - API 문서: http://localhost:8000/docs

#### 프로덕션 모드

```bash
# 프론트엔드 빌드
npm run build

# 프로덕션 서버 시작
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 서버 관리

```bash
# 모든 서버 중지
./stop-dev.sh
```

**⚠️ 중요**: `./start-dev.sh`를 사용하지 마세요 - 위에서 보여준 대로 수동으로 서버를 시작하세요.

## 📁 프로젝트 구조

```
TestscenarioMaker/
├── frontend/src/                    # React 프론트엔드
│   ├── components/                  # 재사용 가능한 UI 컴포넌트
│   │   ├── ScenarioGenerationTab.tsx
│   │   ├── ScenarioResultViewer.tsx
│   │   ├── FeedbackModal.tsx
│   │   ├── RAGSystemPanel.tsx
│   │   └── FeedbackAnalysisTab.tsx
│   ├── services/api.ts              # Axios 기반 API 클라이언트
│   ├── types/index.ts               # TypeScript 정의
│   └── utils/websocket.ts           # WebSocket 연결 처리
├── backend/                         # FastAPI 백엔드
│   ├── main.py                      # FastAPI 앱 초기화
│   ├── routers/                     # API 엔드포인트 모듈
│   │   ├── scenario.py              # 생성 엔드포인트 + WebSocket
│   │   ├── feedback.py              # 피드백 수집 및 분석
│   │   ├── rag.py                   # RAG 시스템 관리
│   │   └── files.py                 # 파일 업로드/다운로드/검증
│   └── models/                      # Pydantic 응답 모델
├── src/                             # 레거시 핵심 모듈
│   ├── git_analyzer.py              # Git diff 추출 및 분석
│   ├── llm_handler.py               # Ollama LLM 통합
│   ├── excel_writer.py              # 템플릿 기반 Excel 생성
│   ├── feedback_manager.py          # SQLite 기반 피드백 저장소
│   └── vector_db/                   # ChromaDB가 있는 RAG 시스템
├── tests/                           # 테스트 스위트
│   ├── unit/                        # 단위 테스트
│   ├── api/                         # API 테스트
│   ├── e2e/                         # 엔드투엔드 테스트
│   └── integration/                 # 통합 테스트
├── templates/                       # Excel 템플릿
├── outputs/                         # 생성된 Excel 파일
├── documents/                       # RAG용 샘플 문서
└── config.json                      # 애플리케이션 설정
```

## 🧪 테스팅

### 테스트 실행

```bash
# 프론트엔드 단위 테스트
npm run test
npm run test:watch
npm run test:coverage

# E2E 테스트 (기능 테스팅에 필수)
npm run test:e2e
npm run test:e2e:ui

# 백엔드 API 테스트
npm run test:api
# 또는: pytest tests/api/

# 모든 테스트
npm run test:all
```

### 테스트 커버리지
- **단위 테스트**: React 컴포넌트, 핵심 비즈니스 로직
- **API 테스트**: 모의 의존성이 있는 모든 FastAPI 엔드포인트
- **E2E 테스트**: 파일 다운로드를 포함한 완전한 사용자 워크플로우
- **통합 테스트**: 데이터베이스 작업이 있는 전체 시스템 워크플로우

## ⚙️ 설정

### config.json
```json
{
    "ollama_base_url": "http://localhost:11434",
    "model_name": "qwen3:8b",
    "timeout_seconds": 600,
    "max_tokens": 4000,
    "temperature": 0.7,
    "rag_enabled": true,
    "feedback_enabled": true
}
```

### 환경 변수
- `NODE_OPTIONS="--no-deprecation"`: Node.js 경고 억제
- `PYTHONPATH`: 모듈 임포트를 위해 프로젝트 루트로 설정

## 🔄 API 통합

### WebSocket 시나리오 생성
1. 프론트엔드가 `ws://localhost:8000/api/scenario/generate-ws`에 연결
2. 실시간 진행률 업데이트: 10% → 20% → 30% → 80% → 90% → 100%
3. 각 진행 단계에는 설명 메시지가 포함됨
4. 최종 결과에는 메타데이터와 Excel 파일명이 포함됨

### 파일 관리
- Excel 파일이 `outputs/` 디렉토리에 생성됨
- `/api/files/download/excel/{filename}`을 통해 다운로드
- UTF-8 인코딩으로 한국어 파일명 지원
- Excel 파일에 대한 적절한 MIME 타입 처리

### RAG 시스템 통합
- `/api/rag/index`를 통한 문서 인덱싱
- `/api/rag/status`를 통한 상태 모니터링
- 시나리오 생성에 통합된 컨텍스트 검색
- 특화된 임베딩으로 한국어 텍스트 처리

## 🛠️ 개발 가이드라인

### 중요한 원칙
- **크로스 플랫폼 호환성**: 상대 경로만 사용 - 프로젝트가 Windows에서 빌드되어야 함
- **E2E 테스팅 필수**: 기능 테스팅 시 항상 Playwright를 사용하여 E2E 테스트 수행
- **명확한 지시가 없으면 기존 기능을 삭제하지 말 것**
- **경로 관리**: `pathlib.Path`와 상대 경로 사용

### WebSocket 구현
- 백엔드는 직렬화를 위해 `progress.model_dump()` + `json.dumps()` 사용
- 프론트엔드는 환경에 맞게 WebSocket URL 조정
- 연결 관리자가 중복 연결 해제 오류 방지
- 진행률 지연으로 각 단계의 사용자 가시성 보장

### 오류 처리
- **백엔드**: 상세한 메시지가 있는 FastAPI HTTPException
- **프론트엔드**: 사용자 친화적 알림이 있는 Try-catch
- **WebSocket**: 재연결 로직이 있는 전용 오류 콜백

## 📊 성능 및 모니터링

### 성능 지표
- **로드 시간**: 3G에서 <3초, WiFi에서 <1초
- **번들 크기**: 초기 <500KB, 전체 <2MB
- **API 응답**: 표준 작업에 <200ms
- **생성 시간**: 완전한 시나리오에 ~30-60초

### 모니터링
- 실시간 WebSocket 진행률 추적
- 구조화된 형식의 오류 로깅
- 성능 지표 수집
- 사용자 피드백 분석

## 🔒 보안

- **입력 검증**: 모든 사용자 입력 검증 및 정제
- **경로 보안**: 상대 경로만, 디렉토리 순회 없음
- **CORS 구성**: 개발/프로덕션을 위한 적절한 CORS 설정
- **오류 처리**: 오류 메시지에 민감한 정보 없음

## 🤝 기여하기

1. 저장소 포크
2. 기능 브랜치 생성
3. 적절한 테스트와 함께 변경사항 작성
4. 모든 테스트 스위트 실행
5. 설명과 함께 풀 리퀘스트 제출

### 개발 워크플로우
- 모든 새로운 프론트엔드 코드에 TypeScript 사용
- 기존 코드 패턴 및 규칙 따르기
- 새 기능에 대한 테스트 추가
- 필요에 따라 문서 업데이트

## 📝 마이그레이션 노트

이 프로젝트는 Streamlit에서 React+FastAPI 아키텍처로 성공적으로 마이그레이션되었습니다:
- ✅ 웹 인터페이스가 Streamlit에서 React SPA로 이동
- ✅ API 엔드포인트가 FastAPI 백엔드로 중앙화
- ✅ Streamlit rerun 대신 WebSocket을 통한 실시간 업데이트
- ✅ E2E 커버리지가 있는 향상된 테스팅 아키텍처
- ✅ 개선된 파일 관리 및 다운로드 시스템
- ✅ 레거시 Streamlit 파일 제거 (app.py, main.py, app_streamlit_backup.py)

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 라이선스됩니다 - 자세한 내용은 LICENSE 파일을 참조하세요.

## 🆘 문제 해결

### 일반적인 문제
- **WebSocket 연결 실패**: 백엔드 서버가 포트 8000에서 실행 중인지 확인
- **생성이 0%에서 멈춤**: Ollama가 실행 중이고 모델이 사용 가능한지 확인
- **파일 다운로드 문제**: outputs 디렉토리 권한 확인
- **한국어 텍스트 문제**: UTF-8 인코딩이 올바르게 구성되었는지 확인

### 지원
문제와 질문이 있으시면 기존 문서를 확인하거나 저장소에서 이슈를 생성해 주세요.