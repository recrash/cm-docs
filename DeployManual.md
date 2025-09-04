  * **Part A:** **개발자/DevOps 담당자**를 위한 `deploy-package.zip` 생성 가이드 (CI 서버에서 수행)
  * **Part B:** **시스템 운영자**를 위한 폐쇄망 서버 배포 매뉴얼 (운영 서버에서 수행)

-----

## Part A: "All-in-One" 배포 패키지 생성 가이드

> 🎯 **목표**: 인터넷이 되는 CI/개발 서버에서, 폐쇄망 운영 서버 배포에 필요한 모든 것을 담은 `deploy-package.zip` 파일 하나를 만드는 것.

### A-1. "의존성 씨앗" 수확 (최초 1회 및 의존성 변경 시)

폐쇄망 CI/CD를 시작하기 전, 인터넷이 연결된 PC에서 앞으로 사용할 **모든 Python 및 Node.js 의존성**을 미리 확보해야 합니다.

1.  프로젝트 루트에서 `Download-All-Dependencies.ps1` (Windows) 또는 `download-all-dependencies.sh` (Linux/macOS) 스크립트를 실행합니다.
2.  스크립트 실행 후 다음 폴더들이 생성됩니다:
    - **`wheelhouse/`**: 모든 Python .whl 파일
    - **`npm-cache/`**: 모든 Node.js 패키지 (**신규 추가**)

**실행 예시**:
```bash
# Windows
.\Download-All-Dependencies.ps1

# Linux/macOS  
./download-all-dependencies.sh

# 결과: wheelhouse/ 및 npm-cache/ 폴더 생성
```

이 폴더들은 프로젝트의 **모든 의존성(Python + Node.js)**을 담는 '저장소' 역할을 합니다.


### A-2. `deploy-package.zip` 생성

이제 CI/CD 파이프라인(인트라넷 Jenkins)이 실행할 패키징 스크립트를 준비합니다. 이 스크립트는 **A-1**에서 만든 `wheelhouse` 폴더가 프로젝트 루트에 존재한다고 가정하고 작동합니다.

#### `Create-Deploy-Package.ps1` (Windows Jenkins용)

```powershell
# (이전 답변에서 제공한 스크립트와 동일)
# ... 스크립트 내용 ...
# 3. 초기 데이터 복사 단계 이후에, wheelhouse 폴더를 복사하는 로직 추가
Write-Host "    - 오프라인 의존성('wheelhouse', 'npm-cache')을 패키지에 포함합니다."
$wheelhouseDir = Join-Path $ProjectRoot "wheelhouse"
$npmCacheDir = Join-Path $ProjectRoot "npm-cache"
$targetDepsDir = Join-Path $PackageDir "dependencies"
Copy-Item -Path $wheelhouseDir -Destination $targetDepsDir -Recurse -Force
Copy-Item -Path $npmCacheDir -Destination (Join-Path $PackageDir "npm-cache") -Recurse -Force
# ... 이후 압축 단계로 ...
```

#### `create-deploy-package.sh` (Linux/macOS Jenkins용)

```bash
# (이전 답변에서 제공한 스크립트와 동일)
# ... 스크립트 내용 ...
# 3. 초기 데이터 복사 단계 이후에, wheelhouse 폴더를 복사하는 로직 추가
echo "    - 오프라인 의존성('wheelhouse', 'npm-cache')을 패키지에 포함합니다."
WHEELHOUSE_DIR="$PROJECT_ROOT/wheelhouse"
NPM_CACHE_DIR="$PROJECT_ROOT/npm-cache"
TARGET_DEPS_DIR="$PACKAGE_DIR/dependencies"
TARGET_NPM_DIR="$PACKAGE_DIR/npm-cache"
mkdir -p "$TARGET_DEPS_DIR" "$TARGET_NPM_DIR"
cp -r "$WHEELHOUSE_DIR"/* "$TARGET_DEPS_DIR/"
cp -r "$NPM_CACHE_DIR"/* "$TARGET_NPM_DIR/"
# ... 이후 압축 단계로 ...
```

-----

-----

## Part B: 폐쇄망 운영 환경 시스템 배포 매뉴얼 (최종 개정판)

### 1\. 개요

본 문서는 '변경관리문서 생성 자동화 시스템'을 외부 인터넷이 차단된 \*\*인트라넷 운영 서버(Windows Server)\*\*에 배포하고 설정하는 절차를 안내합니다.

### 2\. 사전 준비 사항

1.  **배포 패키지**: CI 서버에서 생성된 `deploy-package.zip` 파일 1개.
2.  **서버 환경**:
      * OS: Windows Server
      * Python: **Python 3.13** 과 **Python 3.12** 모두 설치
      * NSSM: `nssm.exe` 파일
      * Nginx: (웹 프록시로 사용할 경우)

### 3\. 최초 배포 절차

#### 3.1. 배포 패키지 압축 해제

1.  `deploy-package.zip` 파일을 운영 서버의 **`C:\`** 드라이브로 복사 후 압축을 해제합니다.
2.  `C:\deploys` 폴더가 아래 구조로 생성되었는지 확인합니다.
    ```
    C:\deploys
    ├── apps\       # 프론트엔드 빌드 결과물
    ├── data\       # 초기 데이터 (모델, 템플릿)
    └── packages\   # 설치 파일 (.whl) 및 의존성
    ```

#### 3.2. Python 가상환경 생성 및 오프라인 설치

**PowerShell**을 **관리자 권한**으로 실행하여 아래 명령어를 순서대로 입력합니다.

1.  **webservice (Python 3.13) 설정**

    ```powershell
    # 가상환경 생성 (.venv)
    New-Item -ItemType Directory -Force -Path "C:\deploys\apps\webservice"
    py -3.13 -m venv "C:\deploys\apps\webservice\.venv"

    # 오프라인 의존성 설치
    $whlAppFile = Get-ChildItem -Path "C:\deploys\packages\webservice\*.whl" | Select-Object -First 1 -ExpandProperty FullName
    $dependencyPath = "C:\deploys\packages\dependencies"
    & "C:\deploys\apps\webservice\.venv\Scripts\pip.exe" install --no-index --find-links="$dependencyPath" $whlAppFile
    ```

2.  **autodoc\_service (Python 3.12) 설정**

    ```powershell
    # 가상환경 생성 (.venv312)
    New-Item -ItemType Directory -Force -Path "C:\deploys\apps\autodoc_service"
    py -3.12 -m venv "C:\deploys\apps\autodoc_service\.venv312"

    # 오프라인 의존성 설치
    $whlAppFile = Get-ChildItem -Path "C:\deploys\packages\autodoc_service\*.whl" | Select-Object -First 1 -ExpandProperty FullName
    $dependencyPath = "C:\deploys\packages\dependencies"
    & "C:\deploys\apps\autodoc_service\.venv312\Scripts\pip.exe" install --no-index --find-links="$dependencyPath" $whlAppFile
    ```

#### 3.3. Windows 서비스 등록 (NSSM)

1.  **webservice 등록 (`nssm install webservice`)**

      * **Application 탭**
          * Path: `C:\deploys\apps\webservice\.venv\Scripts\python.exe`
          * Startup directory: `C:\deploys\apps\webservice`
          * Arguments: `-m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
      * **Environment 탭**
          * `WEBSERVICE_DATA_PATH=C:\deploys\data\webservice`

2.  **autodoc\_service 등록 (`nssm install autodoc_service`)**

      * **Application 탭**
          * Path: `C:\deploys\apps\autodoc_service\.venv312\Scripts\python.exe`
          * Startup directory: `C:\deploys\apps\autodoc_service`
          * Arguments: `-m uvicorn app.main:app --host 0.0.0.0 --port 8001`
      * **Environment 탭**
          * `AUTODOC_DATA_PATH=C:\deploys\data\autodoc_service`

#### 3.4. 서비스 시작 및 확인

```powershell
nssm start webservice
nssm start autodoc_service
nssm status webservice
nssm status autodoc_service
```

  * **로그 파일 위치**: `C:\deploys\data\[서비스이름]\logs`

### 4\. Nginx 연동 가이드 (선택사항)

Nginx를 Port 80으로 실행하여 각 서비스로 요청을 분배(Reverse Proxy)합니다.

1.  Nginx 설치 폴더의 `conf/nginx.conf` 파일을 수정합니다.
2.  `http` 블록 안에 아래 `server` 블록 내용을 추가하거나 수정합니다.

<!-- end list -->

```nginx
# nginx.conf 예시
server {
    listen 80;
    server_name your_server_ip_or_domain; # 서버 IP 또는 도메인

    # 기본 UI 및 Webservice API (Port 8000)
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 지원
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Autodoc Service API (Port 8001)
    location /autodoc/ {
        proxy_pass http://localhost:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3.  Nginx를 재시작합니다. 이제 웹 브라우저에서 `http://서버주소`로 접속하면 `webservice` UI가 표시되고, 프론트엔드에서 `/autodoc/` 경로로 보내는 API 요청은 `autodoc_service`로 자동 전달됩니다.

### 5\. 시스템 업데이트 절차

1.  **서비스 중지**: `nssm stop webservice`, `nssm stop autodoc_service`
2.  **신규 패키지 적용**: 새로운 `deploy-package.zip` 파일의 압축을 풀어 `C:\deploys`에 덮어씁니다. (`data` 폴더는 영향을 받지 않습니다.)
3.  **패키지 재설치**: **3.2절**의 PowerShell 설치 명령어들을 다시 실행하여 패키지를 업그레이드합니다.
4.  **서비스 시작**: `nssm start webservice`, `nssm start autodoc_service`