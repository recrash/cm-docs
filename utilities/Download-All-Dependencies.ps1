# =================================================================
# 폐쇄망 CI/CD를 위한 '의존성 씨앗' 수확 스크립트 (Constraints 반영)
# =================================================================
# 실행 방법:
# 1. 인터넷이 연결된 PC에서 이 스크립트를 프로젝트 루트에 저장
# 2. PowerShell을 관리자 권한으로 실행 후 프로젝트 루트로 이동
# 3. 스크립트 실행: .\Download-All-Dependencies.ps1
# =================================================================

$ProjectRoot = (Get-Location).Path
$WheelhouseDir = Join-Path $ProjectRoot "wheelhouse" # 최종 결과물 폴더

# --- 준비 ---
Write-Host "🚀 'wheelhouse' 폴더를 준비합니다..." -ForegroundColor Yellow
if (-not (Test-Path $WheelhouseDir)) {
    New-Item -Path $WheelhouseDir -ItemType Directory | Out-Null
    Write-Host "    - 새로운 'wheelhouse' 폴더를 생성했습니다."
} else {
    Write-Host "    - 기존 'wheelhouse' 폴더에 누락된 파일만 추가합니다."
}

# --- 서비스별 환경 설정 및 다운로드 ---
$Services = @(
    @{Dir="webservice"; VenvDir=".venv"},
    @{Dir="autodoc_service"; VenvDir=".venv312"},
    @{Dir="cli"; VenvDir=".venv"}
)

# --- 모든 의존성 다운로드 ---
Write-Host "🚀 모든 Python 의존성 .whl 파일을 수확합니다..." -ForegroundColor Yellow
foreach ($service in $Services) {
    $servicePath = Join-Path $ProjectRoot $service.Dir
    $reqFile = Join-Path $servicePath "requirements.txt"
    $reqDevFile = Join-Path $servicePath "requirements-dev.txt"
    $venvPath = Join-Path $servicePath $service.VenvDir
    
    if ((Test-Path $reqFile) -and (Test-Path $venvPath)) {
        # 가상환경의 pip 경로
        $pipPath = Join-Path $venvPath "Scripts\pip.exe"
        
        # ✨ 제약 조건 파일 경로를 동적으로 확인
        $constraintFile = Join-Path $servicePath "pip.constraints.txt"
        
        # 운영 의존성 다운로드
        if (Test-Path $constraintFile) {
            Write-Host "    - '$reqFile' 파일의 의존성을 제약 조건('-c')을 포함하여 다운로드합니다."
            & $pipPath download -r $reqFile -d $WheelhouseDir --prefer-binary -c $constraintFile
        } else {
            Write-Host "    - '$reqFile' 파일의 의존성을 다운로드합니다."
            & $pipPath download -r $reqFile -d $WheelhouseDir --prefer-binary
        }
        
        # 개발 의존성 다운로드 (requirements-dev.txt가 있는 경우)
        if (Test-Path $reqDevFile) {
            Write-Host "    - '$reqDevFile' 파일의 개발 의존성을 다운로드합니다."
            if (Test-Path $constraintFile) {
                & $pipPath download -r $reqDevFile -d $WheelhouseDir --prefer-binary -c $constraintFile
            } else {
                & $pipPath download -r $reqDevFile -d $WheelhouseDir --prefer-binary
            }
        }
    } else {
        if (-not (Test-Path $reqFile)) {
            Write-Host "    - 경고: '$reqFile' 파일을 찾을 수 없습니다." -ForegroundColor DarkYellow
        }
        if (-not (Test-Path $venvPath)) {
            Write-Host "    - 경고: '$venvPath' 가상환경을 찾을 수 없습니다." -ForegroundColor DarkYellow
        }
    }
}

# --- 빌드 도구 자체도 다운로드 (첫 번째 사용 가능한 환경 사용) ---
Write-Host "    - 빌드 필수 도구(build, wheel)를 다운로드합니다."
foreach ($service in $Services) {
    $venvPath = Join-Path $ProjectRoot "$($service.Dir)\$($service.VenvDir)"
    
    if (Test-Path $venvPath) {
        $pipPath = Join-Path $venvPath "Scripts\pip.exe"
        & $pipPath download build wheel -d $WheelhouseDir
        break
    }
}

# --- npm 의존성 캐시 수집 ---
Write-Host "🚀 npm 의존성 캐시를 수집합니다..." -ForegroundColor Yellow
$NpmCacheDir = Join-Path $ProjectRoot "npm-cache"
if (-not (Test-Path $NpmCacheDir)) {
    New-Item -Path $NpmCacheDir -ItemType Directory | Out-Null
    Write-Host "    - 새로운 'npm-cache' 폴더를 생성했습니다."
} else {
    Write-Host "    - 기존 'npm-cache' 폴더에 누락된 패키지만 추가합니다."
}

# webservice frontend npm 의존성 수집
$FrontendPath = Join-Path $ProjectRoot "webservice\frontend"
$PackageJsonPath = Join-Path $FrontendPath "package.json"
$PackageLockPath = Join-Path $FrontendPath "package-lock.json"

if ((Test-Path $PackageJsonPath) -and (Test-Path $PackageLockPath)) {
    Write-Host "    - webservice frontend의 npm 의존성을 수집합니다."
    Push-Location $FrontendPath
    npm config set cache $NpmCacheDir
    npm ci --prefer-offline --no-audit
    Write-Host "    - npm 캐시 수집 완료"
    Pop-Location
} else {
    Write-Host "    - 경고: webservice/frontend의 package.json 또는 package-lock.json을 찾을 수 없습니다." -ForegroundColor DarkYellow
}

Write-Host "✅ 성공! '$WheelhouseDir' 및 '$NpmCacheDir' 폴더에 모든 의존성 씨앗이 준비되었습니다." -ForegroundColor Green
Write-Host "   이제 'wheelhouse'와 'npm-cache' 폴더를 소스코드와 함께 인트라넷 환경으로 가져가세요."