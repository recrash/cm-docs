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
    [Parameter(Mandatory=$true)][string]$WebBackDst,  # C:\deploys\tests\{BID}\apps\webservice
    [Parameter(Mandatory=$true)][string]$WebFrontDst, # C:\nginx\html\tests\{BID}
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\tests\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$true)][string]$UrlPrefix,   # "/tests/{BID}/"
    [Parameter(Mandatory=$true)][string]$PackagesRoot # "C:\deploys\tests\{BID}\packages"
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
        
        # 기존 서비스 중지 (Windows 서비스 명령어로 먼저 확인)
        try {
            $oldWebService = "cm-web-$lowerBranch"
            $oldAutoService = "cm-autodoc-$lowerBranch"
            
            # 웹서비스 정리
            $oldWebSvc = Get-Service -Name $oldWebService -ErrorAction SilentlyContinue
            if ($oldWebSvc) {
                Write-Host "기존 웹서비스 중지: $oldWebService"
                & $Nssm stop $oldWebService 2>$null
                & $Nssm remove $oldWebService confirm 2>$null
            }
            
            # AutoDoc 서비스 정리
            $oldAutoSvc = Get-Service -Name $oldAutoService -ErrorAction SilentlyContinue
            if ($oldAutoSvc) {
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
    $env:PYTHONIOENCODING='utf-8'; & $PythonPath -m venv "$WebBackDst\.venv"
    
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
    $env:PYTHONIOENCODING='utf-8'; & $PythonPath -m venv "$AutoDst\.venv312"
    
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
    
    # 4. 프론트엔드 아티팩트 배포 (작업 공간에서) - 조건부 처리
    Write-Host "`n단계 4: 프론트엔드 아티팩트 배포 중..."
    
    # 현재 작업 공간에 복사된 frontend.zip 아티팩트 경로
    $FrontendZip = "$WebSrc\frontend.zip"
    
    if (Test-Path $FrontendZip) {
        Write-Host "프론트엔드 아티팩트 발견: $FrontendZip"
        
        # frontend.zip을 임시 폴더에 압축 해제
        $TempExtractDir = "$WebFrontDst\temp_extract"
        if (Test-Path $TempExtractDir) {
            Remove-Item -Recurse -Force $TempExtractDir
        }
        New-Item -ItemType Directory -Path $TempExtractDir | Out-Null
        
        # 압축 해제 및 복사
        Expand-Archive -Path $FrontendZip -DestinationPath $TempExtractDir -Force
        Copy-Item -Recurse -Force "$TempExtractDir\*" $WebFrontDst
        
        # 임시 폴더 정리
        Remove-Item -Recurse -Force $TempExtractDir
        
        Write-Host "프론트엔드 아티팩트 배포 완료"
    } else {
        Write-Warning "프론트엔드 아티팩트를 찾을 수 없습니다: $FrontendZip"
        Write-Warning "Frontend 변경이 없거나 빌드가 실패한 경우일 수 있습니다."
        
        # 기존 프론트엔드가 있는지 확인
        if (Test-Path "$WebFrontDst\index.html") {
            Write-Host "기존 프론트엔드 파일이 존재하여 배포를 건너뜁니다."
        } else {
            # 기본 HTML 파일 생성 (최소한의 대체)
            $defaultHtml = @"
<!DOCTYPE html>
<html>
<head>
    <title>테스트 환경</title>
    <meta charset="utf-8">
</head>
<body>
    <h1>테스트 환경 - 프론트엔드 빌드 대기 중</h1>
    <p>브랜치: $Bid</p>
    <p>프론트엔드 빌드가 완료되면 자동으로 업데이트됩니다.</p>
</body>
</html>
"@
            New-Item -ItemType Directory -Force -Path $WebFrontDst | Out-Null
            Set-Content -Path "$WebFrontDst\index.html" -Value $defaultHtml -Encoding UTF8
            Write-Host "기본 HTML 파일 생성 완료 (프론트엔드 빌드 대기용)"
        }
    }
    
   # 5. NSSM 서비스 등록
    Write-Host "`n단계 5: NSSM 서비스 등록 중..."

    # develop 브랜치 여부 확인
    $isDevelop = $Bid -eq "develop"
    
    if ($isDevelop) {
        Write-Host "** develop 브랜치 감지: 서비스 재사용 모드 **"
    }

    # --- 웹서비스 처리 ---
    $webServiceName = "cm-web-$Bid"
    $webServiceExists = $false
    
    Write-Host "웹서비스 확인: $webServiceName"
    
    # Windows 기본 서비스 명령어로 먼저 확인
    try {
        $windowsService = Get-Service -Name $webServiceName -ErrorAction Stop
        $webServiceExists = $true
        Write-Host "  -> 기존 서비스 발견 (Windows 상태: $($windowsService.Status))"
        
        if ($isDevelop) {
            # develop 브랜치: 서비스 재사용 (중지만 하고 삭제하지 않음)
            Write-Host "  -> develop 브랜치: 서비스 재사용을 위해 중지만 수행"
            & $Nssm stop $webServiceName
            Start-Sleep -Seconds 2
        } else {
            # 다른 브랜치: 기존 로직 (삭제 후 재생성)
            Write-Host "  -> 일반 브랜치: 서비스 제거 후 재생성"
            & $Nssm stop $webServiceName
            Start-Sleep -Seconds 2
            & $Nssm remove $webServiceName confirm
            Start-Sleep -Seconds 2
            $webServiceExists = $false
            
            # 최종 확인 (Windows 서비스로)
            $finalService = Get-Service -Name $webServiceName -ErrorAction SilentlyContinue
            if ($finalService) {
                throw "오류: 서비스 '$webServiceName'을 제거하지 못했습니다 (상태: $($finalService.Status))."
            }
            Write-Host "  -> 서비스 제거 완료"
        }
    } catch [Microsoft.PowerShell.Commands.ServiceCommandException] {
        Write-Host "  -> 서비스가 존재하지 않음"
        $webServiceExists = $false
    }

    # --- AutoDoc 서비스 처리 ---
    $autodocServiceName = "cm-autodoc-$Bid"
    $autodocServiceExists = $false
    
    Write-Host "AutoDoc 서비스 확인: $autodocServiceName"
    
    # Windows 기본 서비스 명령어로 먼저 확인
    try {
        $windowsAutodocService = Get-Service -Name $autodocServiceName -ErrorAction Stop
        $autodocServiceExists = $true
        Write-Host "  -> 기존 서비스 발견 (Windows 상태: $($windowsAutodocService.Status))"
        
        if ($isDevelop) {
            # develop 브랜치: 서비스 재사용
            Write-Host "  -> develop 브랜치: 서비스 재사용을 위해 중지만 수행"
            & $Nssm stop $autodocServiceName
            Start-Sleep -Seconds 2
        } else {
            # 다른 브랜치: 기존 로직
            Write-Host "  -> 일반 브랜치: 서비스 제거 후 재생성"
            & $Nssm stop $autodocServiceName
            Start-Sleep -Seconds 2
            & $Nssm remove $autodocServiceName confirm
            Start-Sleep -Seconds 2
            $autodocServiceExists = $false
            
            # 최종 확인 (Windows 서비스로)
            $finalAutodocService = Get-Service -Name $autodocServiceName -ErrorAction SilentlyContinue
            if ($finalAutodocService) {
                throw "오류: 서비스 '$autodocServiceName'을 제거하지 못했습니다 (상태: $($finalAutodocService.Status))."
            }
            Write-Host "  -> 서비스 제거 완료"
        }
    } catch [Microsoft.PowerShell.Commands.ServiceCommandException] {
        Write-Host "  -> 서비스가 존재하지 않음"
        $autodocServiceExists = $false
    }


    # 마스터 데이터 복사 및 로그 정리
    Write-Host "마스터 데이터 복사 및 로그 정리"
    $MasterWebDataPath = "C:\deploys\data\webservice"
    $MasterAutoDataPath = "C:\deploys\data\autodoc_service"

    # --- Webservice 데이터 복사 ---
    if (Test-Path $MasterWebDataPath) {
        Write-Host "  -> 웹서비스 마스터 데이터 복사: $MasterWebDataPath -> $TestWebDataPath"
        Copy-Item -Path "$MasterWebDataPath\*" -Destination $TestWebDataPath -Recurse -Force
    } else {
        Write-Warning "  -> 웹서비스 마스터 데이터 폴더를 찾을 수 없습니다: $MasterWebDataPath"
    }

    # --- AutoDoc 데이터 복사 ---
    if (Test-Path $MasterAutoDataPath) {
        Write-Host "  -> AutoDoc 마스터 데이터 복사: $MasterAutoDataPath -> $TestAutoDataPath"
        Copy-Item -Path "$MasterAutoDataPath\*" -Destination $TestAutoDataPath -Recurse -Force
    } else {
        Write-Warning "  -> AutoDoc 마스터 데이터 폴더를 찾을 수 없습니다: $MasterAutoDataPath"
    }

    # --- 복사된 기존 로그 폴더 삭제 (요청사항 반영) ---
    Write-Host "  -> 복사된 기존 로그 폴더 정리..."
    $WebServiceLogPath = Join-Path $TestWebDataPath "logs"
    $AutoDocLogPath = Join-Path $TestAutoDataPath "logs"

    if (Test-Path $WebServiceLogPath) {
        Remove-Item -Path $WebServiceLogPath -Recurse -Force
        Write-Host "    - 웹서비스 로그 폴더 삭제 완료: $WebServiceLogPath"
    }

    if (Test-Path $AutoDocLogPath) {
        Remove-Item -Path $AutoDocLogPath -Recurse -Force
        Write-Host "    - AutoDoc 로그 폴더 삭제 완료: $AutoDocLogPath"
    }
    
    # 웹서비스 서비스 등록 또는 재시작
    if ($isDevelop -and $webServiceExists) {
        Write-Host "웹서비스 재시작 중 (develop 브랜치)..."
        & $Nssm start "cm-web-$Bid"
        Write-Host "웹서비스 재시작 완료 (Port: $BackPort)"
    } else {
        Write-Host "웹서비스 서비스 등록 중..."
        & $Nssm install "cm-web-$Bid" "$WebBackDst\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $BackPort"
        & $Nssm set "cm-web-$Bid" AppDirectory $WebBackDst
        & $Nssm set "cm-web-$Bid" AppStdout "$TestLogsPath\web-$Bid.out.log"
        & $Nssm set "cm-web-$Bid" AppStderr "$TestLogsPath\web-$Bid.err.log"
        & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath" "PYTHONIOENCODING=utf-8"
        & $Nssm start "cm-web-$Bid"
        Write-Host "웹서비스 서비스 시작 완료 (Port: $BackPort)"
    }
    
    # AutoDoc 서비스 등록 또는 재시작
    if ($isDevelop -and $autodocServiceExists) {
        Write-Host "AutoDoc 서비스 재시작 중 (develop 브랜치)..."
        & $Nssm start "cm-autodoc-$Bid"
        Write-Host "AutoDoc 서비스 재시작 완료 (Port: $AutoPort)"
    } else {
        Write-Host "AutoDoc 서비스 등록 중..."
        & $Nssm install "cm-autodoc-$Bid" "$AutoDst\.venv312\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $AutoPort"
        & $Nssm set "cm-autodoc-$Bid" AppDirectory $AutoDst
        & $Nssm set "cm-autodoc-$Bid" AppStdout "$TestLogsPath\autodoc-$Bid.out.log"
        & $Nssm set "cm-autodoc-$Bid" AppStderr "$TestLogsPath\autodoc-$Bid.err.log"
        & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath" "PYTHONIOENCODING=utf-8"
        & $Nssm start "cm-autodoc-$Bid"
        Write-Host "AutoDoc 서비스 시작 완료 (Port: $AutoPort)"
    }
    
    # 6. Nginx 설정 (Include 방식: Upstream + Location 분리)
    Write-Host "`n단계 6: Nginx 설정 적용 중..."
    
    # 템플릿 파일 경로
    $upstreamTemplatePath = "$PSScriptRoot\..\infra\nginx\tests.upstream.template.conf"
    $locationTemplatePath = "$PSScriptRoot\..\infra\nginx\tests.template.conf"
    
    if (-not (Test-Path $upstreamTemplatePath)) {
        throw "Upstream 템플릿 파일을 찾을 수 없습니다: $upstreamTemplatePath"
    }
    if (-not (Test-Path $locationTemplatePath)) {
        throw "Location 템플릿 파일을 찾을 수 없습니다: $locationTemplatePath"
    }
    
    # nginx include 디렉토리 생성 (표준 경로)
    $nginxRoot = Split-Path $Nginx -Parent
    $includeDir = Join-Path "$nginxRoot" "conf\include"
    if (-not (Test-Path $includeDir)) {
        New-Item -ItemType Directory -Force -Path $includeDir | Out-Null
        Write-Host "Nginx include 디렉토리 생성: $includeDir"
    }
    
    # Upstream 설정 파일 생성
    $upstreamTpl = Get-Content -Raw $upstreamTemplatePath
    $upstreamConf = $upstreamTpl.Replace("{{BID}}", $Bid).Replace("{{BACK_PORT}}", "$BackPort").Replace("{{AUTO_PORT}}", "$AutoPort")
    $upstreamOut = Join-Path $includeDir "tests-$Bid.upstream.conf"
    
    # Location 설정 파일 생성  
    $locationTpl = Get-Content -Raw $locationTemplatePath
    $locationConf = $locationTpl.Replace("{{BID}}", $Bid).Replace("{{BACK_PORT}}", "$BackPort").Replace("{{AUTO_PORT}}", "$AutoPort")
    $locationOut = Join-Path $includeDir "tests-$Bid.location.conf"
    
    # BOM 없는 UTF8 인코딩으로 파일 저장
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($upstreamOut, $upstreamConf, $utf8NoBom)
    [System.IO.File]::WriteAllText($locationOut, $locationConf, $utf8NoBom)
    
    Write-Host "Nginx 설정 파일 생성 완료:"
    Write-Host "  Upstream: $upstreamOut"
    Write-Host "  Location: $locationOut"
    
    # 기존 conf.d 방식 파일 정리 (있는 경우)
    $oldConfFile = Join-Path (Join-Path (Split-Path $Nginx -Parent) "conf\conf.d") "tests-$Bid.conf"
    if (Test-Path $oldConfFile) {
        Remove-Item $oldConfFile -Force
        Write-Host "기존 conf.d 파일 삭제: $oldConfFile"
    }
    
    # Nginx 리로드 (권한 문제 해결: NSSM 서비스 재시작)
    Write-Host "Nginx 설정 적용을 위한 서비스 재시작 중..."
    
    try {
        # PowerShell 서비스 관리 사용 (NSSM 권한 문제 해결)
        Write-Host "  PowerShell Restart-Service 사용..."
        Restart-Service -Name "nginx-frontend" -Force
        Start-Sleep -Seconds 3
        
        # Windows 기본 서비스 상태 확인
        $nginxService = Get-Service -Name "nginx-frontend"
        if ($nginxService.Status -eq "Running") {
            Write-Host "Nginx 서비스 재시작 완료 (Include 방식 설정 적용)"
        } else {
            throw "Nginx 서비스 재시작 후 상태가 비정상입니다: $($nginxService.Status)"
        }
        
    } catch {
        Write-Warning "PowerShell 서비스 재시작 실패, 직접 reload 시도: $($_.Exception.Message)"
        
        # 폴백: 직접 reload 시도 (권한 에러 무시)
        try {
            & $Nginx -p "$nginxRoot" -s reload 2>$null
            Write-Host "Nginx 직접 리로드 시도 완료 (권한 에러 무시)"
        } catch {
            Write-Warning "Nginx 리로드 완전 실패: $($_.Exception.Message)"
            Write-Host "참고: 수동으로 nginx 재시작 필요할 수 있습니다"
        }
    }
    
    # 7. 서비스 상태 확인 및 Smoke 테스트  
    Write-Host "`n단계 7: 서비스 확인 및 Smoke 테스트 중..."
    Start-Sleep -Seconds 10  # wheel 기반 서비스 시작 대기시간 증가
    
    # Windows 기본 서비스 상태 확인 (Get-Service 사용)
    try {
        $webService = Get-Service -Name "cm-web-$Bid" -ErrorAction Stop
        $autodocService = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction Stop
        
        Write-Host "웹서비스 상태: $($webService.Status)"
        Write-Host "AutoDoc 상태: $($autodocService.Status)"
        
        # 간단한 상태 검증 (PowerShell 객체의 Status 속성 직접 사용)
        if ($webService.Status -ne "Running") {
            throw "웹서비스가 정상 실행되지 않았습니다 (상태: $($webService.Status))"
        }
        if ($autodocService.Status -ne "Running") {
            throw "AutoDoc 서비스가 정상 실행되지 않았습니다 (상태: $($autodocService.Status))"
        }
        
        Write-Host "모든 서비스가 정상 실행 중입니다"
        
    } catch {
        Write-Warning "Get-Service를 사용한 상태 확인 실패, NSSM으로 폴백: $($_.Exception.Message)"
        
        # NSSM 폴백 (에러 발생 시에만)
        $webStatus = & $Nssm status "cm-web-$Bid" 2>$null
        $autodocStatus = & $Nssm status "cm-autodoc-$Bid" 2>$null
        
        Write-Host "웹서비스 상태 (NSSM): $webStatus"
        Write-Host "AutoDoc 상태 (NSSM): $autodocStatus"
        
        # NSSM 결과가 빈 값이거나 에러인 경우에만 실패로 처리
        if (-not $webStatus -or $webStatus -like "*error*") {
            throw "웹서비스 상태 확인 실패"
        }
        if (-not $autodocStatus -or $autodocStatus -like "*error*") {
            throw "AutoDoc 서비스 상태 확인 실패"
        }
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
    
    # Windows 서비스 확인 후 정리
    $cleanupWebSvc = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
    if ($cleanupWebSvc) {
        & $Nssm stop "cm-web-$Bid" 2>$null
        & $Nssm remove "cm-web-$Bid" confirm 2>$null
    }
    
    $cleanupAutoSvc = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction SilentlyContinue
    if ($cleanupAutoSvc) {
        & $Nssm stop "cm-autodoc-$Bid" 2>$null
        & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
    }
    
    $confFile = Join-Path $NginxConfDir "tests-$Bid.conf"
    Remove-Item $confFile -Force -ErrorAction SilentlyContinue
    & $Nginx -s reload 2>$null
    
    throw $_.Exception
}