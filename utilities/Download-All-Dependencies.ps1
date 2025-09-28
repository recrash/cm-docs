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

# --- npm 의존성 완전 오프라인 수집 ---
Write-Host "🚀 npm 의존성을 완전 오프라인 형태로 수집합니다..." -ForegroundColor Yellow

# webservice frontend npm 의존성 수집
$FrontendPath = Join-Path $ProjectRoot "webservice\frontend"
$PackageJsonPath = Join-Path $FrontendPath "package.json"
$PackageLockPath = Join-Path $FrontendPath "package-lock.json"

if ((Test-Path $PackageJsonPath) -and (Test-Path $PackageLockPath)) {
    Write-Host "    - webservice frontend의 npm 의존성을 완전 설치 후 복사합니다."
    Push-Location $FrontendPath

    # 1. 완전한 node_modules 설치
    npm ci
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    - 오류: npm ci 실패" -ForegroundColor Red
        Pop-Location
        exit 1
    }

    # 2. 대상 디렉토리 준비 (단일 node_modules 폴더)
    $NodeModulesTarget = "C:\deploys\packages\frontend\node_modules"
    if (Test-Path $NodeModulesTarget) {
        Write-Host "    - 기존 node_modules 폴더 제거 중..."
        Remove-Item $NodeModulesTarget -Recurse -Force
    }

    # 3. node_modules 폴더 복사 (xcopy 사용)
    Write-Host "    - node_modules 폴더를 오프라인 패키지 위치로 복사 중..."
    $xcopyCmd = "xcopy /E /I /H /Y `"node_modules`" `"$NodeModulesTarget\`" >nul 2>&1"
    cmd /c $xcopyCmd

    if ($LASTEXITCODE -ne 0) {
        Write-Host "    - 오류: node_modules 복사 실패" -ForegroundColor Red
        Pop-Location
        exit 1
    }

    Write-Host "    - npm 오프라인 패키지 준비 완료: $NodeModulesTarget"
    Pop-Location
} else {
    Write-Host "    - 경고: webservice/frontend의 package.json 또는 package-lock.json을 찾을 수 없습니다." -ForegroundColor DarkYellow
}

Write-Host "✅ 성공! 모든 의존성 패키지가 준비되었습니다." -ForegroundColor Green
Write-Host "   - Python: $WheelhouseDir"
Write-Host "   - Node.js: C:\deploys\packages\frontend\node_modules"
Write-Host "   이제 이 폴더들을 폐쇄망 환경으로 복사하세요."
Write-Host ""
Write-Host "📋 폐쇄망 환경에서의 설치 방법:" -ForegroundColor Cyan
Write-Host "   1. Python: pip install --no-index --find-links wheelhouse/ -r requirements.txt"
Write-Host "   2. Node.js: xcopy로 C:\deploys\packages\frontend\node_modules 폴더 복사"