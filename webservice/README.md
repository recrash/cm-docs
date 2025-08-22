# TestscenarioMaker

Git 저장소 변경사항을 분석하여 한국어 테스트 시나리오를 Excel 형식으로 자동 생성하는 AI 기반 도구

## 🚀 프로젝트 개요

TestscenarioMaker는 Git 저장소의 변경사항을 분석하고 AI(LLM)를 활용하여 고품질의 한국어 테스트 시나리오를 자동으로 생성하는 풀스택 웹 애플리케이션입니다. RAG(Retrieval-Augmented Generation) 시스템과 피드백 기반 학습 시스템을 통해 지속적으로 개선되는 테스트 시나리오를 제공합니다.

## ✨ 주요 기능

### 🔍 AI 기반 시나리오 생성
- **Git 분석**: 커밋 메시지 및 코드 diff 자동 추출 및 분석
- **LLM 통합**: Ollama qwen3 모델을 활용한 지능형 시나리오 생성
- **Excel 출력**: 표준화된 테스트 시나리오 템플릿 기반 Excel 파일 생성
- **한국어 특화**: 자연스러운 한국어 테스트 시나리오 생성
- **실시간 진행**: WebSocket 기반 실시간 생성 진행상황 표시

### 🧠 RAG(검색 증강 생성) 시스템
- **벡터 데이터베이스**: ChromaDB를 활용한 지능형 문서 검색
- **한국어 임베딩**: ko-sroberta-multitask 모델 기반 정확한 유사도 검색
- **컨텍스트 향상**: 과거 분석 결과를 활용한 개선된 시나리오 생성
- **다형식 지원**: DOCX, TXT, PDF 문서 자동 인덱싱 및 검색
- **오프라인 지원**: 로컬 임베딩 모델을 통한 폐쇄망 환경 지원

### 📊 피드백 및 분석 시스템
- **사용자 피드백**: 생성된 시나리오에 대한 5점 척도 평가
- **자동 개선**: 피드백 기반 프롬프트 및 생성 품질 최적화
- **분석 대시보드**: 종합적인 통계 분석 및 트렌드 시각화
- **데이터 관리**: 자동 백업, JSON/Excel 내보내기, 요약 보고서 생성
- **데이터 무결성**: SQLite 기반 트랜잭션 처리 및 외래키 제약 조건

### 🌐 현대적인 웹 인터페이스
- **React SPA**: Material-UI 기반 반응형 단일 페이지 애플리케이션
- **실시간 업데이트**: WebSocket을 통한 생성 진행상황 실시간 표시
- **드래그 앤 드롭**: 직관적인 파일 업로드 및 관리
- **모바일 친화적**: 적응형 레이아웃의 반응형 디자인
- **접근성**: WCAG 가이드라인 준수 및 키보드 네비게이션 지원

## 🏗️ 기술 스택

### 프론트엔드
- **React 18** + **TypeScript** - 현대적인 UI 개발
- **Material-UI (MUI)** - 일관된 디자인 시스템
- **Vite** - 빠른 개발 환경 및 빌드 도구
- **Axios** - HTTP 클라이언트 및 API 통신
- **WebSocket** - 실시간 양방향 통신

### 백엔드
- **FastAPI** - 고성능 Python 웹 프레임워크
- **Uvicorn** - ASGI 서버
- **WebSocket** - 실시간 통신 지원
- **SQLite** - 피드백 데이터 저장
- **Pydantic** - 데이터 검증 및 직렬화

### AI/ML
- **Ollama** - 로컬 LLM 실행 환경
- **qwen3:8b** - 메인 생성 모델 (백업: qwen3:1.7b)
- **ChromaDB** - 벡터 데이터베이스
- **sentence-transformers** - 한국어 텍스트 임베딩
- **ko-sroberta-multitask** - 한국어 특화 임베딩 모델

### 개발 도구
- **Vitest** - 프론트엔드 유닛 테스트 (Vite 네이티브)
- **Playwright** - E2E 테스트 및 브라우저 자동화
- **pytest** - 백엔드 API 테스트
- **ESLint** + **TypeScript** - 코드 품질 관리

## 📋 시스템 요구사항

- **Python**: 3.8 이상
- **Node.js**: 16 이상
- **Ollama**: qwen3:8b 모델 설치
- **Git**: 2.0 이상 (저장소 분석용)
- **메모리**: 최소 8GB RAM (qwen3:8b 모델 실행용)
- **저장공간**: 최소 2GB (모델 및 의존성 포함)

## 🚀 빠른 시작

### 1. 저장소 클론 및 설정
```bash
git clone <repository-url>
cd TestscenarioMaker

# 설정 파일 생성
cp config.example.json config.json
```

### 2. 백엔드 설정
```bash
# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 3. 프론트엔드 설정
```bash
# Node.js 의존성 설치
npm install
```

### 4. Ollama 설정
```bash
# Ollama 설치 (https://ollama.com)
# qwen3 모델 다운로드
ollama pull qwen3:8b
# 또는 경량 모델
ollama pull qwen3:1.7b
```

### 5. 한국어 임베딩 모델 다운로드
```bash
# 온라인 환경
python scripts/download_embedding_model.py

# 모델이 ./models/ko-sroberta-multitask/ 에 다운로드됩니다
```

### 6. 애플리케이션 실행

#### 개발 모드
```bash
# 터미널 1: 백엔드 서버 (포트 8000)
cd backend
python -m uvicorn main:app --reload --port 8000

# 터미널 2: 프론트엔드 서버 (포트 3000)
npm run dev
```

#### 웹 인터페이스 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API 문서**: http://localhost:8000/docs
- **API 대안 문서**: http://localhost:8000/redoc

## 🧪 테스트 실행

### 전체 테스트 스위트
```bash
npm run test:all
```

### 개별 테스트
```bash
# 프론트엔드 유닛 테스트
npm run test
npm run test:watch
npm run test:coverage

# E2E 테스트 (기능 검증 필수)
npm run test:e2e
npm run test:e2e:ui
npm run test:e2e:report

# 백엔드 API 테스트
npm run test:api
pytest tests/api/ -v

# 커버리지 리포트
pytest --cov=src --cov-report=html --cov-report=term
```

### 특정 테스트 파일
```bash
pytest tests/api/test_scenario_api.py -v
pytest tests/unit/test_git_analyzer.py::test_function_name -v
```

## 📁 프로젝트 구조

```
TestscenarioMaker/
├── 🌐 frontend/src/                 # React 프론트엔드
│   ├── components/                  # 재사용 가능한 UI 컴포넌트
│   │   ├── ScenarioGenerationTab.tsx    # 시나리오 생성 인터페이스
│   │   ├── ScenarioResultViewer.tsx     # 결과 표시 및 다운로드
│   │   ├── FeedbackModal.tsx            # 피드백 수집
│   │   ├── RAGSystemPanel.tsx           # RAG 시스템 관리
│   │   ├── FeedbackAnalysisTab.tsx      # 피드백 분석 대시보드
│   │   └── BackupFileManagementModal.tsx # 백업 파일 관리
│   ├── services/api.ts              # API 클라이언트
│   ├── utils/websocket.ts           # WebSocket 연결 관리
│   └── types/index.ts               # TypeScript 타입 정의
├── ⚙️ backend/                      # FastAPI 백엔드
│   ├── main.py                      # 애플리케이션 진입점
│   ├── routers/                     # API 라우터 모듈
│   │   ├── scenario.py              # 시나리오 생성 + WebSocket
│   │   ├── feedback.py              # 피드백 수집 및 분석
│   │   ├── rag.py                   # RAG 시스템 관리
│   │   ├── files.py                 # 파일 업로드/다운로드
│   │   └── logging.py               # 로깅 시스템
│   └── models/                      # Pydantic 모델
├── 🧠 src/                          # 핵심 비즈니스 로직
│   ├── git_analyzer.py              # Git 분석 및 diff 추출
│   ├── llm_handler.py               # Ollama LLM 통합
│   ├── excel_writer.py              # Excel 템플릿 기반 생성
│   ├── feedback_manager.py          # 피드백 데이터 관리
│   ├── config_loader.py             # 설정 파일 로더
│   ├── logging_config.py            # 구조화된 로깅
│   └── vector_db/                   # RAG 시스템
│       ├── rag_manager.py           # RAG 오케스트레이션
│       ├── chroma_manager.py        # ChromaDB 관리
│       ├── document_chunker.py      # 문서 청킹
│       └── document_indexer.py      # 문서 인덱싱
├── 🧪 tests/                        # 테스트 스위트
│   ├── unit/                        # 유닛 테스트
│   ├── api/                         # API 테스트
│   ├── e2e/                         # E2E 테스트
│   └── integration/                 # 통합 테스트
├── 📊 templates/template.xlsx       # Excel 템플릿
├── 📂 outputs/                      # 생성된 Excel 파일
├── 📚 models/ko-sroberta-multitask/ # 한국어 임베딩 모델
├── 🗄️ logs/                         # 구조화된 로그 파일
└── 📄 documents/                    # RAG 시스템용 문서
```

## ⚙️ 설정

### config.json 주요 설정
```json
{
    "model_name": "qwen3:8b",
    "timeout": 600,
    "documents_folder": "documents",
    "rag": {
        "enabled": true,
        "persist_directory": "vector_db_data",
        "embedding_model": "jhgan/ko-sroberta-multitask",
        "local_embedding_model_path": "./models/ko-sroberta-multitask",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "search_k": 5
    }
}
```

### 환경변수
```bash
# Python 모듈 경로 (필수)
export PYTHONPATH=$(pwd):$PYTHONPATH

# Node.js 경고 비활성화 (선택)
export NODE_OPTIONS="--no-deprecation"
```

## 🔧 주요 API 엔드포인트

### 시나리오 생성
- `ws://localhost:8000/api/scenario/generate-ws` - WebSocket 기반 시나리오 생성

### 파일 관리
- `POST /api/files/validate/repo-path` - Git 저장소 경로 검증
- `GET /api/files/download/excel/{filename}` - Excel 파일 다운로드

### RAG 시스템
- `POST /api/rag/index` - 문서 인덱싱
- `GET /api/rag/status` - RAG 시스템 상태 조회

### 피드백 시스템
- `POST /api/feedback/submit` - 피드백 제출
- `GET /api/feedback/analysis` - 피드백 분석 데이터
- `GET /api/feedback/export` - 피드백 데이터 내보내기

### 시스템
- `GET /api/health` - 헬스체크
- `GET /api/logs` - 로그 데이터 조회

## 🔄 실시간 시나리오 생성 워크플로우

1. **저장소 검증**: Git 저장소 경로 유효성 확인
2. **WebSocket 연결**: 실시간 진행상황 스트리밍 연결
3. **Git 분석**: 변경사항 추출 및 구조화 (10% → 20%)
4. **RAG 컨텍스트**: 관련 문서 검색 및 컨텍스트 구성 (30%)
5. **LLM 생성**: AI 모델 기반 시나리오 생성 (80%)
6. **Excel 출력**: 템플릿 기반 Excel 파일 생성 (90%)
7. **완료**: 다운로드 가능한 결과 파일 제공 (100%)

## 🎯 사용 방법

### 1. 기본 시나리오 생성
1. 웹 인터페이스에서 Git 저장소 경로 입력
2. 필요시 성능 모드 선택 (기본: 활성화)
3. "테스트 시나리오 생성" 버튼 클릭
4. 실시간 진행상황 모니터링
5. 완료 후 Excel 파일 다운로드

### 2. RAG 시스템 활용
1. RAG 시스템 패널에서 문서 업로드
2. 자동 인덱싱 완료 확인
3. 시나리오 생성 시 관련 컨텍스트 자동 활용

### 3. 피드백 제공
1. 생성된 결과에서 만족도 평가
2. 구체적인 개선 사항 입력
3. 피드백 제출로 시스템 지속 개선

## 📊 모니터링 및 로깅

### 구조화된 로깅
- **로그 위치**: `logs/YYYYMMDD_[frontend|backend].log`
- **로그 레벨**: DEBUG, INFO, WARNING, ERROR
- **실시간 모니터링**: WebSocket 연결 및 API 호출 추적
- **성능 메트릭**: 응답 시간 및 리소스 사용량 기록

### 로그 조회
```bash
# 실시간 로그 모니터링
tail -f logs/$(date +%Y%m%d)_backend.log
tail -f logs/$(date +%Y%m%d)_frontend.log
```

## 🚨 문제 해결

### 일반적인 문제
- **WebSocket 연결 실패**: 백엔드 서버 포트 8000 실행 상태 확인
- **생성이 0%에서 멈춤**: Ollama 서버 및 모델 가용성 확인
- **한국어 텍스트 깨짐**: UTF-8 인코딩 설정 확인
- **모듈 임포트 오류**: `PYTHONPATH` 환경변수 설정 확인

### 성능 최적화
- qwen3:1.7b 모델 사용으로 메모리 사용량 감소
- RAG 시스템 비활성화로 처리 속도 향상
- 성능 모드 활성화로 빠른 생성

### 서버 관리
```bash
# 개발 서버 중지
./stop-dev.sh

# 헬스체크
curl http://localhost:8000/api/health
```

## 🔒 보안 고려사항

- **입력 검증**: 모든 사용자 입력에 대한 검증 및 정제
- **경로 보안**: 상대 경로만 사용, 디렉터리 순회 공격 방지  
- **CORS 설정**: 개발/운영 환경별 적절한 CORS 정책
- **민감정보 보호**: 로그 및 응답에서 민감정보 마스킹

## 🤝 개발 가이드라인

### 중요 원칙
- **크로스 플랫폼 호환성**: Windows 환경 고려 필수
- **E2E 테스트 필수**: 기능 변경 시 Playwright 테스트 실행
- **기존 기능 보존**: 명확한 지시 없이 기능 삭제 금지
- **한국어 지원**: 모든 사용자 대면 텍스트 한국어 지원

### 개발 워크플로우
1. 기능 브랜치 생성
2. 테스트 기반 개발 (TDD)
3. 모든 테스트 스위트 통과 확인
4. 코드 리뷰 및 품질 검사
5. 문서 업데이트

## 📈 로드맵

### 단기 계획
- [ ] 추가 LLM 모델 지원 (Claude, GPT 등)
- [ ] 시나리오 템플릿 커스터마이제이션
- [ ] 배치 처리 기능

### 중기 계획
- [ ] 다국어 지원 확장
- [ ] 클라우드 배포 지원
- [ ] API 키 기반 외부 LLM 통합

### 장기 계획
- [ ] 기업용 SSO 통합
- [ ] 고급 분석 및 리포팅
- [ ] AI 모델 파인튜닝 지원

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🙋‍♂️ 지원 및 기여

- **이슈 리포팅**: GitHub Issues를 통한 버그 신고 및 기능 요청
- **기여 방법**: Pull Request를 통한 코드 기여 환영
- **문서 개선**: 문서 개선 및 번역 기여 환영

---

**TestscenarioMaker** - AI 기반 지능형 테스트 시나리오 자동 생성 도구