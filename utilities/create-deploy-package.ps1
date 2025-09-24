# =================================================================
# 폐쇄망 배포용 'deploy-package.zip' 생성 스크립트
# =================================================================
# 실행 방법:
# 1. 이 스크립트를 프로젝트 루트 폴더에 저장 (예: C:\git\cm-docs\)
# 2. PowerShell을 관리자 권한으로 실행
# 3. 프로젝트 루트로 이동: cd C:\git\cm-docs
# 4. 스크립트 실행: .\Create-Deploy-Package.ps1
# =================================================================

# --- 스크립트 설정 ---
$ErrorActionPreference = "Stop" # 에러 발생 시 즉시 중지

# --- 경로 변수 정의 ---
$ProjectRoot = (Get-Location).Path
$StagingDir = Join-Path $ProjectRoot "staging"
$PackageFile = Join-Path $ProjectRoot "deploy-package.zip"

# --- 폴더 구조 정의 ---
$DeployRoot = Join-Path $StagingDir "deploys"
$PackageDir = Join-Path $DeployRoot "packages"
$DataDir = Join-Path $DeployRoot "data"
$AppsDir = Join-Path $DeployRoot "apps"

# =================================================================
# 0. 패키징 준비
# =================================================================
Write-Host "🚀 (0/5) 패키징을 위한 임시 스테이징 폴더를 준비합니다..." -ForegroundColor Yellow
if (Test-Path $StagingDir) {
    Remove-Item -Path $StagingDir -Recurse -Force
    Write-Host "    - 기존 'staging' 폴더를 삭제했습니다."
}
New-Item -Path $DeployRoot, $PackageDir, $DataDir, $AppsDir -ItemType Directory | Out-Null
Write-Host "    - 새로운 'staging/deploys' 폴더 구조를 생성했습니다."

# =================================================================
# 1. 백엔드 서비스 빌드 (.whl 생성)
# =================================================================
Write-Host "🚀 (1/5) Python 백엔드 서비스를 빌드합니다..." -ForegroundColor Yellow

# --- autodoc_service 빌드 ---
try {
    $servicePath = Join-Path $ProjectRoot "autodoc_service"
    Push-Location $servicePath
    
    Write-Host "    - 'autodoc_service' 빌드 중..."
    py -3.12 -m venv .venv312
    & ".\.venv312\Scripts\pip.exe" install setuptools build wheel --upgrade --quiet
    & ".\.venv312\Scripts\python.exe" -m build --wheel --no-isolation
    
    $targetDir = Join-Path $PackageDir "autodoc_service"
    New-Item -Path $targetDir -ItemType Directory | Out-Null
    Copy-Item -Path ".\dist\*.whl" -Destination $targetDir -Force
    Write-Host "    - 'autodoc_service' 빌드 완료!" -ForegroundColor Green
    
    Pop-Location
} catch {
    Write-Host "❌ 'autodoc_service' 빌드 중 심각한 오류가 발생했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# --- webservice 빌드 ---
try {
    $servicePath = Join-Path $ProjectRoot "webservice"
    Push-Location $servicePath

    Write-Host "    - 'webservice' 빌드 중..."
    py -3.9 -m venv .venv
    & ".\.venv\Scripts\pip.exe" install setuptools build wheel --upgrade --quiet
    & ".\.venv\Scripts\python.exe" -m build --wheel --no-isolation

    $targetDir = Join-Path $PackageDir "webservice"
    New-Item -Path $targetDir -ItemType Directory | Out-Null
    Copy-Item -Path ".\dist\*.whl" -Destination $targetDir -Force
    Write-Host "    - 'webservice' 빌드 완료!" -ForegroundColor Green

    Pop-Location
} catch {
    Write-Host "❌ 'webservice' 빌드 중 심각한 오류가 발생했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}


# =================================================================
# 2. 프론트엔드 빌드 (React)
# =================================================================
Write-Host "🚀 (2/5) React 프론트엔드를 빌드합니다..." -ForegroundColor Yellow
try {
    $frontendPath = Join-Path $ProjectRoot "webservice\frontend"
    Push-Location $frontendPath

    Write-Host "    - 의존성 설치 (npm install)..."
    npm install
    Write-Host "    - 프로덕션 빌드 (npm run build)..."
    npm run build

    $targetDir = Join-Path $AppsDir "webservice\frontend"
    Copy-Item -Path ".\dist\*" -Destination $targetDir -Recurse -Force
    Write-Host "    - 프론트엔드 빌드 완료!" -ForegroundColor Green
    
    Pop-Location
} catch {
    Write-Host "❌ 프론트엔드 빌드 중 심각한 오류가 발생했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# =================================================================
# 3. 초기 데이터 복사
# =================================================================
Write-Host "🚀 (3/5) 운영에 필요한 초기 데이터를 복사합니다..." -ForegroundColor Yellow

# --- AutoDoc 템플릿 복사 ---
Write-Host "    - 'autodoc_service'의 템플릿 파일을 복사합니다."
$sourceDir = Join-Path $ProjectRoot "autodoc_service\templates"
$targetDir = Join-Path $DataDir "autodoc_service\templates"
Copy-Item -Path $sourceDir -Destination $targetDir -Recurse -Force

# --- Webservice 프롬프트 파일 복사 ---
Write-Host "    - 'webservice'의 프롬프트 파일을 복사합니다."
$sourceDir = Join-Path $ProjectRoot "webservice\prompts"
$targetDir = Join-Path $DataDir "webservice\prompts"
Copy-Item -Path $sourceDir -Destination $targetDir -Recurse -Force

# --- 임베딩 모델 다운로드 및 복사 ---
Write-Host "    - 'webservice'의 임베딩 모델을 다운로드 및 복사합니다. (시간이 걸릴 수 있습니다)"
try {
    $servicePath = Join-Path $ProjectRoot "webservice"
    Push-Location $servicePath

    # webservice 가상환경의 python으로 다운로드 스크립트 실행
    & ".\.venv\Scripts\python.exe" ".\scripts\download_embedding_model.py"

    $sourceDir = Join-Path $servicePath "app\data\models" # 새로운 모델 저장 경로
    $targetDir = Join-Path $DataDir "webservice\models"

    # 모델 경로가 존재하는지 확인
    if (Test-Path $sourceDir) {
        Copy-Item -Path $sourceDir -Destination $targetDir -Recurse -Force
        Write-Host "    - 임베딩 모델 복사 완료!" -ForegroundColor Green
    } else {
        Write-Host "    - 경고: 모델 경로 '$sourceDir'가 존재하지 않습니다. 모델 다운로드를 건너뜁니다." -ForegroundColor Yellow
    }

    Pop-Location
} catch {
    Write-Host "❌ 임베딩 모델 처리 중 오류가 발생했습니다: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "    - 초기 데이터 준비 완료!" -ForegroundColor Green

# =================================================================
# 4. 최종 패키지 압축
# =================================================================
Write-Host "🚀 (4/5) 모든 결과물을 'deploy-package.zip' 파일로 압축합니다..." -ForegroundColor Yellow
if (Test-Path $PackageFile) {
    Remove-Item -Path $PackageFile -Force
}
Compress-Archive -Path "$DeployRoot\*" -DestinationPath $PackageFile -Force

# =================================================================
# 5. 완료
# =================================================================
Write-Host "🚀 (5/5) 모든 작업 완료!" -ForegroundColor Cyan
Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "✅ 성공! '$PackageFile' 파일이 생성되었습니다." -ForegroundColor Green
Write-Host "   이 파일을 폐쇄망 운영 서버로 전달하여 배포 매뉴얼에 따라 설치하세요."
Write-Host "-----------------------------------------------------------------" -ForegroundColor Cyan