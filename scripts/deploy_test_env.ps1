# scripts/deploy_test_env.ps1
# 브랜치별 테스트 인스턴스 자동 배포 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][int]$BackPort,
    [Parameter(Mandatory=$true)][int]$AutoPort,
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$NginxConfDir,
    [Parameter(Mandatory=$true)][string]$WebSrc,      # repo/webservice
    [Parameter(Mandatory=$true)][string]$AutoSrc,     # repo/autodoc_service
    [Parameter(Mandatory=$true)][string]$WebBackDst,  # C:\deploys\tests\{BID}\webservice\backend
    [Parameter(Mandatory=$true)][string]$WebFrontDst, # C:\deploys\tests\{BID}\webservice\frontend
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\tests\{BID}\autodoc
    [Parameter(Mandatory=$true)][string]$UrlPrefix    # "/tests/{BID}/"
)

$ErrorActionPreference = "Stop"

Write-Host "===========================================`n"
Write-Host "🚀 테스트 인스턴스 배포 시작`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• Backend Port: $BackPort"
Write-Host "• AutoDoc Port: $AutoPort"
Write-Host "• URL Prefix: $UrlPrefix"
Write-Host "===========================================`n"

try {
    # 1. 백엔드/autodoc 파일 배치
    Write-Host "📦 1단계: 백엔드 및 AutoDoc 파일 배치 중..."
    
    # 테스트 인스턴스용 데이터 경로 생성 (먼저 생성)
    $TestWebDataPath = "$WebBackDst\..\..\data\webservice"
    $TestAutoDataPath = "$AutoDst\..\data\autodoc_service"
    
    New-Item -ItemType Directory -Force -Path $WebBackDst, $AutoDst, $TestWebDataPath, $TestAutoDataPath | Out-Null
    Write-Host "디렉토리 생성 완료: $WebBackDst, $AutoDst"
    Write-Host "테스트 데이터 디렉토리 생성 완료: $TestWebDataPath, $TestAutoDataPath"
    
    # 백엔드 파일 복사 (app 디렉토리, config 파일 포함)
    Copy-Item -Recurse -Force "$WebSrc\app" "$WebBackDst\app"
    Copy-Item -Force "$WebSrc\main.py" "$WebBackDst\main.py"
    Copy-Item -Force "$WebSrc\requirements.txt" "$WebBackDst\requirements.txt"
    if (Test-Path "$WebSrc\pip.constraints.txt") {
        Copy-Item -Force "$WebSrc\pip.constraints.txt" "$WebBackDst\pip.constraints.txt"
    }
    
    # 테스트 인스턴스용 config 파일을 데이터 경로에 복사
    if (Test-Path "$WebSrc\config.test.json") {
        Copy-Item -Force "$WebSrc\config.test.json" "$TestWebDataPath\config.json"
        Write-Host "테스트용 config 파일 복사 완료: $TestWebDataPath\config.json"
    } elseif (Test-Path "$WebSrc\config.json") {
        Copy-Item -Force "$WebSrc\config.json" "$TestWebDataPath\config.json"
        Write-Host "기본 config 파일 복사 완료: $TestWebDataPath\config.json"
    } else {
        Write-Warning "config 파일을 찾을 수 없습니다"
    }
    Write-Host "백엔드 파일 복사 완료"
    
    # AutoDoc 파일 복사
    Copy-Item -Recurse -Force "$AutoSrc\*" $AutoDst
    Write-Host "AutoDoc 파일 복사 완료"
    
    # 2. 가상환경 및 의존성 설치 (휠하우스 활용)
    Write-Host "`n📦 2단계: 가상환경 및 의존성 설치 중..."
    
    # 공유 휠하우스 경로
    $WheelhousePath = "C:\deploys\packages\wheelhouse"
    
    # 웹서비스 가상환경 생성 및 의존성 설치
    Write-Host "웹서비스 가상환경 설정 중..."
    & $Py -m venv "$WebBackDst\.venv"
    
    if (Test-Path "$WheelhousePath\*.whl") {
        Write-Host "휠하우스 발견 - 오프라인 고속 설치"
        $ConstraintFile = "$WebBackDst\pip.constraints.txt"
        if (Test-Path $ConstraintFile) {
            & "$WebBackDst\.venv\Scripts\pip.exe" install -r "$WebBackDst\requirements.txt" -c $ConstraintFile --no-index --find-links="$WheelhousePath"
        } else {
            & "$WebBackDst\.venv\Scripts\pip.exe" install -r "$WebBackDst\requirements.txt" --no-index --find-links="$WheelhousePath"
        }
    } else {
        Write-Host "휠하우스 없음 - 온라인 설치"
        $ConstraintFile = "$WebBackDst\pip.constraints.txt"
        if (Test-Path $ConstraintFile) {
            & "$WebBackDst\.venv\Scripts\pip.exe" install -r "$WebBackDst\requirements.txt" -c $ConstraintFile
        } else {
            & "$WebBackDst\.venv\Scripts\pip.exe" install -r "$WebBackDst\requirements.txt"
        }
    }
    Write-Host "웹서비스 의존성 설치 완료"
    
    # AutoDoc 가상환경 생성 및 의존성 설치
    Write-Host "AutoDoc 가상환경 설정 중..."
    & $Py -m venv "$AutoDst\.venv312"
    
    if (Test-Path "$WheelhousePath\*.whl") {
        Write-Host "휠하우스 발견 - 오프라인 고속 설치"
        & "$AutoDst\.venv312\Scripts\pip.exe" install -r "$AutoDst\requirements.txt" --no-index --find-links="$WheelhousePath"
    } else {
        Write-Host "휠하우스 없음 - 온라인 설치"
        & "$AutoDst\.venv312\Scripts\pip.exe" install -r "$AutoDst\requirements.txt"
    }
    Write-Host "AutoDoc 의존성 설치 완료"
    
    # 3. 프론트엔드 빌드 (Vite 기본)
    Write-Host "`n🎨 3단계: 프론트엔드 빌드 중..."
    
    Push-Location "$WebSrc\frontend"
    try {
        if (Test-Path "package-lock.json" -or Test-Path "package.json") {
            Write-Host "npm 의존성 설치 중..."
            npm ci
            
            Write-Host "Vite 빌드 시작 (base: $UrlPrefix)"
            npm run build -- --base="$UrlPrefix"
            Write-Host "Vite 빌드 완료"
            
            # CRA 사용 시 대신 사용할 명령어:
            # $env:PUBLIC_URL = $UrlPrefix
            # npm run build
        } else {
            throw "package.json 파일을 찾을 수 없습니다"
        }
    } finally {
        Pop-Location
    }
    
    # 빌드 결과 복사
    New-Item -ItemType Directory -Force -Path $WebFrontDst | Out-Null
    if (Test-Path "$WebSrc\frontend\dist") {
        Copy-Item -Recurse -Force "$WebSrc\frontend\dist\*" $WebFrontDst
        Write-Host "프론트엔드 빌드 결과 복사 완료"
    } else {
        throw "프론트엔드 빌드 결과가 없습니다: dist 폴더를 찾을 수 없음"
    }
    
    # 4. NSSM 서비스 등록/재시작
    Write-Host "`n⚙️ 4단계: NSSM 서비스 등록 중..."
    
    # 기존 서비스 정리 (에러 무시)
    & $Nssm stop "cm-web-$Bid" 2>$null
    & $Nssm remove "cm-web-$Bid" confirm 2>$null
    & $Nssm stop "cm-autodoc-$Bid" 2>$null
    & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
    
    # 로그 디렉토리 생성
    $LogDir = "$WebBackDst\..\..\logs"
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    
    # 웹서비스 백엔드 서비스 등록
    Write-Host "웹서비스 백엔드 서비스 등록 중..."
    & $Nssm install "cm-web-$Bid" $Py "-m uvicorn main:app --host 0.0.0.0 --port $BackPort"
    & $Nssm set "cm-web-$Bid" AppDirectory $WebBackDst
    & $Nssm set "cm-web-$Bid" AppStdout "$LogDir\web-$Bid.out.log"
    & $Nssm set "cm-web-$Bid" AppStderr "$LogDir\web-$Bid.err.log"
    
    # 테스트 인스턴스용 환경변수 설정
    & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath"
    & $Nssm restart "cm-web-$Bid"
    Write-Host "웹서비스 백엔드 서비스 시작 완료 (Port: $BackPort)"
    
    # AutoDoc 서비스 등록
    Write-Host "AutoDoc 서비스 등록 중..."
    & $Nssm install "cm-autodoc-$Bid" $Py "-m uvicorn main:app --host 0.0.0.0 --port $AutoPort"
    & $Nssm set "cm-autodoc-$Bid" AppDirectory $AutoDst
    & $Nssm set "cm-autodoc-$Bid" AppStdout "$AutoDst\..\logs\autodoc-$Bid.out.log"
    & $Nssm set "cm-autodoc-$Bid" AppStderr "$AutoDst\..\logs\autodoc-$Bid.err.log"
    
    # 테스트 인스턴스용 환경변수 설정
    & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath"
    & $Nssm restart "cm-autodoc-$Bid"
    Write-Host "AutoDoc 서비스 시작 완료 (Port: $AutoPort)"
    
    # 5. Nginx location 파일 생성 + reload
    Write-Host "`n🌐 5단계: Nginx 설정 적용 중..."
    
    $templatePath = "$PSScriptRoot\..\infra\nginx\tests.template.conf"
    if (-not (Test-Path $templatePath)) {
        throw "Nginx 템플릿 파일을 찾을 수 없습니다: $templatePath"
    }
    
    $tpl = Get-Content -Raw $templatePath
    $conf = $tpl.Replace("{{BID}}", $Bid).Replace("{{BACK_PORT}}", "$BackPort").Replace("{{AUTO_PORT}}", "$AutoPort")
    $out = Join-Path $NginxConfDir "tests-$Bid.conf"
    $conf | Set-Content -Encoding UTF8 $out
    
    Write-Host "Nginx 설정 파일 생성 완료: $out"
    
    # Nginx 리로드
    & $Nginx -s reload
    Write-Host "Nginx 리로드 완료"
    
    # 6. 서비스 시작 확인
    Write-Host "`n✅ 6단계: 서비스 시작 확인 중..."
    Start-Sleep -Seconds 5
    
    $webStatus = & $Nssm status "cm-web-$Bid"
    $autodocStatus = & $Nssm status "cm-autodoc-$Bid"
    
    Write-Host "웹서비스 상태: $webStatus"
    Write-Host "AutoDoc 상태: $autodocStatus"
    
    if ($webStatus -ne "SERVICE_RUNNING") {
        Write-Warning "웹서비스가 정상 실행되지 않았습니다"
    }
    if ($autodocStatus -ne "SERVICE_RUNNING") {
        Write-Warning "AutoDoc 서비스가 정상 실행되지 않았습니다"
    }
    
    Write-Host "`n===========================================`n"
    Write-Host "🎉 테스트 인스턴스 배포 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    Write-Host "• 웹서비스: http://localhost:$BackPort"
    Write-Host "• AutoDoc: http://localhost:$AutoPort"
    Write-Host "• URL: /tests/$Bid/"
    Write-Host "• 로그: $LogDir"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "테스트 인스턴스 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리 시도
    Write-Host "실패 후 정리 시도 중..."
    & $Nssm stop "cm-web-$Bid" 2>$null
    & $Nssm remove "cm-web-$Bid" confirm 2>$null
    & $Nssm stop "cm-autodoc-$Bid" 2>$null
    & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
    
    $confFile = Join-Path $NginxConfDir "tests-$Bid.conf"
    Remove-Item $confFile -Force -ErrorAction SilentlyContinue
    & $Nginx -s reload 2>$null
    
    throw $_.Exception
}