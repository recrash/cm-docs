# TestscenarioMaker

Git 변경 내역을 분석하여 자동으로 테스트 시나리오를 생성하는 AI 기반 도구입니다.

## 📋 프로젝트 개요

TestscenarioMaker는 Git 저장소의 변경 내역을 분석하여 AI 기반으로 한국어 테스트 시나리오를 자동 생성하는 도구입니다. Ollama LLM, RAG(Retrieval-Augmented Generation) 시스템, 피드백 기반 자동 개선 기능을 통해 고품질의 테스트 시나리오를 Excel 형태로 제공합니다.

## 🎯 주요 기능

### 🔍 **AI 기반 시나리오 생성**
- **Git 변경 내역 분석**: 커밋 메시지와 코드 diff를 자동으로 추출
- **LLM 기반 시나리오 생성**: Ollama를 통한 qwen3:8b 모델 활용
- **Excel 템플릿 기반 출력**: 표준화된 테스트 시나리오 형식으로 저장
- **한국어 특화**: 한국어 기반의 자연스러운 테스트 시나리오 생성

### 🧠 **RAG (Retrieval-Augmented Generation) 시스템**
- **벡터 데이터베이스**: ChromaDB를 활용한 지능형 문서 검색
- **한국어 임베딩**: ko-sroberta-multitask 모델로 정확한 유사도 검색
- **컨텍스트 제공**: 과거 분석 결과를 활용한 향상된 시나리오 생성
- **문서 인덱싱**: 다양한 형식(DOCX, TXT, PDF)의 문서 자동 처리

### 📊 **피드백 시스템**
- **사용자 평가**: 생성된 시나리오에 대한 5점 척도 평가
- **자동 개선**: 피드백 데이터를 활용한 프롬프트 자동 최적화
- **분석 대시보드**: 피드백 통계 및 개선 패턴 시각화
- **백업 시스템**: 데이터 안전성을 위한 자동 백업 기능

### 🧪 **테스트 프레임워크**
- **pytest 기반**: 단위 테스트 및 통합 테스트 지원
- **Mock 아키텍처**: 외부 의존성 격리를 통한 안정적인 테스트
- **코드 커버리지**: 테스트 커버리지 측정 및 리포트 생성
- **CI/CD 지원**: 자동화된 테스트 실행 환경

## 🏗️ 프로젝트 구조

```
TestscenarioMaker/
├── 📂 src/                     # 핵심 로직 모듈
│   ├── git_analyzer.py         # Git 변경 내역 분석
│   ├── llm_handler.py          # Ollama LLM 호출
│   ├── excel_writer.py         # 엑셀 파일 생성
│   ├── config_loader.py        # 설정 파일 로더
│   ├── document_parser.py      # 문서 파싱 (변경관리요청서)
│   ├── feedback_manager.py     # 피드백 수집 및 관리
│   ├── prompt_enhancer.py      # 피드백 기반 프롬프트 개선
│   ├── prompt_loader.py        # 프롬프트 로딩 및 RAG 통합
│   └── 📂 vector_db/           # RAG 시스템 모듈
│       ├── chroma_manager.py   # ChromaDB 관리
│       ├── document_chunker.py # 문서 청킹
│       ├── document_indexer.py # 문서 인덱싱
│       ├── document_reader.py  # 문서 읽기
│       └── rag_manager.py      # RAG 시스템 관리
├── 📂 scripts/                 # 유틸리티 스크립트
│   └── download_embedding_model.py  # 임베딩 모델 다운로드 도구
├── 📂 models/                  # 한국어 임베딩 모델 (로컬 설치)
│   └── ko-sroberta-multitask/  # sentence-transformers 모델
├── 📂 tests/                   # 테스트 코드
│   ├── conftest.py             # 공유 fixtures
│   ├── 📂 unit/                # 단위 테스트
│   └── 📂 integration/         # 통합 테스트
├── 📂 templates/               # 엑셀 템플릿 파일
│   └── template.xlsx
├── 📂 prompts/                 # LLM 프롬프트 템플릿
│   └── final_prompt.txt
├── 📂 outputs/                 # 생성된 엑셀 파일 저장
├── 📂 backups/                 # 피드백 데이터 백업
├── 📂 documents/               # RAG용 문서 저장
├── 📜 app.py                   # Streamlit 웹 인터페이스
├── 📜 main.py                  # CLI 실행 스크립트
├── 📜 config.example.json      # 설정 파일 예제
├── 📜 pytest.ini              # 테스트 설정
└── 📜 requirements.txt         # Python 의존성
```

## 🚀 설치 및 실행

### 1. 환경 요구사항

- **Python 3.8 이상**
- **Ollama** (로컬 LLM 실행용)
- **Git 저장소 접근 권한**

### 2. 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. 한국어 임베딩 모델 설치

```bash
# RAG 시스템용 한국어 임베딩 모델 다운로드 (약 432MB)
python scripts/download_embedding_model.py
```

> **📝 참고**: 이 단계는 RAG 기능을 사용하려는 경우에만 필요합니다. `config.json`에서 `rag.enabled: false`로 설정하면 모델 없이도 기본 기능을 사용할 수 있습니다.

### 4. Ollama 설정

```bash
# Ollama 설치 (https://ollama.ai)
# qwen3:8b 모델 다운로드
ollama pull qwen3:8b

# Ollama 서버 시작
ollama serve
```

### 5. 설정 파일 생성

```bash
# 설정 파일 복사 및 수정
cp config.example.json config.json
# config.json에서 repo_path 등을 실제 환경에 맞게 수정
```

### 6. 실행 방법

#### 웹 인터페이스 (권장)
```bash
# Streamlit 웹 애플리케이션 실행
streamlit run app.py
```

#### 명령줄 인터페이스
```bash
# CLI 스크립트 실행
python main.py
```

### 7. 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지 리포트와 함께 실행
pytest --cov=src --cov-report=html

# 단위 테스트만 실행
pytest tests/unit/

# 통합 테스트만 실행
pytest tests/integration/
```

## 📖 사용법

### 웹 인터페이스 사용법

1. **Streamlit 앱 실행**: `streamlit run app.py`
2. **Git 저장소 경로 설정**: 웹 인터페이스에서 경로 입력
3. **RAG 문서 관리**: 
   - `documents/` 폴더에 참고 문서 업로드
   - "문서 인덱싱" 버튼으로 벡터 DB에 저장
4. **시나리오 생성**: "시나리오 생성" 버튼 클릭
5. **결과 확인 및 다운로드**: 생성된 Excel 파일 미리보기 및 다운로드
6. **피드백 제공**: 👍/👎 버튼으로 시나리오 품질 평가
7. **피드백 분석**: "피드백 분석" 탭에서 통계 및 개선 내역 확인

### CLI 사용법

1. **설정 파일 수정**: `config.json`에서 저장소 경로 등 설정
2. **스크립트 실행**: `python main.py`
3. **결과 확인**: `outputs/` 폴더에서 생성된 Excel 파일 확인

### 폐쇄망 환경 설정

TestscenarioMaker는 인터넷 연결이 제한된 폐쇄망 환경에서도 사용 가능합니다.

#### 사전 준비 (인터넷 환경에서)

1. **모델 다운로드**:
   ```bash
   # 한국어 임베딩 모델 다운로드 (약 432MB)
   python scripts/download_embedding_model.py
   ```

2. **파일 복사 준비**:
   ```bash
   # 전체 models/ 폴더를 복사 가능한 형태로 압축
   tar -czf models.tar.gz models/
   ```

#### 폐쇄망 환경 설치

1. **프로젝트 파일 복사**: 전체 프로젝트와 `models.tar.gz` 파일을 폐쇄망으로 이동
2. **모델 파일 압축 해제**:
   ```bash
   tar -xzf models.tar.gz
   ```
3. **설정 파일 수정** (`config.json`):
   ```json
   {
     "rag": {
       "enabled": true,
       "local_embedding_model_path": "./models/ko-sroberta-multitask"
     }
   }
   ```

4. **의존성 설치** (pip wheel 방식):
   ```bash
   # 인터넷 환경에서 wheel 파일 다운로드
   pip download -r requirements.txt -d wheels/
   
   # 폐쇄망에서 wheel 파일로 설치
   pip install --no-index --find-links wheels/ -r requirements.txt
   ```

#### 주의사항
- Ollama 설치는 별도로 필요 (폐쇄망용 Ollama 설치 가이드 참조)
- RAG 기능을 사용하지 않는 경우 `rag.enabled: false` 설정으로 모델 없이 사용 가능

### 고급 설정

#### config.json 주요 옵션
```json
{
  "repo_path": "/path/to/your/git/repo",
  "model_name": "qwen3:8b",
  "timeout": 600,
  "rag": {
    "enabled": true,
    "max_results": 5,
    "similarity_threshold": 0.7
  },
  "performance_mode": false
}
```

#### RAG 시스템 관리
```bash
# SQLite 피드백 DB 확인
sqlite3 feedback.db ".tables"
sqlite3 feedback.db "SELECT * FROM scenario_feedback LIMIT 5;"

# 벡터 DB 상태 확인 (Streamlit UI에서 가능)
```

## 🔧 핵심 모듈 설명

### 🔍 **분석 및 처리 모듈**

#### git_analyzer.py
- Git 저장소의 커밋 메시지와 코드 diff를 추출
- 브랜치 간 비교 분석 지원 (develop ↔ feature)
- 변경 내역을 구조화된 텍스트로 변환
- 공통 조상 커밋 기반 정확한 diff 계산

#### llm_handler.py
- Ollama API를 통한 LLM 호출 관리
- 다양한 모델 지원 (기본: qwen3:8b)
- 타임아웃 및 에러 처리 강화
- JSON 응답 형식 지원

#### excel_writer.py
- LLM 생성 결과를 Excel 템플릿에 매핑
- 한국어 개행 문자 처리 (`\\n` → 실제 개행)
- 테스트 케이스별 상세 정보 저장
- 타임스탬프 기반 파일명 자동 생성

### 🧠 **RAG 시스템 모듈**

#### vector_db/chroma_manager.py
- ChromaDB 벡터 데이터베이스 관리
- 한국어 임베딩 모델 통합
- 문서 저장 및 유사도 검색

#### vector_db/rag_manager.py
- RAG 시스템 통합 관리
- 컨텍스트 검색 및 프롬프트 보강
- 성능 최적화 및 캐싱

#### vector_db/document_chunker.py
- 문서를 의미있는 단위로 분할
- Git 분석 결과 전용 청킹 전략
- 텍스트 오버랩 처리

### 📊 **피드백 시스템**

#### feedback_manager.py
- SQLite 기반 피드백 데이터 관리
- 시나리오 및 개별 테스트 케이스 평가
- 백업 및 복원 시스템
- 통계 분석 및 리포트 생성

#### prompt_enhancer.py
- 피드백 데이터 분석을 통한 프롬프트 개선
- 좋은/나쁜 예시 기반 자동 최적화
- Chain of Thought 패턴 적용

### ⚙️ **설정 및 유틸리티**

#### config_loader.py
- JSON 기반 설정 파일 관리
- 환경별 설정 지원
- 기본값 및 검증 로직

#### prompt_loader.py
- 프롬프트 템플릿 로딩
- RAG 컨텍스트 통합
- 싱글톤 패턴 구현

## 📊 출력 형식

생성되는 Excel 파일은 다음 구조를 가집니다:

### Excel 템플릿 구조
- **B5 (시나리오 개요)**: 전체 테스트 목적 및 배경 설명
- **F4 (테스트 시나리오명)**: 변경사항을 대표하는 제목
- **A11부터 (테스트 케이스 목록)**:
  - **ID**: 자동 생성되는 테스트 케이스 식별자
  - **절차**: 테스트 수행 단계별 가이드
  - **사전조건**: 테스트 실행 전 필요한 준비사항
  - **데이터**: 테스트에 사용되는 입력 데이터
  - **예상결과**: 테스트 성공 시 예상되는 결과
  - **종류**: 단위 테스트/통합 테스트 구분 (Y/N 플래그)

### 특수 기능
- **개행 문자 처리**: `\\n` 이스케이프 시퀀스를 실제 개행으로 변환
- **JSON 데이터 포맷팅**: 복잡한 데이터 구조를 읽기 쉬운 JSON 형태로 저장
- **타임스탬프 파일명**: `YYYYMMDD_HHMMSS_테스트_시나리오_결과.xlsx` 형식

## 🛠️ 기술 스택

### **AI & LLM**
- **Ollama**: 로컬 LLM 실행 환경
- **qwen3:8b**: 한국어 지원 언어 모델
- **sentence-transformers**: 한국어 임베딩 (ko-sroberta-multitask)

### **데이터베이스**
- **ChromaDB**: 벡터 데이터베이스 (RAG 시스템)
- **SQLite**: 피드백 데이터 저장

### **Python 라이브러리**
- **GitPython**: Git 저장소 분석
- **openpyxl**: Excel 파일 처리
- **python-docx**: Word 문서 파싱
- **streamlit**: 웹 인터페이스
- **pandas**: 데이터 처리
- **requests**: HTTP 통신

### **테스트 도구**
- **pytest**: 테스트 프레임워크
- **pytest-mock**: Mock 객체 지원
- **pytest-cov**: 코드 커버리지 측정

## 🔍 문제 해결

### 일반적인 오류

#### 🔌 **Ollama 관련 오류**
1. **Ollama 연결 실패**
   - Ollama 서버가 실행 중인지 확인: `ollama serve`
   - `http://localhost:11434` 접근 가능 여부 확인
   - 포트 충돌 확인 및 방화벽 설정

2. **모델 다운로드 실패**
   - 인터넷 연결 확인
   - `ollama pull qwen3:8b` 재실행
   - 디스크 공간 부족 여부 확인

#### 📁 **Git 저장소 관련 오류**
1. **Git 저장소 접근 오류**
   - 저장소 경로가 올바른지 확인
   - Git 인증 정보 설정 확인
   - 저장소 권한 확인

2. **브랜치 분석 실패**
   - 대상 브랜치 존재 여부 확인
   - `origin/develop`, `HEAD` 브랜치 상태 확인
   - Git remote 설정 확인

#### 🗄️ **데이터베이스 관련 오류**
1. **ChromaDB 초기화 실패**
   - `vector_db_data/` 디렉토리 권한 확인
   - 디스크 공간 확인
   - sentence-transformers 모델 다운로드 확인

2. **SQLite 피드백 DB 오류**
   - `feedback.db` 파일 권한 확인
   - 데이터베이스 잠금 상태 확인

#### 🧪 **테스트 관련 오류**
1. **테스트 실행 실패**
   - 가상환경 활성화 확인
   - pytest 의존성 설치 확인: `pip install pytest pytest-mock pytest-cov`
   - 테스트 파일 경로 확인

2. **Mock 관련 오류**
   - pytest-mock 설치 확인
   - 테스트 격리 문제 시 `conftest.py` 설정 확인

### 성능 최적화

#### 🚀 **응답 속도 개선**
- `config.json`에서 `performance_mode: true` 설정
- RAG 시스템 비활성화: `rag.enabled: false`
- 타임아웃 시간 조정: `timeout` 값 증가

#### 💾 **메모리 사용량 최적화**
- 벡터 DB 크기 관리 (불필요한 문서 삭제)
- 피드백 데이터 정기적 백업 및 정리

## 🤝 기여하기

### 개발 환경 설정
1. **Repository Fork**: GitHub에서 프로젝트 Fork
2. **Clone**: `git clone https://github.com/YOUR_USERNAME/TestscenarioMaker.git`
3. **가상환경 설정**: `python -m venv venv && source venv/bin/activate`
4. **의존성 설치**: `pip install -r requirements.txt`
5. **테스트 실행**: `pytest` (모든 테스트가 통과하는지 확인)

### 기여 가이드라인
1. **Feature Branch 생성**: `git checkout -b feature/YourFeatureName`
2. **코드 작성**: 
   - 타입 힌트 추가
   - 함수별 docstring 작성
   - 테스트 코드 포함
3. **테스트 실행**: `pytest --cov=src` (커버리지 확인)
4. **Commit & Push**: 
   ```bash
   git commit -m 'feat: Add YourFeatureName'
   git push origin feature/YourFeatureName
   ```
5. **Pull Request 생성**: GitHub에서 PR 생성

### 코딩 컨벤션
- **Python 스타일**: PEP 8 준수
- **테스트 작성**: 모든 새 기능에 대한 단위 테스트 필수
- **문서화**: 새로운 기능은 README.md 및 CLAUDE.md 업데이트
- **커밋 메시지**: Conventional Commits 형식 권장

### 이슈 리포팅
- **버그 리포트**: 재현 단계, 예상 결과, 실제 결과 포함
- **기능 요청**: 사용 사례 및 기대 효과 설명
- **문서 개선**: 불분명한 부분이나 누락된 정보 지적

## 🏆 기여자

이 프로젝트에 기여해주신 모든 분들께 감사드립니다!

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원 및 문의

- **GitHub Issues**: 버그 리포트 및 기능 요청
- **Discussions**: 일반적인 질문 및 토론
- **Wiki**: 자세한 사용법 및 팁 공유

---

**TestscenarioMaker**를 사용해 주셔서 감사합니다! 🚀 