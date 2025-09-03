# scripts/deploy_test_env.ps1
# 브랜치별 테스트 인스턴스 wheel 기반 배포 스크립트

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
    [Parameter(Mandatory=$true)][string]$WebBackDst,  # C:\deploys\test\{BID}\apps\webservice
    [Parameter(Mandatory=$true)][string]$WebFrontDst, # C:\deploys\test\{BID}\frontend
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\test\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$true)][string]$UrlPrefix,   # "/tests/{BID}/"
    [Parameter(Mandatory=$true)][string]$PackagesRoot # "C:\deploys\test\{BID}\packages"
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===========================================`n"
Write-Host "배포 시작: 테스트 인스턴스 (Wheel 기반)`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• Backend Port: $BackPort"
Write-Host "• AutoDoc Port: $AutoPort"
Write-Host "• URL Prefix: $UrlPrefix"
Write-Host "• Packages Root: $PackagesRoot"
Write-Host "===========================================`n"

try {
    # 0. 기존 소문자 폴더 정리 (대소문자 중복 방지)
    Write-Host "단계 0: 기존 폴더 정리 중..."
    $testRoot = "C:\deploys\tests"
    $currentBranch = $Bid
    $lowerBranch = $currentBranch.ToLower()
    
    # 소문자 버전 폴더가 존재하고 현재 브랜치명과 다른 경우 정리
    $lowerBranchPath = "$testRoot\$lowerBranch"
    if (($currentBranch -ne $lowerBranch) -and (Test-Path $lowerBranchPath)) {
        Write-Host "기존 소문자 브랜치 폴더 발견: $lowerBranchPath"
        
        # 기존 서비스 중지
        try {
            $oldWebService = "cm-web-$lowerBranch"
            $oldAutoService = "cm-autodoc-$lowerBranch"
            
            $webStatus = & $Nssm status $oldWebService 2>$null
            if ($webStatus) {
                Write-Host "기존 웹서비스 중지: $oldWebService"
                & $Nssm stop $oldWebService 2>$null
                & $Nssm remove $oldWebService confirm 2>$null
            }
            
            $autoStatus = & $Nssm status $oldAutoService 2>$null
            if ($autoStatus) {
                Write-Host "기존 AutoDoc 서비스 중지: $oldAutoService"
                & $Nssm stop $oldAutoService 2>$null
                & $Nssm remove $oldAutoService confirm 2>$null
            }
        } catch {
            Write-Host "기존 서비스 정리 중 오류 (무시): $($_.Exception.Message)"
        }
        
        # 기존 폴더 삭제
        try {
            Remove-Item -Path $lowerBranchPath -Recurse -Force
            Write-Host "기존 소문자 브랜치 폴더 삭제 완료: $lowerBranchPath"
        } catch {
            Write-Host "경고: 기존 폴더 삭제 실패: $($_.Exception.Message)"
        }
    }
    
    # 1. 디렉토리 구조 생성
    Write-Host "단계 1: 디렉토리 구조 생성 중..."
    
    # 테스트 브랜치별 데이터 경로
    $TestWebDataPath = "$PackagesRoot\..\data\webservice"
    $TestAutoDataPath = "$PackagesRoot\..\data\autodoc_service"
    $TestLogsPath = "$PackagesRoot\..\logs"
    
    New-Item -ItemType Directory -Force -Path $WebBackDst, $AutoDst, $WebFrontDst | Out-Null
    New-Item -ItemType Directory -Force -Path $TestWebDataPath, $TestAutoDataPath, $TestLogsPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$PackagesRoot\webservice", "$PackagesRoot\autodoc_service" | Out-Null
    
    Write-Host "디렉토리 생성 완료"
    Write-Host "  Apps: $WebBackDst, $AutoDst"
    Write-Host "  Data: $TestWebDataPath, $TestAutoDataPath"
    Write-Host "  Packages: $PackagesRoot"
    
    # 2. Config 파일 준비
    Write-Host "`n단계 2: Config 파일 준비 중..."
    
    # 웹서비스 config
    if (Test-Path "$WebSrc\config.test.json") {
        Copy-Item -Force "$WebSrc\config.test.json" "$TestWebDataPath\config.json"
        Write-Host "테스트용 config 복사: $TestWebDataPath\config.json"
    } elseif (Test-Path "$WebSrc\config.json") {
        Copy-Item -Force "$WebSrc\config.json" "$TestWebDataPath\config.json"
        Write-Host "기본 config 복사: $TestWebDataPath\config.json"
    } else {
        Write-Warning "웹서비스 config 파일을 찾을 수 없습니다"
    }
    
    # 오토독 config 및 templates
    if (Test-Path "$AutoSrc\data\templates") {
        Copy-Item -Recurse -Force "$AutoSrc\data\templates" "$TestAutoDataPath\templates"
        Write-Host "AutoDoc 템플릿 복사 완료"
    }
    
    # 3. Wheel 설치
    Write-Host "`n단계 3: Wheel 기반 서비스 설치 중..."
    
    # Python 경로 확장
    $PythonPath = $Py
    if ($PythonPath.Contains('%LOCALAPPDATA%')) {
        $PythonPath = $PythonPath.Replace('%LOCALAPPDATA%', $env:LOCALAPPDATA)
    }
    
    # 브랜치별 wheel 경로 및 글로벌 폴백
    $BranchWebWheelPath = "$PackagesRoot\webservice"
    $BranchAutoWheelPath = "$PackagesRoot\autodoc_service"
    $GlobalWheelPath = "C:\deploys\packages"
    
    # 웹서비스 설치
    Write-Host "웹서비스 설치 중..."
    & $PythonPath -m venv "$WebBackDst\.venv"
    
    # Wheel 경로 결정 (브랜치 → 글로벌 폴백)
    $WebWheelSource = ""
    if (Test-Path "$BranchWebWheelPath\webservice-*.whl") {
        $WebWheelSource = $BranchWebWheelPath
        Write-Host "브랜치별 webservice wheel 발견: $BranchWebWheelPath"
    } elseif (Test-Path "$GlobalWheelPath\webservice\webservice-*.whl") {
        $WebWheelSource = "$GlobalWheelPath\webservice"
        Write-Host "글로벌 webservice wheel 사용: $GlobalWheelPath\webservice"
    } else {
        throw "webservice wheel 파일을 찾을 수 없습니다: $BranchWebWheelPath 또는 $GlobalWheelPath\webservice"
    }
    
    # 1. 의존성 먼저 설치 (wheelhouse에서)
    Write-Host "  - 의존성 설치 (from wheelhouse)..."
    $webPip = "$WebBackDst\.venv\Scripts\pip.exe"
    if (Test-Path "$WebSrc\pip.constraints.txt") {
        & $webPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt" -c "$WebSrc\pip.constraints.txt"
    } else {
        & $webPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt"
    }
    
    # 2. 의존성 검사 없이 .whl 패키지 설치
    Write-Host "  - webservice.whl 패키지 설치 (--no-deps)..."
    $webWheelFile = Get-ChildItem -Path "$WebWheelSource" -Filter "webservice-*.whl" | Select-Object -First 1
    & $webPip install $webWheelFile.FullName --no-deps
    Write-Host "웹서비스 설치 완료"
    
    # AutoDoc 설치
    Write-Host "AutoDoc 설치 중..."
    & $PythonPath -m venv "$AutoDst\.venv312"
    
    # AutoDoc Wheel 경로 결정
    $AutoWheelSource = ""
    if (Test-Path "$BranchAutoWheelPath\autodoc_service-*.whl") {
        $AutoWheelSource = $BranchAutoWheelPath
        Write-Host "브랜치별 autodoc_service wheel 발견: $BranchAutoWheelPath"
    } elseif (Test-Path "$GlobalWheelPath\autodoc_service\autodoc_service-*.whl") {
        $AutoWheelSource = "$GlobalWheelPath\autodoc_service"
        Write-Host "글로벌 autodoc_service wheel 사용: $GlobalWheelPath\autodoc_service"
    } else {
        throw "autodoc_service wheel 파일을 찾을 수 없습니다: $BranchAutoWheelPath 또는 $GlobalWheelPath\autodoc_service"
    }
    
    # 1. AutoDoc 의존성 먼저 설치 (wheelhouse에서)
    Write-Host "  - AutoDoc 의존성 설치 (from wheelhouse)..."
    $autoPip = "$AutoDst\.venv312\Scripts\pip.exe"
    & $autoPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt"
    
    # 2. AutoDoc wheel 설치
    & "$AutoDst\.venv312\Scripts\pip.exe" install --no-index --find-links="$AutoWheelSource" autodoc_service
    
    # AutoDoc 추가 의존성 설치
    & "$AutoDst\.venv312\Scripts\pip.exe" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt"
    Write-Host "AutoDoc 설치 완료"
    
    # 4. 프론트엔드 빌드
    Write-Host "`n단계 4: 프론트엔드 빌드 중..."
    
    Push-Location "$WebSrc\frontend"
    try {
        if (Test-Path "package.json") {
            Write-Host "npm 의존성 설치 중..."
            npm ci
            
            Write-Host "Vite 빌드 시작 (base: $UrlPrefix)"
            npm run build -- --base="$UrlPrefix"
            Write-Host "Vite 빌드 완료"
        } else {
            throw "package.json 파일을 찾을 수 없습니다"
        }
    } finally {
        Pop-Location
    }
    
    # 프론트엔드 결과 복사
    if (Test-Path "$WebSrc\frontend\dist") {
        Copy-Item -Recurse -Force "$WebSrc\frontend\dist\*" $WebFrontDst
        Write-Host "프론트엔드 빌드 결과 복사 완료"
    } else {
        throw "프론트엔드 빌드 결과가 없습니다: dist 폴더를 찾을 수 없음"
    }
    
    # 5. NSSM 서비스 등록
    Write-Host "`n단계 5: NSSM 서비스 등록 중..."
    
    # 기존 서비스 정리 (안전한 방식)
    Write-Host "기존 서비스 확인 및 정리 중..."
    
    # --- 웹서비스 정리 (수정된 로직) ---
    $webServiceName = "cm-web-$Bid"
    Write-Host "기존 웹서비스 확인 및 정리: $webServiceName"
    $webStatus = & $Nssm status $webServiceName 2>$null

    if ($webStatus) {
        Write-Host "  -> 기존 서비스 발견 (상태: $webStatus). 제거를 시도합니다..."
        try {
            & $Nssm stop $webServiceName
            Start-Sleep -Seconds 2 # 서비스가 완전히 중지될 때까지 잠시 대기
            & $Nssm remove $webServiceName confirm
            Start-Sleep -Seconds 2 # 서비스가 완전히 제거될 때까지 잠시 대기
            Write-Host "  -> 서비스 제거 명령 실행 완료."
        } catch {
            Write-Warning "  -> 서비스 중지/제거 중 오류 발생 (무시하고 계속): $($_.Exception.Message)"
        }

        # 최종 확인: 서비스가 정말로 제거되었는지 확인
        $finalStatus = & $Nssm status $webServiceName 2>$null
        if ($finalStatus) {
            throw "오류: 기존 서비스 '$webServiceName'을 제거하지 못했습니다. Jenkins 서버에서 수동으로 서비스를 제거한 후 다시 시도해주세요."
        }
        Write-Host "  -> 서비스 제거 최종 확인 완료."
    } else {
        Write-Host "  -> 기존 서비스가 없어 정리 작업을 건너뜁니다."
    }
    
    # --- AutoDoc 서비스 정리 (동일하게 수정) ---
    $autodocServiceName = "cm-autodoc-$Bid"
    Write-Host "기존 AutoDoc 서비스 확인 및 정리: $autodocServiceName"
    $autodocStatus = & $Nssm status $autodocServiceName 2>$null

    if ($autodocStatus) {
        Write-Host "  -> 기존 서비스 발견 (상태: $autodocStatus). 제거를 시도합니다..."
        try {
            & $Nssm stop $autodocServiceName
            Start-Sleep -Seconds 2
            & $Nssm remove $autodocServiceName confirm
            Start-Sleep -Seconds 2
            Write-Host "  -> 서비스 제거 명령 실행 완료."
        } catch {
            Write-Warning "  -> 서비스 중지/제거 중 오류 발생 (무시하고 계속): $($_.Exception.Message)"
        }
        
        # 최종 확인
        $finalAutodocStatus = & $Nssm status $autodocServiceName 2>$null
        if ($finalAutodocStatus) {
            throw "오류: 기존 서비스 '$autodocServiceName'을 제거하지 못했습니다. 수동으로 제거 후 다시 시도하세요."
        }
        Write-Host "  -> 서비스 제거 최종 확인 완료."
    } else {
        Write-Host "  -> 기존 서비스가 없어 정리 작업을 건너뜁니다."
    }
    
    # 웹서비스 서비스 등록
    Write-Host "웹서비스 서비스 등록 중..."
    # & $Nssm install "cm-web-$Bid" "$WebBackDst\.venv\Scripts\python.exe" "-m uvicorn webservice.app.main:app --host 0.0.0.0 --port $BackPort"
    & $Nssm install "cm-web-$Bid" "$WebBackDst\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $BackPort"
    & $Nssm set "cm-web-$Bid" AppDirectory $WebBackDst
    & $Nssm set "cm-web-$Bid" AppStdout "$TestLogsPath\web-$Bid.out.log"
    & $Nssm set "cm-web-$Bid" AppStderr "$TestLogsPath\web-$Bid.err.log"
    & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath"
    & $Nssm start "cm-web-$Bid"
    Write-Host "웹서비스 서비스 시작 완료 (Port: $BackPort)"
    
    # AutoDoc 서비스 등록
    Write-Host "AutoDoc 서비스 등록 중..."
    & $Nssm install "cm-autodoc-$Bid" "$AutoDst\.venv312\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $AutoPort"
    # & $Nssm install "cm-autodoc-$Bid" "$AutoDst\.venv312\Scripts\python.exe" "-m uvicorn autodoc_service.app.main:app --host 0.0.0.0 --port $AutoPort"
    & $Nssm set "cm-autodoc-$Bid" AppDirectory $AutoDst
    & $Nssm set "cm-autodoc-$Bid" AppStdout "$TestLogsPath\autodoc-$Bid.out.log"
    & $Nssm set "cm-autodoc-$Bid" AppStderr "$TestLogsPath\autodoc-$Bid.err.log"
    & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath"
    & $Nssm start "cm-autodoc-$Bid"
    Write-Host "AutoDoc 서비스 시작 완료 (Port: $AutoPort)"
    
    # 6. Nginx 설정
    Write-Host "`n단계 6: Nginx 설정 적용 중..."
    
    $templatePath = "$PSScriptRoot\..\infra\nginx\tests.template.conf"
    if (-not (Test-Path $templatePath)) {
        throw "Nginx 템플릿 파일을 찾을 수 없습니다: $templatePath"
    }
    
    $tpl = Get-Content -Raw $templatePath
    $conf = $tpl.Replace("{{BID}}", $Bid).Replace("{{BACK_PORT}}", "$BackPort").Replace("{{AUTO_PORT}}", "$AutoPort")
    $out = Join-Path $NginxConfDir "tests-$Bid.conf"
    
    # Nginx conf 디렉토리 생성 확인 (상위 디렉토리 포함)
    $nginxConfParent = Split-Path $NginxConfDir -Parent
    if (-not (Test-Path $nginxConfParent)) {
        New-Item -ItemType Directory -Force -Path $nginxConfParent | Out-Null
        Write-Host "Nginx 상위 디렉토리 생성: $nginxConfParent"
    }
    
    # 최종 디렉토리 존재 확인
    if (-not (Test-Path $NginxConfDir)) {
        New-Item -ItemType Directory -Force -Path $NginxConfDir | Out-Null
        Write-Host "Nginx conf.d 디렉토리 생성: $NginxConfDir"
    }
    
    $conf | Set-Content -Encoding UTF8 $out
    
    Write-Host "Nginx 설정 파일 생성 완료: $out"
    
    # Nginx 리로드
    & $Nginx -s reload
    Write-Host "Nginx 리로드 완료"
    
    # 7. 서비스 상태 확인 및 Smoke 테스트
    Write-Host "`n단계 7: 서비스 확인 및 Smoke 테스트 중..."
    Start-Sleep -Seconds 10  # wheel 기반 서비스 시작 대기시간 증가
    
    $webStatus = & $Nssm status "cm-web-$Bid"
    $autodocStatus = & $Nssm status "cm-autodoc-$Bid"
    
    Write-Host "웹서비스 상태: $webStatus"
    Write-Host "AutoDoc 상태: $autodocStatus"
    
    # 서비스 상태 검증
    if ($webStatus -ne "SERVICE_RUNNING") {
        throw "웹서비스가 정상 실행되지 않았습니다 (상태: $webStatus)"
    }
    if ($autodocStatus -ne "SERVICE_RUNNING") {
        throw "AutoDoc 서비스가 정상 실행되지 않았습니다 (상태: $autodocStatus)"
    }
    
    # HTTP Health Check
    Write-Host "HTTP Health Check 수행 중..."
    try {
        $webHealth = Invoke-RestMethod -Uri "http://localhost:$BackPort/api/health" -TimeoutSec 30
        Write-Host "웹서비스 Health Check: 정상"
    } catch {
        Write-Warning "웹서비스 Health Check 실패: $($_.Exception.Message)"
    }
    
    try {
        $autoHealth = Invoke-RestMethod -Uri "http://localhost:$AutoPort/health" -TimeoutSec 30
        Write-Host "AutoDoc Health Check: 정상"
    } catch {
        Write-Warning "AutoDoc Health Check 실패: $($_.Exception.Message)"
    }
    
    Write-Host "`n===========================================`n"
    Write-Host "테스트 인스턴스 배포 완료 (Wheel 기반)!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    Write-Host "• 웹서비스: http://localhost:$BackPort"
    Write-Host "• AutoDoc: http://localhost:$AutoPort"
    Write-Host "• 프론트엔드 URL: /tests/$Bid/"
    Write-Host "• 로그 디렉토리: $TestLogsPath"
    Write-Host "• Wheel 경로: $PackagesRoot"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "테스트 인스턴스 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리
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