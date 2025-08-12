# TestscenarioMaker 모노레포

Git 저장소 변경사항을 분석하여 한국어 테스트 시나리오를 자동 생성하는 AI 기반 통합 솔루션

## 🌟 프로젝트 개요

이 모노레포는 TestscenarioMaker 생태계의 두 가지 주요 컴포넌트를 통합합니다:

- **Backend (웹 서비스)**: Pseudo-MSA 아키텍처 기반의 풀스택 웹 애플리케이션
- **CLI (명령줄 도구)**: 브라우저 통합 및 URL 프로토콜을 지원하는 크로스플랫폼 CLI 도구

두 프로젝트는 독립적으로 개발되고 배포되지만, 공통된 목표를 가지고 상호 보완적으로 작동합니다.

## 📁 프로젝트 구조

```
testscenario-monorepo/
├── backend/              # TestscenarioMaker 웹 서비스
│   ├── frontend/         # React + TypeScript 프론트엔드
│   ├── backend/          # FastAPI 백엔드 서비스
│   ├── src/             # 핵심 분석 모듈
│   └── tests/           # 테스트 슈트 (E2E, API, 단위)
├── cli/                 # TestscenarioMaker CLI 도구
│   ├── src/ts_cli/      # CLI 핵심 로직
│   ├── scripts/         # 빌드 및 배포 스크립트
│   └── tests/           # CLI 테스트 슈트
├── README.md            # 통합 프로젝트 문서
└── pyproject.toml       # 공통 개발 환경 설정
```

## 🎯 Backend - TestscenarioMaker 웹 서비스

### 기술 스택
- **프론트엔드**: React 18 + TypeScript + Material-UI + Vite
- **백엔드**: FastAPI + Python (Pseudo-MSA 아키텍처)
- **AI/LLM**: Ollama 통합 (qwen3:8b 모델)
- **벡터 DB**: ChromaDB (RAG 시스템)
- **테스팅**: Jest + Playwright (E2E) + pytest (API)

### 주요 기능

#### 🧠 AI 기반 시나리오 생성
- Git 커밋 메시지 및 코드 diff 자동 분석
- Ollama qwen3 모델을 활용한 지능형 시나리오 생성
- 표준화된 Excel 템플릿 기반 테스트 시나리오 출력
- WebSocket 기반 실시간 생성 진행상황 표시

#### 🔍 RAG(검색 증강 생성) 시스템
- ChromaDB를 활용한 벡터 기반 문서 검색
- ko-sroberta-multitask 모델 기반 한국어 임베딩
- DOCX, TXT, PDF 문서 자동 인덱싱
- 오프라인 환경 지원을 위한 로컬 임베딩 모델

#### 📊 피드백 및 분석 시스템
- 5점 척도 사용자 피드백 수집
- 피드백 기반 자동 품질 개선
- 종합적인 분석 대시보드 및 트렌드 시각화
- SQLite 기반 데이터 무결성 보장

### 개발 환경 설정

```bash
# Backend 디렉토리로 이동
cd backend

# 의존성 설치
pip install -r requirements.txt
npm install

# 백엔드 서버 시작 (포트 8000)
cd backend && python -m uvicorn main:app --reload --port 8000

# 프론트엔드 개발 서버 시작 (포트 3000)
npm run dev

# 전체 테스트 실행
npm run test:all
```

### 테스팅
- **E2E 테스트**: `npm run test:e2e` (Playwright 필수)
- **API 테스트**: `npm run test:api` (pytest)
- **프론트엔드 테스트**: `npm run test` (Jest)

## ⚡ CLI - TestscenarioMaker 명령줄 도구

### 기술 스택
- **코어**: Python 3.8+ + Click + Rich
- **네트워킹**: httpx + tenacity (재시도 로직)
- **빌드**: PyInstaller (크로스플랫폼 실행파일)
- **테스팅**: pytest (단위/통합/E2E)

### 주요 기능

#### 🔧 로컬 저장소 분석
- Git 저장소 변경사항 자동 분석
- 브랜치 간 차이점 비교 (기본: origin/develop → HEAD)
- 작업 중인 변경사항 포함 분석

#### 🌐 브라우저 통합
- `testscenariomaker://` 커스텀 URL 프로토콜 지원
- 크로스플랫폼 URL 프로토콜 자동 등록
- macOS 전용 헬퍼 앱으로 브라우저 샌드박스 제약 우회

#### 🎨 사용자 경험
- 한국어 사용자 인터페이스
- Rich 라이브러리 기반 향상된 콘솔 출력
- JSON 및 텍스트 형식 출력 지원

### 설치 및 사용

#### 사전 빌드된 실행파일 사용
```bash
# Windows: TestscenarioMaker-CLI-Setup.exe 설치
# macOS: .dmg 파일 설치 (헬퍼 앱 포함)
# Linux: AppImage 또는 직접 빌드
```

#### 소스코드에서 개발 설치
```bash
# CLI 디렉토리로 이동
cd cli

# 개발 모드 설치
pip install -e .

# CLI 실행
ts-cli analyze /path/to/repository
```

#### 빌드
```bash
cd cli

# 크로스플랫폼 실행파일 빌드
python scripts/build.py

# Windows 설치 프로그램 생성 (Windows에서)
makensis scripts/setup_win.nsi

# macOS DMG 및 헬퍼 앱 생성 (macOS에서)
python scripts/create_dmg.py
```

### 테스팅
```bash
cd cli

# 전체 테스트 슈트
pytest --cov=ts_cli --cov-report=html

# 테스트 유형별 실행
pytest -m unit          # 단위 테스트
pytest -m integration   # 통합 테스트  
pytest -m e2e           # End-to-End 테스트
```

## 🛠 공통 개발 환경

### 의존성 관리
- **Backend**: `backend/requirements.txt` + `backend/package.json`
- **CLI**: `cli/requirements.txt` + `cli/requirements-dev.txt`
- **공통**: 루트 `pyproject.toml` (개발 도구 설정)

### 코드 품질
```bash
# 코드 포맷팅 (프로젝트 루트에서)
black backend/src backend/backend cli/src cli/tests
isort backend/src backend/backend cli/src cli/tests

# 린팅
flake8 backend/src backend/backend cli/src cli/tests

# 타입 체크
mypy backend/src cli/src
```

### Git 관리
이 모노레포는 Git subtree를 사용하여 구성되었습니다:

```bash
# 서브트리 업데이트 (필요시)
git subtree pull --prefix=backend https://github.com/recrash/TestscenarioMaker.git main --squash
git subtree pull --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main --squash

# 서브트리 푸시 (필요시)
git subtree push --prefix=backend https://github.com/recrash/TestscenarioMaker.git main
git subtree push --prefix=cli https://github.com/recrash/TestscenarioMaker-CLI.git main
```

## 🚀 배포 및 CI/CD

### 독립적인 배포 파이프라인
각 서브프로젝트는 독립적인 CI/CD 파이프라인을 가집니다:

- **Backend**: Pseudo-MSA 서비스별 독립 배포
  - API 테스트, E2E 테스트, 서비스별 배포 검증
  - WebSocket 연결 및 실시간 기능 검증

- **CLI**: 크로스플랫폼 패키지 및 설치 프로그램 빌드
  - Windows 설치 프로그램 (.exe)
  - macOS 디스크 이미지 (.dmg) + 헬퍼 앱
  - Linux AppImage 또는 패키지

### 환경별 배포
```bash
# Backend 프로덕션 배포
cd backend
export PYTHONPATH=$(pwd):$PYTHONPATH
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# CLI 배포 버전 생성
cd cli
python scripts/build.py
```

## 📊 품질 보증

### 테스트 커버리지 목표
- **Backend**: ≥80% 단위 테스트, ≥70% 통합 테스트
- **CLI**: ≥85% 전체 커버리지
- **E2E**: 주요 사용자 워크플로우 100% 커버

### 성능 기준
- **Backend API**: 응답시간 <200ms, WebSocket 연결 <1초
- **CLI**: 저장소 분석 <30초, URL 프로토콜 처리 <5초
- **빌드**: 전체 빌드 시간 <10분

## 🤝 기여 가이드라인

### 개발 워크플로우
1. 해당 서브프로젝트 디렉토리에서 작업
2. 독립적인 테스트 슈트 실행 및 통과 확인
3. 코드 품질 도구 실행 (black, isort, flake8)
4. 커밋 메시지는 서브프로젝트 접두어 사용: `[backend]` 또는 `[cli]`

### 이슈 및 PR
- 서브프로젝트별로 라벨링: `backend`, `cli`, `monorepo`
- 독립적인 CI/CD 파이프라인 고려사항 명시
- 크로스플랫폼 호환성 검증 필수

## 📝 라이선스

MIT License - 각 서브프로젝트의 라이선스 파일 참조

## 🔗 관련 링크

- **Backend Documentation**: [backend/README.md](backend/README.md)
- **CLI Documentation**: [cli/README.md](cli/README.md)
- **Backend CLAUDE.md**: [backend/CLAUDE.md](backend/CLAUDE.md)
- **CLI CLAUDE.md**: [cli/CLAUDE.md](cli/CLAUDE.md)

---

각 서브프로젝트는 독립적으로 개발되고 배포되며, 이 모노레포는 통합된 이슈 트래킹과 개발 환경을 제공합니다.