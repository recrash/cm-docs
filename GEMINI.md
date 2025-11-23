# GEMINI.md - TestscenarioMaker Monorepo Architecture Guide

이 문서는 소스 코드 분석을 기반으로 작성된 **TestscenarioMaker**의 아키텍처, 개발 환경, 배포 전략 및 제약 사항을 정의한 **Single Source of Truth**입니다.

## 1\. 🏛️ 프로젝트 핵심 철학 및 제약 사항 (Critical Constraints)

이 프로젝트는 일반적인 클라우드 네이티브 환경과 다릅니다. 개발 시 다음 제약 사항을 **반드시** 준수해야 합니다.

1.  **Docker 사용 절대 불가 (No Docker):**
      * 개발 및 운영 서버(GCP VM T4)의 중첩 가상화가 비활성화되어 있습니다.
      * 모든 서비스는 **Windows Native Process** 또는 **NSSM(Non-Sucking Service Manager)** 서비스로 구동됩니다.
2.  **폐쇄망 환경 (Air-gapped Environment):**
      * 운영 서버는 인터넷이 차단되어 있습니다. `pip install`이나 `npm install`이 불가능합니다.
      * 모든 의존성은 **Wheelhouse(.whl)** 및 **오프라인 캐시** 형태로 미리 준비되어야 합니다.
3.  **크로스 플랫폼 & Windows 우선 (Cross-Platform, Windows First):**
      * 서버는 Windows Server 2019입니다.
      * 경로 처리 시 반드시 `pathlib`을 사용하고, 문자열 경로 결합(`+ "\\"`)을 피해야 합니다.
      * Powershell 스크립트 작성 시 \*\*UTF-8 인코딩(BOM 이슈)\*\*에 각별히 주의해야 합니다.
4.  **MSA-like Monorepo:**
      * 하나의 리포지토리 안에 3개의 독립적인 서비스(`webservice`, `cli`, `autodoc_service`)가 공존합니다.
      * 각 서비스는 서로 다른 Python 버전을 사용할 수 있으므로 가상환경(`.venv`)을 철저히 분리해야 합니다.

-----

## 2\. 🏗️ 시스템 아키텍처 (System Architecture)

### 2.1 서비스 구성 (Service Components)

| 서비스명 | 경로 | 기술 스택 | Python 버전 | 역할 |
| :--- | :--- | :--- | :--- | :--- |
| **Webservice** | `/webservice` | FastAPI, ChromaDB, PyTorch | **3.9** | 메인 백엔드 API, RAG, LLM 연동, 세션 관리 |
| **Frontend** | `/webservice/frontend` | React, Vite, MUI | Node.js | 사용자 UI, WebSocket 클라이언트 |
| **AutoDoc** | `/autodoc_service` | FastAPI, python-docx, openpyxl | **3.12** | Word/Excel 문서 생성 및 파싱 전담 (안정성 중시) |
| **CLI** | `/cli` | Click, Rich, PyInstaller | **3.13** | 로컬 저장소(Git/SVN) 분석 및 API 전송 도구 |

> **⚠️ 주의:** 서비스별 Python 버전이 상이합니다. `Jenkinsfile`과 배포 스크립트(`deploy_test_env.ps1`)를 보면 `webservice`는 CUDA 호환성을 위해 3.9를, 문서를 다루는 `autodoc`은 3.12를, `cli`는 최신 3.13을 사용하고 있습니다.

### 2.2 데이터 흐름 (Data Flow)

1.  **Phase 1 (Scenario Gen):** CLI/Web → Git/SVN 분석 → Webservice → RAG(ChromaDB) → LLM(Ollama) → 결과 JSON → Excel 생성
2.  **Phase 2 (Full Doc Gen):** Web(HTML 업로드) → AutoDoc(파싱) → Webservice(세션 생성) → CLI(URL Protocol 실행) → WebSocket(진행률) → 문서 통합 생성

-----

## 3\. 📂 디렉토리 구조 및 핵심 파일 (Directory Structure)

```
root/
├── webservice/                  # [Main Backend]
│   ├── app/
│   │   ├── api/routers/v2/      # Phase 2 (CLI 연동, WebSocket) 핵심 로직
│   │   ├── core/                # 비즈니스 로직 (LLM, RAG, Excel)
│   │   │   ├── vector_db/       # ChromaDB 매니저
│   │   │   └── git_analyzer.py  # Git 분석 로직
│   │   └── main.py              # FastAPI 진입점
│   ├── frontend/                # [React App]
│   └── .venv/                   # Python 3.9 Virtual Env
├── autodoc_service/             # [Document Service]
│   ├── app/services/            # 문서 생성 로직 (Word, Excel)
│   │   ├── html_parser.py       # HTML 파싱 로직
│   │   └── label_based_word_builder.py # 라벨 기반 Word 매핑
│   └── .venv312/                # Python 3.12 Virtual Env
├── cli/                         # [Client Tool]
│   ├── src/ts_cli/
│   │   ├── vcs/                 # Git/SVN 전략 패턴 구현
│   │   └── main.py              # URL Protocol 핸들러 포함
│   └── .venv/                   # Python 3.13 Virtual Env
├── scripts/                     # [Deployment Scripts]
│   ├── deploy_test_env.ps1      # 테스트 인스턴스 배포 (핵심)
│   └── download-all-dependencies.sh # 오프라인 패키지 수집
└── utilities/                   # 유틸리티 스크립트
```

-----

## 4\. 💻 개발 가이드라인 (Development Guidelines)

### 4.1 환경 변수 및 경로 처리

이 프로젝트는 \*\*프로덕션(배포)\*\*과 **개발(로컬)** 환경을 구분하기 위해 환경 변수를 적극적으로 사용합니다.

  * **데이터 경로:** 코드 내에서 하드코딩하지 말고 `app.core.config_loader` 또는 `paths.py`를 통해 경로를 가져와야 합니다.
      * `WEBSERVICE_DATA_PATH`: 운영 서버의 데이터 저장소 (예: `C:\deploys\data\webservice`)
      * `AUTODOC_DATA_PATH`: AutoDoc 서비스 데이터 저장소
  * **NSSM 서비스:** 운영 서버에서는 `nssm`을 통해 환경 변수를 주입받아 실행됩니다.

### 4.2 로깅 (Logging)

  * **파일 로깅 필수:** Windows 서비스로 동작 시 콘솔 확인이 어렵습니다. `logging_config.py`를 통해 일별 로그 파일(`YYYYMMDD_backend.log`)을 생성합니다.
  * **인코딩:** 로그 파일 생성 시 반드시 `encoding='utf-8'`을 명시해야 합니다. (한글 깨짐 방지)

### 4.3 API 및 통신

  * **Websocket:** `v2/progress_websocket.py`와 `full_generation_websocket.py`를 통해 장시간 작업의 진행 상황을 전송합니다.
      * Frontend는 `ping`을 보내고 Backend는 `pong`으로 응답하여 연결을 유지합니다 (Heartbeat).
  * **Inter-Service:** Webservice가 AutoDoc Service를 호출할 때는 `http://localhost:8001`을 사용합니다.

-----

## 5\. 🚀 배포 프로세스 (Deployment)

### 5.1 Jenkins & PowerShell

  * 배포는 Jenkins에서 `Jenkinsfile`을 통해 트리거되며, 실제 작업은 `scripts/*.ps1` PowerShell 스크립트가 수행합니다.
  * **Wheelhouse:** 인터넷이 없는 환경을 위해 `download-all-dependencies.sh`로 `.whl` 파일을 미리 받아 `C:\deploys\packages\wheelhouse`에 저장해두고, 배포 시 `--no-index --find-links` 옵션으로 설치합니다.

### 5.2 배포 스크립트 로직 (`deploy_test_env.ps1`)

1.  **격리된 Python 실행:** `py_clean.bat` 래퍼를 생성하여 `PYTHONHOME`, `PYTHONPATH` 환경 변수를 초기화한 뒤 가상환경을 생성합니다. (Windows 전역 Python 설정 충돌 방지)
2.  **서비스 관리:** `nssm`을 사용하여 서비스를 중지/삭제/등록/시작합니다.
3.  **Nginx 설정:** 브랜치별로 `nginx` 설정을 동적으로 생성(`tests-{BID}.conf`)하고 리로드합니다.

-----

## 6\. 🔍 문제 해결 (Troubleshooting)

### Q: "Could not import runpy module" 오류가 발생해요.

**A:** Windows 서버에 전역 `PYTHONHOME`이 설정되어 있어 가상환경 Python과 충돌하는 경우입니다. `scripts/python_isolation.ps1`에 구현된 것처럼 배치 파일 래퍼를 통해 환경 변수를 초기화하고 실행해야 합니다.

### Q: 문서 생성 시 폰트가 깨지거나 스타일이 이상해요.

**A:** `autodoc_service`는 서버에 설치된 폰트(맑은 고딕 등)에 의존합니다. 또한 `python-docx`나 `openpyxl` 사용 시 스타일 객체를 정확히 복사/적용하는지 `style_utils.py`(또는 관련 로직)를 확인하세요.

### Q: CLI가 URL Protocol로 실행되지 않아요.

**A:** 레지스트리 등록 문제일 수 있습니다. `cli/scripts/setup_win.nsi` 또는 `url_handler.ps1`이 올바르게 실행되었는지, 그리고 브라우저에서 해당 프로토콜(`testscenariomaker://`)을 허용했는지 확인하세요. 경로는 URL Decoding이 필요합니다.

### Q: RAG 검색 결과가 이상해요.

**A:** `webservice/config.json`의 임베딩 모델 설정과 실제 `vector_db_data`에 저장된 임베딩이 일치하는지 확인하세요. 모델을 변경했다면 DB를 초기화(`rm -rf vector_db_data`)하고 재인덱싱해야 합니다.

-----

이 문서는 코드 베이스가 변경됨에 따라 지속적으로 업데이트되어야 합니다. **항상 코드가 진실(Truth)입니다.**