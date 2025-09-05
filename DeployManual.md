  * **Part A:** **개발자/DevOps 담당자**를 위한 `deploy-package.zip` 생성 가이드 (CI 서버에서 수행)
  * **Part B:** **시스템 운영자**를 위한 폐쇄망 서버 배포 매뉴얼 (운영 서버에서 수행)
  * **Part C:** **Jenkins 관리자**를 위한 멀티브랜치 파이프라인 설정 가이드

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

-----

## Part C: Jenkins 멀티브랜치 파이프라인 설정 가이드

### 1\. Jenkins 멀티브랜치 파이프라인 생성

#### 1.1. 루트 멀티브랜치 파이프라인 (cm-docs-pipeline)

1. Jenkins 대시보드에서 **"New Item"** 클릭
2. 이름 입력: `cm-docs-pipeline`
3. 타입 선택: **"Multibranch Pipeline"**
4. **Branch Sources** 설정:
   - Add source → Git
   - Repository URL: `https://github.com/recrash/cm-docs.git`
   - Credentials: GitHub 자격증명 추가
   - **Behaviors**:
     - Discover branches: 모든 브랜치
     - Filter by name (wildcards): `main develop feature/* hotfix/*`

5. **Build Configuration**:
   - Mode: by Jenkinsfile
   - Script Path: `Jenkinsfile`

6. **Scan Multibranch Pipeline Triggers**:
   - ✅ Periodically if not otherwise run
   - Interval: 1 minute

7. **Properties**:
   - ❌ **Lightweight checkout 비활성화** (중요!)

#### 1.2. CLI 서브 파이프라인 (cli-pipeline)

1. **"New Item"** → 이름: `cli-pipeline` → **"Pipeline"** (일반 파이프라인)
2. **Pipeline** 섹션에서 Definition: **Pipeline script from SCM** 선택
3. **SCM**: Git
   - Repository URL: `https://github.com/recrash/cm-docs.git`
   - Credentials: GitHub 자격증명
   - **Branches to build**: `*/${BRANCH_PARAM}`
   - **Script Path**: `cli/Jenkinsfile`
   
4. **This project is parameterized** 체크:
   - Add Parameter → String Parameter
   - Name: `BRANCH_PARAM`
   - Default Value: `main`
   - Description: `Branch to build`

5. **Build Triggers**:
   - ❌ Lightweight checkout 비활성화

#### 1.3. 다른 서브 파이프라인들

동일한 방식으로 다음 파이프라인들을 생성:
- `webservice-backend-pipeline` (Script Path: `webservice/Jenkinsfile.backend`)
- `webservice-frontend-pipeline` (Script Path: `webservice/Jenkinsfile.frontend`)
- `autodoc-service-pipeline` (Script Path: `autodoc_service/Jenkinsfile`)

### 2\. Windows Jenkins 에이전트 설정

#### 2.1. Jenkins 노드 추가

1. **Manage Jenkins** → **Manage Nodes and Clouds**
2. **New Node** 클릭:
   - Node name: `windows-build-agent`
   - Type: Permanent Agent
   
3. **Node Properties**:
   ```
   Remote root directory: C:\jenkins-agent
   Labels: windows cli-build
   Usage: Use this node as much as possible
   Launch method: Launch agent by connecting it to the controller
   ```

#### 2.2. Windows 에이전트 설치

Windows 빌드 서버에서:
```powershell
# Jenkins 에이전트 디렉토리 생성
New-Item -ItemType Directory -Force -Path "C:\jenkins-agent"

# agent.jar 다운로드
Invoke-WebRequest -Uri "http://jenkins-server:8080/jnlpJars/agent.jar" -OutFile "C:\jenkins-agent\agent.jar"

# 에이전트 시작 (Jenkins에서 제공하는 secret 사용)
java -jar agent.jar -jnlpUrl http://jenkins-server:8080/computer/windows-build-agent/slave-agent.jnlp -secret [SECRET_KEY]
```

### 3\. CLI 파이프라인 특별 설정

#### 3.1. 필요한 소프트웨어 설치

Windows 빌드 에이전트에 다음 소프트웨어 설치 필수:
- **Python 3.13**: CLI 개발 환경
- **NSIS**: Windows 설치 프로그램 생성
- **Git**: 소스코드 체크아웃

#### 3.2. 환경 변수 설정

Jenkins 노드 설정에서 환경 변수 추가:
```
PYTHONIOENCODING=UTF-8
LANG=en_US.UTF-8
WHEELHOUSE_PATH=C:\deploys\packages\wheelhouse
```

#### 3.3. 파이프라인별 특별 설정

**CLI Pipeline (cli/Jenkinsfile)**:
- ✅ 테스트 실패 허용: `returnStatus: true`
- ✅ Coverage report: `allowMissing: true`
- ✅ NSIS 경로 자동 감지
- ✅ UTF-8 인코딩 강제

### 4\. 문제 해결 가이드

#### 4.1. Lightweight Checkout 문제

**증상**: Jenkins가 오래된 커밋을 체크아웃함
**해결**: 
1. Pipeline 설정에서 **"Lightweight checkout"** 비활성화
2. 또는 명시적 GitSCM checkout 사용:
```groovy
checkout([
    $class: 'GitSCM',
    branches: [[name: "*/${params.BRANCH}"]],
    extensions: [[$class: 'CleanBeforeCheckout']]
])
```

#### 4.2. 인코딩 에러

**증상**: `'charmap' codec can't encode characters`
**해결**:
1. Jenkinsfile에 환경 변수 추가:
```groovy
environment {
    PYTHONIOENCODING = 'UTF-8'
    LANG = 'en_US.UTF-8'
}
```
2. 한글 텍스트를 영문으로 변경

#### 4.3. NSIS Installer 경로 문제

**증상**: `Installer not created!` 에러
**해결**:
```groovy
// NSIS는 scripts/ 디렉토리에 생성됨
bat '''
    makensis scripts\\setup_win.nsi
    if exist scripts\\TestscenarioMaker-CLI-Setup.exe (
        move /Y scripts\\TestscenarioMaker-CLI-Setup.exe dist\\
    )
'''
```

#### 4.4. 테스트 중단 (KeyboardInterrupt)

**증상**: 테스트 중 KeyboardInterrupt 발생
**해결**:
```groovy
// 테스트 실패해도 계속 진행
bat(returnStatus: true, script: '''
    .venv\\Scripts\\pytest.exe tests\\unit\\ -v
''')
```

### 5\. 파이프라인 모니터링

#### 5.1. Blue Ocean 사용

1. **Blue Ocean** 플러그인 설치
2. 파이프라인 실시간 모니터링
3. 병렬 실행 상태 시각화

#### 5.2. 파이프라인 로그 확인

```powershell
# Jenkins 로그 위치
Get-Content "C:\ProgramData\Jenkins\.jenkins\jobs\cli-pipeline\builds\lastBuild\log"

# 에이전트 로그
Get-Content "C:\jenkins-agent\remoting\logs\remoting.log"
```

### 6\. 권장 Jenkins 플러그인

- **Pipeline**: 파이프라인 기본 기능
- **Git**: Git 저장소 연동
- **Blue Ocean**: 시각적 파이프라인 관리
- **HTML Publisher**: Coverage report 표시
- **JUnit**: 테스트 결과 표시
- **Workspace Cleanup**: 작업 공간 자동 정리