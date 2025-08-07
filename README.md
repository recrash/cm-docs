# TestscenarioMaker CLI

TestscenarioMaker를 위한 로컬 저장소 분석 CLI 도구입니다. v2 API WebSocket 지원으로 실시간 진행 상황 모니터링과 Custom URL Protocol을 통한 직관적인 워크플로우를 제공합니다.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

## 🎯 주요 기능

- **v2 API WebSocket 지원**: 실시간 진행 상황 모니터링으로 향상된 사용자 경험
- **Custom URL Protocol**: `testscenariomaker://` 프로토콜을 통한 웹에서 직접 실행
- **백그라운드 실행**: URL 프로토콜 클릭 시 백그라운드에서 자동 실행
- **진행상황 모니터링**: 로그 파일과 프로세스 상태를 통한 실시간 모니터링
- **Git 저장소 분석**: 로컬 Git 저장소의 변경사항을 자동으로 분석
- **전략 패턴 기반**: 향후 SVN, Mercurial 등 다른 VCS 지원 확장 가능
- **크로스플랫폼**: Windows와 macOS 모두 지원
- **한국어 UI**: 모든 사용자 인터페이스가 한국어로 제공
- **풍부한 출력**: 텍스트와 JSON 형식 출력 지원
- **macOS 헬퍼 앱**: 브라우저 샌드박스 제약을 우회하는 전용 헬퍼 앱 제공

## 🚀 빠른 시작

### 설치

#### Windows
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `TestscenarioMaker-CLI-Setup.exe` 다운로드
2. 설치 프로그램 실행 후 안내에 따라 설치
3. `testscenariomaker://` URL 프로토콜이 자동으로 등록됩니다

#### macOS
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `.dmg` 파일 다운로드
2. DMG 파일을 마운트하고 `install.sh` 실행
   - 메인 CLI 앱과 헬퍼 앱이 동시에 설치됩니다
   - 헬퍼 앱은 웹 브라우저 샌드박스 제약을 우회합니다
   - `testscenariomaker://` URL 프로토콜이 헬퍼 앱에 등록됩니다

#### 개발자 설치 (pip)
```bash
git clone https://github.com/testscenariomaker/cli.git
cd cli
pip install -e .
```

### 기본 사용법

```bash
# 현재 디렉토리 분석 (v2 API 사용)
ts-cli analyze

# 특정 경로 분석
ts-cli analyze --path /path/to/repository

# 상세 모드로 분석
ts-cli analyze --path /path/to/repository --verbose

# JSON 형식으로 출력
ts-cli analyze --path /path/to/repository --output json

# Dry run (실제 API 호출 없이 분석만)
ts-cli analyze --path /path/to/repository --dry-run
```

### 실시간 진행 상황 모니터링

v2 API WebSocket 지원으로 시나리오 생성 과정을 실시간으로 확인할 수 있습니다:

```bash
# 실시간 진행 상황 표시 (기본)
ts-cli analyze --path /path/to/repository

# 상세 진행 상황 (verbose 모드)
ts-cli analyze --path /path/to/repository --verbose
```

**진행 상황 표시 예시:**
```
v2 API 요청 전송 중... [████████████████████] 100%
시나리오 생성 진행 중... [██████████░░░░░░░░░░] 50%
[ANALYZING] 저장소 분석 중... [████████████████░░] 80%
[GENERATING] 테스트 시나리오 생성 중... [████████████████████] 100%
✅ 시나리오 생성 완료!
```

### 백그라운드 실행 및 모니터링

#### URL 프로토콜을 통한 백그라운드 실행

웹 브라우저에서 `testscenariomaker://` 링크를 클릭하면 CLI가 백그라운드에서 실행됩니다:

**Windows:**
- CLI가 백그라운드 프로세스로 실행됨
- 콘솔 창이 표시되지 않음
- 진행상황은 로그 파일을 통해 확인 가능

**macOS:**
- 헬퍼 앱이 CLI를 독립적인 프로세스로 실행
- 브라우저 샌드박스 제약을 우회하여 네트워크 통신 가능
- 진행상황은 터미널에서 직접 확인 가능

#### 백그라운드 실행 시 진행상황 확인 방법

**1. 로그 파일 확인**
```bash
# 로그 파일 위치 확인
ts-cli config-show

# 로그 파일 실시간 모니터링 (macOS)
tail -f ~/Library/Logs/testscenariomaker-cli/ts-cli.log

# 로그 파일 실시간 모니터링 (Windows)
Get-Content "$env:APPDATA\testscenariomaker-cli\ts-cli.log" -Wait

# 로그 파일 실시간 모니터링 (Linux)
tail -f ~/.local/share/testscenariomaker-cli/ts-cli.log
```

**2. 프로세스 상태 확인**
```bash
# 실행 중인 CLI 프로세스 확인 (macOS/Linux)
ps aux | grep ts-cli

# 실행 중인 CLI 프로세스 확인 (Windows)
tasklist | findstr ts-cli
```

**3. URL 프로토콜 실행 시 터미널 출력**
```bash
# macOS: 헬퍼 앱이 CLI를 터미널에서 실행하도록 설정
# (기본적으로는 백그라운드 실행)

# Windows: 백그라운드 실행이 기본값
# 진행상황 확인을 위해 로그 파일 사용
```

#### 백그라운드 실행 설정

**로그 파일 활성화:**
```ini
# config.ini
[logging]
file_enabled = true
# 플랫폼별 기본 경로 자동 사용 (권장)
# macOS: ~/Library/Logs/testscenariomaker-cli/ts-cli.log
# Windows: %APPDATA%/testscenariomaker-cli/ts-cli.log  
# Linux: ~/.local/share/testscenariomaker-cli/ts-cli.log
file_path = auto
level = INFO
```

**진행상황 표시 설정:**
```ini
# config.ini
[cli]
show_progress = true
verbose = true
```

### 저장소 정보 확인

```bash
# 저장소 정보 조회
ts-cli info /path/to/repository

# 설정 정보 확인
ts-cli config-show

# 버전 확인
ts-cli --version
```

### Custom URL Protocol 사용법

설치 후 웹 브라우저에서 `testscenariomaker://` 링크를 클릭하면 CLI가 백그라운드에서 자동으로 실행됩니다:

```bash
# 웹에서 클릭 가능한 링크 예시
testscenariomaker:///path/to/your/repository
testscenariomaker://C:/projects/my-repo    # Windows

# 터미널에서 직접 테스트
ts-cli "testscenariomaker:///path/to/repository"
```

**지원 기능:**
- 크로스플랫폼 경로 처리 (Windows, macOS, Linux)
- URL 인코딩된 경로 지원 (공백, 특수문자 포함)
- 자동 브라우저 통합 (설치 시 프로토콜 등록)
- **백그라운드 실행**: 콘솔 창 없이 백그라운드에서 실행
- **진행상황 모니터링**: 로그 파일을 통한 실시간 진행상황 확인
- **macOS 헬퍼 앱**: 브라우저 샌드박스 제약 우회

#### macOS 헬퍼 앱 시스템

macOS에서는 브라우저의 샌드박스 제약으로 인해 CLI가 네트워크 통신을 할 수 없는 문제를 해결하기 위해 전용 헬퍼 앱을 제공합니다:

**작동 원리:**
1. 브라우저에서 `testscenariomaker://` 링크 클릭
2. TestscenarioMaker Helper.app이 URL을 수신
3. 헬퍼 앱이 독립적인 프로세스로 CLI 실행 (샌드박스 제약 우회)
4. CLI가 정상적으로 v2 API 호출 및 분석 수행

**브라우저 호환성:**
- **Safari**: 첫 번째 클릭 시 "허용" 선택
- **Chrome**: 첫 번째 클릭 시 "열기" 선택
- **Firefox**: 첫 번째 클릭 시 "링크 열기" 선택

**헬퍼 앱 관리:**
```bash
# 헬퍼 앱만 별도 설치/업데이트
sh scripts/install_helper.sh

# 헬퍼 앱 테스트
python scripts/test_helper_app.py

# URL 스킴 등록 확인
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
```

## 📁 프로젝트 구조

```
testscenariomaker-cli/
├── src/ts_cli/              # 메인 소스 코드
│   ├── main.py              # CLI 진입점
│   ├── cli_handler.py       # 비즈니스 로직 (v2 API 통합)
│   ├── api_client.py        # API 클라이언트 (WebSocket 지원)
│   ├── vcs/                 # VCS 전략 패턴
│   │   ├── base_analyzer.py # 추상 기반 클래스
│   │   └── git_analyzer.py  # Git 구현체
│   └── utils/               # 유틸리티
│       ├── config_loader.py # 설정 관리
│       └── logger.py        # 로깅
├── tests/                   # 테스트 스위트
│   ├── unit/               # 단위 테스트
│   ├── integration/        # 통합 테스트
│   ├── e2e/                # E2E 테스트
│   └── test_url_parsing.py # URL 프로토콜 테스트
├── scripts/                # 빌드 및 패키징
│   ├── build.py           # 빌드 스크립트
│   ├── setup_win.nsi      # Windows NSIS (URL 프로토콜 등록)
│   ├── create_dmg.py      # macOS DMG (헬퍼 앱 포함)
│   ├── helper_app.applescript    # macOS 헬퍼 앱 소스
│   ├── helper_app_info.plist     # 헬퍼 앱 설정
│   ├── build_helper_app.py       # 헬퍼 앱 빌더
│   ├── install_helper.sh         # 헬퍼 앱 설치 스크립트
│   └── test_helper_app.py        # 헬퍼 앱 테스트 도구
├── config/                # 설정 파일
│   └── config.ini         # 기본 설정
└── test_url_protocol.html # URL 프로토콜 E2E 테스트
```

## 🔧 개발자 가이드

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
# 모든 테스트 실행
pytest

# 단위 테스트만
pytest tests/unit/

# 커버리지 포함
pytest --cov=ts_cli --cov-report=html

# 특정 마커만
pytest -m unit          # 단위 테스트
pytest -m integration   # 통합 테스트
pytest -m e2e           # E2E 테스트

# URL 프로토콜 테스트
pytest tests/test_url_parsing.py

# macOS 헬퍼 앱 종합 테스트 (macOS에서만)
python scripts/test_helper_app.py
```

### 빌드

#### 크로스플랫폼 실행파일 빌드

```bash
# 전체 빌드 (정리 + 빌드 + 테스트)
python scripts/build.py

# 정리 없이 빌드
python scripts/build.py --no-clean

# 테스트 없이 빌드
python scripts/build.py --no-test

# 빌드 결과 확인
ls -la dist/
```

#### 플랫폼별 패키징

**Windows 설치 프로그램 (Windows 환경에서)**
```bash
# 실행파일 빌드 후
python scripts/build.py
makensis scripts/setup_win.nsi
# testscenariomaker:// URL 프로토콜이 자동 등록됩니다
```

**macOS DMG (macOS 환경에서)**
```bash
# 실행파일 빌드 후
python scripts/build.py
python scripts/create_dmg.py
# 메인 CLI 앱과 헬퍼 앱이 포함된 DMG 생성됩니다
# testscenariomaker:// URL 프로토콜이 헬퍼 앱에 등록됩니다

# 헬퍼 앱만 별도 빌드/테스트
python scripts/build_helper_app.py
python scripts/test_helper_app.py

# 헬퍼 앱 없이 DMG 생성
python scripts/create_dmg.py --no-helper-app
```

#### 빌드 시스템 특징

- **견고한 파일 검증**: 필수 파일 존재 여부를 사전 확인하여 빌드 실패 방지
- **선택적 파일 처리**: config.ini, icon 파일 등이 없어도 빌드 진행
- **상대경로 기반**: 프로젝트 이식성을 위해 상대경로 구조 유지
- **상세한 로깅**: 각 빌드 단계별 진행 상황과 오류 상세 표시
- **자동 복구**: DMG 생성 시 마운트 실패 등에 대한 자동 복구 로직

#### 빌드 문제 해결

**일반적인 빌드 오류:**

```bash
# PyInstaller 누락 시
pip install pyinstaller

# 권한 문제 (macOS)
chmod +x scripts/build.py scripts/create_dmg.py

# 디스크 공간 부족 확인
df -h

# 임시 파일 정리
rm -rf build/ dist/ *.spec
```

**macOS DMG 생성 오류:**

```bash
# hdiutil 권한 확인
sudo hdiutil attach --help

# 마운트된 볼륨 강제 해제
sudo hdiutil detach "/Volumes/TestscenarioMaker CLI*" -force

# 임시 DMG 파일 정리
rm -f dist/temp.dmg
```

**macOS 헬퍼 앱 관련 오류:**

```bash
# AppleScript 컴파일 오류
# Xcode Command Line Tools 설치 확인
xcode-select --install

# osacompile 명령어 확인
osacompile -l

# 헬퍼 앱 빌드 전 CLI 빌드 필수
python scripts/build.py
python scripts/build_helper_app.py

# 헬퍼 앱 테스트 및 문제 진단
python scripts/test_helper_app.py

# URL 스킴 등록 강제 갱신
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f /Applications/TestscenarioMaker\ Helper.app
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

## ⚙️ 설정

### 설정 파일 위치

1. 현재 디렉토리의 `config.ini`
2. 프로젝트 루트의 `config/config.ini`
3. 자동 생성되는 기본 설정

### 설정 옵션

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
```

## 🧪 테스트 전략

### 테스트 피라미드

- **단위 테스트** (Unit): 개별 모듈 기능 테스트
- **통합 테스트** (Integration): API 통신 및 모듈 간 연동 테스트  
- **E2E 테스트** (End-to-End): 전체 사용자 워크플로우 테스트

### CLAUDE.md 지침 준수

- Playwright MCP를 사용한 E2E 테스트 필수 구현
- 95%+ 테스트 커버리지 목표
- 모든 기능은 테스트 코드로 검증

## 🏗️ 아키텍처

### v2 API WebSocket 통신

새로운 v2 API는 WebSocket을 통한 실시간 통신을 지원합니다:

```python
# v2 API 요청 및 WebSocket 모니터링
async def send_analysis_v2(repo_path: str, progress_callback=None):
    # 1. v2 API로 시나리오 생성 요청
    response = await client.post("/api/v2/scenario/generate", json=request_data)
    
    # 2. WebSocket URL 수신
    websocket_url = response.json().get("websocket_url")
    
    # 3. WebSocket으로 실시간 진행 상황 모니터링
    result = await listen_to_progress_v2(websocket_url, progress_callback)
    return result
```

### 전략 패턴 (Strategy Pattern)

VCS 지원을 위해 전략 패턴을 사용하여 확장 가능한 구조를 제공합니다:

```python
# 향후 확장 예시
def get_analyzer(path: Path) -> Optional[RepositoryAnalyzer]:
    if (path / ".git").exists():
        return GitAnalyzer(path)
    elif (path / ".svn").exists():
        return SVNAnalyzer(path)  # 향후 구현
    elif (path / ".hg").exists():
        return MercurialAnalyzer(path)  # 향후 구현
    return None
```

### 의존성 역전 원칙

- 추상 인터페이스에 의존
- 구체적인 구현체들은 플러그인 방식으로 교체 가능
- 테스트 시 Mock 객체로 쉽게 대체

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
- 커밋 메시지는 한국어 또는 영어로 명확하게 작성
- CLAUDE.md 지침을 준수한 개발

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 지원

- **버그 리포트**: [GitHub Issues](https://github.com/testscenariomaker/cli/issues)
- **기능 요청**: [GitHub Discussions](https://github.com/testscenariomaker/cli/discussions)
- **문서**: [공식 문서](https://docs.testscenariomaker.com/cli)

## 🔧 문제 해결

### 백그라운드 실행 관련 문제

**URL 프로토콜 클릭 후 아무 반응이 없는 경우:**

1. **로그 파일 확인**
   ```bash
   # 로그 파일 위치 확인
   ts-cli config-show
   
   # 로그 파일 내용 확인 (플랫폼별)
   # macOS
   cat ~/Library/Logs/testscenariomaker-cli/ts-cli.log
   
   # Windows (PowerShell)
   Get-Content "$env:APPDATA\testscenariomaker-cli\ts-cli.log"
   
   # Linux
   cat ~/.local/share/testscenariomaker-cli/ts-cli.log
   ```

2. **프로세스 실행 확인**
   ```bash
   # macOS/Linux
   ps aux | grep ts-cli
   
   # Windows
   tasklist | findstr ts-cli
   ```

3. **URL 프로토콜 등록 확인**
   ```bash
   # macOS
   /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
   
   # Windows (레지스트리 확인)
   reg query "HKEY_CLASSES_ROOT\testscenariomaker"
   ```

**진행상황이 보이지 않는 경우:**

1. **로그 파일 활성화**
   ```ini
   # config.ini 수정
   [logging]
   file_enabled = true
   # 플랫폼별 기본 경로 자동 사용
   file_path = auto
   level = INFO
   ```

2. **실시간 로그 모니터링**
   ```bash
   # macOS
   tail -f ~/Library/Logs/testscenariomaker-cli/ts-cli.log
   
   # Windows PowerShell
   Get-Content "$env:APPDATA\testscenariomaker-cli\ts-cli.log" -Wait
   
   # Linux
   tail -f ~/.local/share/testscenariomaker-cli/ts-cli.log
   ```

3. **터미널에서 직접 실행하여 진행상황 확인**
   ```bash
   ts-cli analyze --path /path/to/repository --verbose
   ```

### 일반적인 문제 해결

**URL 프로토콜이 작동하지 않는 경우**

1. 시스템 재시작
2. 헬퍼 앱을 한 번 더블클릭하여 실행
3. 다음 명령어로 URL 스킴 등록 확인:
```bash
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -dump | grep testscenariomaker
```

## 📊 상태

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)
![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)

---

**TestscenarioMaker CLI**는 개발자의 생산성 향상을 위해 지속적으로 발전하고 있습니다. v2 API WebSocket 지원과 Custom URL Protocol로 더욱 직관적이고 효율적인 워크플로우를 제공합니다. 🚀