# TestscenarioMaker CLI

TestscenarioMaker를 위한 로컬 저장소 분석 CLI 도구입니다. Git 저장소의 변경사항을 분석하여 테스트 시나리오를 자동 생성합니다.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

## 🎯 주요 기능

- **Git 저장소 분석**: 로컬 Git 저장소의 변경사항을 자동으로 분석
- **브랜치 비교**: 기본 브랜치와 현재 브랜치 간 차이점 분석 (기본값: origin/develop → HEAD)
- **Custom URL Protocol**: `testscenariomaker://` 프로토콜을 통한 웹 브라우저 통합
- **크로스플랫폼**: Windows, macOS, Linux 지원
- **한국어 UI**: 모든 사용자 인터페이스가 한국어로 제공
- **풍부한 출력**: 텍스트와 JSON 형식 출력 지원
- **백그라운드 실행**: URL 프로토콜 클릭 시 백그라운드에서 자동 실행
- **macOS 헬퍼 앱**: 브라우저 샌드박스 제약을 우회하는 전용 헬퍼 앱 제공

## 🚀 설치 및 사용법

### 사전 배포 버전 설치 (권장)

#### Windows
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `TestscenarioMaker-CLI-Setup.exe` 다운로드
2. 설치 프로그램 실행 후 안내에 따라 설치
3. `testscenariomaker://` URL 프로토콜이 자동으로 등록됩니다

#### macOS
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `.dmg` 파일 다운로드
2. DMG 파일을 마운트하고 `install.sh` 실행
3. 메인 CLI 앱과 헬퍼 앱이 동시에 설치됩니다
4. `testscenariomaker://` URL 프로토콜이 헬퍼 앱에 등록됩니다

### 개발자 설치

```bash
# 저장소 클론
git clone https://github.com/testscenariomaker/cli.git
cd cli

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 개발 모드로 설치
pip install -e .
```

### 기본 사용법

```bash
# 현재 디렉토리 분석
ts-cli analyze

# 특정 경로 분석
ts-cli analyze --path /path/to/repository

# 상세 모드로 분석
ts-cli analyze --path /path/to/repository --verbose

# JSON 형식으로 출력
ts-cli analyze --path /path/to/repository --output json

# Dry run (실제 API 호출 없이 분석만)
ts-cli analyze --path /path/to/repository --dry-run

# 저장소 정보만 조회
ts-cli info /path/to/repository

# 설정 정보 확인
ts-cli config-show

# 버전 확인
ts-cli --version
```

### URL 프로토콜 사용법

설치 후 웹 브라우저에서 `testscenariomaker://` 링크를 클릭하면 CLI가 자동으로 실행됩니다:

```
testscenariomaker:///path/to/your/repository
testscenariomaker://C:/projects/my-repo    # Windows
```

**지원 기능:**
- 크로스플랫폼 경로 처리
- URL 인코딩된 경로 지원 (공백, 특수문자 포함)
- 자동 브라우저 통합 (설치 시 프로토콜 등록)
- 백그라운드 실행 (콘솔 창 없음)

#### macOS 헬퍼 앱

macOS에서는 브라우저 샌드박스 제약으로 인한 네트워크 통신 문제를 해결하기 위해 전용 헬퍼 앱을 제공합니다:

**작동 원리:**
1. 브라우저에서 `testscenariomaker://` 링크 클릭
2. TestscenarioMaker Helper.app이 URL 수신
3. 헬퍼 앱이 독립적인 프로세스로 CLI 실행 (샌드박스 제약 우회)
4. CLI가 정상적으로 API 호출 및 분석 수행

**브라우저 호환성:**
- Safari, Chrome, Firefox 모두 지원
- 첫 번째 클릭 시 "허용" 또는 "열기" 선택 필요

## 📁 프로젝트 구조

```
testscenariomaker-cli/
├── src/ts_cli/              # 메인 소스 코드
│   ├── main.py              # CLI 진입점 및 URL 프로토콜 처리
│   ├── cli_handler.py       # 비즈니스 로직 오케스트레이션
│   ├── api_client.py        # API 클라이언트 (httpx + tenacity)
│   ├── vcs/                 # VCS 전략 패턴
│   │   ├── base_analyzer.py # 추상 기반 클래스
│   │   └── git_analyzer.py  # Git 구현체
│   └── utils/               # 유틸리티
│       ├── config_loader.py # 다중 위치 설정 관리
│       └── logger.py        # Rich 콘솔 + 파일 로깅
├── tests/                   # 테스트 피라미드
│   ├── unit/               # 단위 테스트
│   ├── integration/        # 통합 테스트  
│   ├── e2e/                # E2E 테스트
│   └── test_url_parsing.py # URL 프로토콜 테스트
├── scripts/                # 빌드 및 패키징
│   ├── build.py           # 크로스플랫폼 빌드
│   ├── setup_win.nsi      # Windows NSIS (URL 프로토콜 등록)
│   ├── create_dmg.py      # macOS DMG (헬퍼 앱 포함)
│   ├── helper_app.applescript    # macOS 헬퍼 앱 소스
│   ├── build_helper_app.py       # 헬퍼 앱 빌더
│   ├── install_helper.sh         # 헬퍼 앱 설치 스크립트
│   └── test_helper_app.py        # 헬퍼 앱 테스트 도구
└── config/                # 기본 설정
    └── config.ini         # 기본 설정 파일
```

## 🏗️ 아키텍처

### VCS 전략 패턴

확장 가능한 VCS 지원을 위해 전략 패턴을 사용합니다:

- **추상 기반**: `RepositoryAnalyzer`가 공통 인터페이스 정의
- **현재 구현**: `GitAnalyzer`가 Git 지원
- **팩토리**: `get_analyzer()`가 저장소 타입별 적절한 분석기 반환
- **확장성**: SVN, Mercurial 등 새로운 VCS 쉽게 추가 가능

### URL 프로토콜 통합

- **프로토콜 핸들러**: `main.py`의 `handle_url_protocol()`이 URL 스킴 처리
- **크로스플랫폼**: Windows 레지스트리(HKCR)와 macOS CFBundleURLTypes 지원
- **경로 처리**: 플랫폼별 URL 파싱과 경로 정규화
- **오류 처리**: URL, 경로, 저장소 상태에 대한 포괄적인 검증

### 핵심 컴포넌트 흐름

1. **CLI 진입점** (`main.py`) → URL 프로토콜 감지 → Click 기반 한국어 UI 및 명령 라우팅
2. **비즈니스 로직** (`cli_handler.py`) → 저장소 분석 → API 호출 → 결과 처리 오케스트레이션
3. **VCS 분석** (`vcs/`) → Git/SVN/Mercurial 지원을 위한 전략 패턴 (현재 Git만 구현)
4. **API 클라이언트** (`api_client.py`) → httpx + tenacity를 통한 견고한 API 통신
5. **설정 관리** (`config_loader.py`) → 다중 위치 설정 파일 로딩
6. **로깅** (`logger.py`) → Rich 콘솔 + 파일 로깅

## ⚙️ 설정

### 설정 파일 위치 (우선순위)

1. 현재 디렉토리의 `config.ini`
2. 프로젝트 루트의 `config/config.ini`
3. 자동 생성되는 기본 설정

### 주요 설정 옵션

```ini
[api]
base_url = http://localhost:8000
timeout = 30
max_retries = 3

[cli]
default_output_format = text
verbose = false
show_progress = true

[logging]
level = INFO
file_enabled = false
# 플랫폼별 자동 경로 (권장)
file_path = auto
# macOS: ~/Library/Logs/testscenariomaker-cli/ts-cli.log
# Windows: %APPDATA%/testscenariomaker-cli/ts-cli.log
# Linux: ~/.local/share/testscenariomaker-cli/ts-cli.log

[vcs]
git_timeout = 30
max_diff_size = 1048576
```

## 🧪 개발 가이드

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/testscenariomaker/cli.git
cd cli

# 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 개발 의존성 설치
pip install -r requirements-dev.txt
pip install -e .
```

### 테스트 실행

```bash
# 모든 테스트 실행 (커버리지 포함)
pytest --cov=ts_cli --cov-report=html

# 테스트 유형별 실행
pytest -m unit          # 단위 테스트만
pytest -m integration   # 통합 테스트만
pytest -m e2e           # E2E 테스트만

# 특정 테스트 실행
pytest tests/unit/test_vcs.py
pytest tests/unit/test_vcs.py::TestVCSFactory::test_get_analyzer_with_git_repository

# URL 프로토콜 테스트
pytest tests/test_url_parsing.py

# macOS 헬퍼 앱 종합 테스트 (macOS에서만)
python scripts/test_helper_app.py
```

### 코드 품질

```bash
# 코드 포매팅
black src/ tests/
isort src/ tests/

# 린팅
flake8 src/ tests/

# 타입 체킹
mypy src/
```

### 빌드

#### 크로스플랫폼 실행파일 빌드

```bash
# 전체 빌드 (정리 + 빌드 + 테스트)
python scripts/build.py

# 빌드 옵션
python scripts/build.py --no-clean    # 정리 단계 스킵
python scripts/build.py --no-test     # 테스트 단계 스킵
```

#### 플랫폼별 패키징

**Windows 설치 프로그램:**
```bash
python scripts/build.py
makensis scripts/setup_win.nsi
```

**macOS DMG (헬퍼 앱 포함):**
```bash
python scripts/build.py
python scripts/create_dmg.py

# 헬퍼 앱만 별도 빌드/테스트
python scripts/build_helper_app.py
python scripts/test_helper_app.py

# 헬퍼 앱 없이 DMG 생성
python scripts/create_dmg.py --no-helper-app
```

### 빌드 시스템 특징

- **자동 파일 검증**: 빌드 전 필수 파일 존재 여부 확인
- **선택적 리소스**: config.ini, 아이콘 등 없어도 빌드 진행
- **크로스플랫폼 경로**: pathlib 사용으로 플랫폼 독립적 경로 처리
- **상세 로깅**: 각 빌드 단계별 진행 상황과 오류 상세 표시
- **자동 복구**: DMG 생성 시 마운트 실패 등에 대한 자동 복구

### 크로스플랫폼 개발 가이드

#### 중요: pathlib 사용 필수

**올바른 경로 사용법:**
```python
from pathlib import Path

# 프로젝트 구조 (상대 경로)
project_root = Path(__file__).parent.parent
src_dir = project_root / "src"
config_file = project_root / "config" / "config.ini"

# subprocess 호출 시 문자열 변환 필수
subprocess.run(
    ['git', 'status'], 
    cwd=str(repo_path),  # 크로스플랫폼 호환성을 위해 필수
    capture_output=True
)
```

**피해야 할 패턴:**
```python
# ❌ 문자열 연결
config_path = project_root + "/config/config.ini"

# ❌ os.path 사용
import os
config_path = os.path.join(project_root, "config", "config.ini")

# ❌ subprocess에 Path 객체 직접 전달
subprocess.run(['git', 'status'], cwd=repo_path)  # 오류 발생!
```

### VCS 지원 확장

새로운 VCS 시스템 추가 방법:

1. `RepositoryAnalyzer`를 상속하는 새 분석기 클래스 생성
2. 추상 메서드 구현: `validate_repository()`, `get_changes()`, `get_repository_info()`
3. `get_analyzer()` 팩토리 함수에 감지 로직 추가
4. 기존 패턴을 따라 포괄적인 테스트 작성
5. **중요**: 모든 파일 시스템 작업에 `pathlib.Path` 사용

## 🔧 문제 해결

### URL 프로토콜 관련

**링크 클릭 후 반응이 없는 경우:**

1. **프로세스 실행 확인**
   ```bash
   # macOS/Linux
   ps aux | grep ts-cli
   
   # Windows
   tasklist | findstr ts-cli
   ```

2. **URL 프로토콜 등록 확인**
   ```bash
   # macOS
   /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
   
   # Windows
   reg query "HKEY_CLASSES_ROOT\testscenariomaker"
   ```

3. **로그 파일 확인**
   ```bash
   # 로그 위치 확인
   ts-cli config-show
   
   # 로그 내용 확인
   # macOS
   cat ~/Library/Logs/testscenariomaker-cli/ts-cli.log
   
   # Windows
   type "%APPDATA%\testscenariomaker-cli\ts-cli.log"
   
   # Linux
   cat ~/.local/share/testscenariomaker-cli/ts-cli.log
   ```

**macOS 헬퍼 앱 문제:**

```bash
# AppleScript 컴파일 오류 시
xcode-select --install

# 헬퍼 앱 수동 설치
sh scripts/install_helper.sh

# URL 스킴 강제 재등록
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "/Applications/TestscenarioMaker Helper.app"

# 헬퍼 앱 종합 테스트
python scripts/test_helper_app.py
```

### 일반적인 빌드 문제

```bash
# PyInstaller 누락
pip install pyinstaller

# 권한 문제 (macOS/Linux)
chmod +x scripts/build.py scripts/create_dmg.py

# 임시 파일 정리
rm -rf build/ dist/ *.spec

# macOS DMG 마운트 문제
sudo hdiutil detach "/Volumes/TestscenarioMaker CLI*" -force
rm -f dist/temp.dmg
```

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Run tests (`pytest`)
4. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
5. Push to the Branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

### 기여 지침

- 모든 새 기능은 테스트와 함께 제출
- 코드 스타일은 Black과 isort 사용
- 커밋 메시지는 명확하게 작성
- `pathlib.Path` 사용으로 크로스플랫폼 호환성 확보

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

- **버그 리포트**: [GitHub Issues](https://github.com/testscenariomaker/cli/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/testscenariomaker/cli/discussions)
- **문서**: [공식 문서](https://docs.testscenariomaker.com/cli)

---

**TestscenarioMaker CLI**는 개발자의 생산성 향상을 위해 지속적으로 발전하고 있습니다. 🚀