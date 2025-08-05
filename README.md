# TestscenarioMaker CLI

TestscenarioMaker를 위한 로컬 저장소 분석 CLI 도구입니다.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

## 🎯 주요 기능

- **Git 저장소 분석**: 로컬 Git 저장소의 변경사항을 자동으로 분석
- **전략 패턴 기반**: 향후 SVN, Mercurial 등 다른 VCS 지원 확장 가능
- **크로스플랫폼**: Windows와 macOS 모두 지원
- **한국어 UI**: 모든 사용자 인터페이스가 한국어로 제공
- **풍부한 출력**: 텍스트와 JSON 형식 출력 지원
- **URL 프로토콜**: `testscenariomaker://` 프로토콜 지원으로 웹에서 직접 실행

## 🚀 빠른 시작

### 설치

#### Windows
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `TestscenarioMaker-CLI-Setup.exe` 다운로드
2. 설치 프로그램 실행 후 안내에 따라 설치

#### macOS
1. [최신 릴리스](https://github.com/testscenariomaker/cli/releases)에서 `.dmg` 파일 다운로드
2. DMG 파일을 마운트하고 `install.sh` 실행

#### 개발자 설치 (pip)
```bash
git clone https://github.com/testscenariomaker/cli.git
cd cli
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

### URL 프로토콜 사용법

설치 후 웹 브라우저에서 `testscenariomaker://` 링크를 클릭하면 CLI가 자동으로 실행됩니다:

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
```

## 📁 프로젝트 구조

```
testscenariomaker-cli/
├── src/ts_cli/              # 메인 소스 코드
│   ├── main.py              # CLI 진입점
│   ├── cli_handler.py       # 비즈니스 로직
│   ├── api_client.py        # API 클라이언트
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
│   └── create_dmg.py      # macOS DMG (URL 프로토콜 등록)
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
# testscenariomaker:// URL 프로토콜이 Info.plist에 등록됩니다
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

## 📊 상태

![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)

---

**TestscenarioMaker CLI**는 개발자의 생산성 향상을 위해 지속적으로 발전하고 있습니다. 🚀