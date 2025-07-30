# TestscenarioMaker

Git 변경 내역을 분석하여 자동으로 테스트 시나리오를 생성하는 AI 기반 도구입니다.

## 📋 프로젝트 개요

이 프로젝트는 Git 저장소의 변경 내역(커밋 메시지, 코드 diff)을 분석하여, LLM(Large Language Model)을 활용해 고품질의 한국어 테스트 시나리오를 자동으로 생성합니다. 생성된 시나리오는 Excel 파일(.xlsx) 형태로 출력됩니다.

## 🎯 주요 기능

- **Git 변경 내역 분석**: 커밋 메시지와 코드 diff를 자동으로 추출
- **LLM 기반 시나리오 생성**: Ollama를 통한 qwen3:8b 모델 활용
- **Excel 템플릿 기반 출력**: 표준화된 테스트 시나리오 형식으로 저장
- **다국어 지원**: 한국어 기반의 테스트 시나리오 생성

## 🏗️ 프로젝트 구조

```
TestscenarioMaker/
├── 📂 outputs/              # 생성된 엑셀 파일 저장 폴더
├── 📂 src/                  # 핵심 로직 모듈
│   ├── git_analyzer.py      # Git 변경 내역 분석
│   ├── llm_handler.py       # Ollama LLM 호출
│   ├── excel_writer.py      # 엑셀 파일 생성
│   └── document_parser.py   # 문서 파싱 (변경관리요청서)
├── 📂 templates/            # 엑셀 템플릿 파일
│   └── template.xlsx
├── 📜 main.py               # 메인 실행 스크립트
└── 📜 requirements.txt      # Python 의존성
```

## 🚀 설치 및 실행

### 1. 환경 요구사항

- Python 3.8 이상
- Ollama (로컬 LLM 실행용)
- Git 저장소 접근 권한

### 2. 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 3. Ollama 설정

```bash
# Ollama 설치 (https://ollama.ai)
# qwen3:8b 모델 다운로드
ollama pull qwen3:8b

# Ollama 서버 시작
ollama serve
```

### 4. 실행

```bash
# 메인 스크립트 실행
python main.py
```

## 📖 사용법

### 기본 실행

1. `main.py`에서 `repo_path` 변수를 분석할 Git 저장소 경로로 수정
2. 스크립트 실행: `python main.py`
3. 생성된 Excel 파일은 `outputs/` 폴더에 저장

### 설정 옵션

- **모델 변경**: `main.py`의 `model_name` 변수 수정
- **브랜치 지정**: `git_analyzer.py`의 `base_branch`, `head_branch` 파라미터 조정
- **템플릿 경로**: `excel_writer.py`의 `template_path` 파라미터 수정

## 🔧 주요 모듈 설명

### git_analyzer.py
- Git 저장소의 커밋 메시지와 코드 diff를 추출
- 브랜치 간 비교 분석 지원
- 변경 내역을 구조화된 텍스트로 변환

### llm_handler.py
- Ollama API를 통한 LLM 호출
- 다양한 모델 지원 (기본: qwen3:8b)
- 타임아웃 및 에러 처리

### excel_writer.py
- LLM 생성 결과를 Excel 템플릿에 매핑
- 테스트 케이스별 상세 정보 저장
- 타임스탬프 기반 파일명 생성

### document_parser.py
- 변경관리요청서(.docx) 파싱
- 제목, 목적 등 주요 정보 추출
- 표(table) 구조 분석

## 📊 출력 형식

생성되는 Excel 파일은 다음 구조를 가집니다:

- **시나리오 개요**: 전체 테스트 목적 설명
- **테스트 시나리오명**: 대표 제목
- **테스트 케이스**: ID, 절차, 사전조건, 데이터, 예상결과, 종류(단위/통합)

## 🛠️ 기술 스택

- **LLM**: Ollama + qwen3:8b
- **Git 분석**: GitPython
- **Excel 처리**: openpyxl
- **문서 파싱**: python-docx
- **HTTP 통신**: requests

## 🔍 문제 해결

### 일반적인 오류

1. **Ollama 연결 실패**
   - Ollama 서버가 실행 중인지 확인
   - `http://localhost:11434` 접근 가능 여부 확인

2. **Git 저장소 접근 오류**
   - 저장소 경로가 올바른지 확인
   - Git 인증 정보 설정 확인

3. **모델 다운로드 실패**
   - 인터넷 연결 확인
   - `ollama pull qwen3:8b` 재실행

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요. 