# scripts/deploy_webservice_only.ps1
# 웹서비스 백엔드만 배포하는 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][int]$BackPort,
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$WebSrc,      # repo/webservice
    [Parameter(Mandatory=$true)][string]$WebBackDst,  # C:\deploys\test\{BID}\apps\webservice
    [Parameter(Mandatory=$true)][string]$PackagesRoot # "C:\deploys\test\{BID}\packages"
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 공통 함수 로드
. "$PSScriptRoot\deploy_common.ps1" -Bid $Bid -Nssm $Nssm -Nginx $Nginx -PackagesRoot $PackagesRoot

Write-Host "===========================================`n"
Write-Host "웹서비스 백엔드 배포 시작 (독립 배포)`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• Backend Port: $BackPort"
Write-Host "• Packages Root: $PackagesRoot"
Write-Host "===========================================`n"

try {
    # 1. 공통 초기화
    $commonDirs = Initialize-CommonDirectories -PackagesRoot $PackagesRoot -Bid $Bid
    $TestWebDataPath = "$($commonDirs.TestDataRoot)\webservice"
    $TestLogsPath = $commonDirs.TestLogsPath
    
    # 2. 웹서비스 디렉토리 생성
    Write-Host "단계 1: 웹서비스 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $WebBackDst, $TestWebDataPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$PackagesRoot\webservice" | Out-Null
    Write-Host "디렉토리 생성 완료: $WebBackDst"
    
    # 3. Config 파일 준비
    Write-Host "`n단계 2: Config 파일 준비 중..."
    if (Test-Path "$WebSrc\config.test.json") {
        Copy-Item -Force "$WebSrc\config.test.json" "$TestWebDataPath\config.json"
        Write-Host "테스트용 config 복사: $TestWebDataPath\config.json"
    } elseif (Test-Path "$WebSrc\config.json") {
        Copy-Item -Force "$WebSrc\config.json" "$TestWebDataPath\config.json"
        Write-Host "기본 config 복사: $TestWebDataPath\config.json"
    } else {
        Write-Warning "웹서비스 config 파일을 찾을 수 없습니다"
    }
    
    # 4. Wheel 설치
    Write-Host "`n단계 3: 웹서비스 Wheel 설치 중..."
    
    # Python 경로 확장
    $PythonPath = $Py
    if ($PythonPath.Contains('%LOCALAPPDATA%')) {
        $PythonPath = $PythonPath.Replace('%LOCALAPPDATA%', $env:LOCALAPPDATA)
    }
    
    # 6. 서비스 관리 (가상환경 정리 전에 먼저 수행)
    Write-Host "`n단계 4: 웹서비스 서비스 관리 중..."
    
    # develop 브랜치 여부 확인
    $isDevelop = $Bid -eq "develop"
    
    # 웹서비스 처리
    $webServiceName = "cm-web-$Bid"
    $webServiceExists = $false
    
    Write-Host "웹서비스 확인: $webServiceName"
    
    try {
        $windowsService = Get-Service -Name $webServiceName -ErrorAction Stop
        $webServiceExists = $true
        Write-Host "  -> 기존 서비스 발견 (Windows 상태: $($windowsService.Status))"
        
        Write-Host "  -> 서비스 중지 중..."
        & $Nssm stop $webServiceName
        Start-Sleep -Seconds 3  # 서비스 완전 중지 대기
        
        if (-not $isDevelop) {
            Write-Host "  -> 일반 브랜치: 서비스 제거"
            & $Nssm remove $webServiceName confirm
            Start-Sleep -Seconds 2
            $webServiceExists = $false
            
            # 최종 확인
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
    
    # 서비스 중지 후 가상환경 정리 (파일 잠금 방지)
    if (Test-Path "$WebBackDst\.venv") {
        Write-Host "기존 가상환경 정리 중..."
        Start-Sleep -Seconds 2  # 추가 대기
        Remove-Item -Recurse -Force "$WebBackDst\.venv"
        Write-Host "기존 가상환경 정리 완료"
    }
    
    # 웹서비스 가상환경 생성
    Write-Host "웹서비스 가상환경 생성 중..."
    & $PythonPath -m venv "$WebBackDst\.venv"
    
    # Wheel 경로 결정 (브랜치 → 글로벌 폴백)
    $BranchWebWheelPath = "$PackagesRoot\webservice"
    $GlobalWheelPath = "C:\deploys\packages"
    
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
    
    # 5. 마스터 데이터 복사
    Copy-MasterData -TestWebDataPath $TestWebDataPath -TestAutoDataPath $null
    
    # 6. 웹서비스 서비스 등록 또는 재시작
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
        & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath"
        & $Nssm start "cm-web-$Bid"
        Write-Host "웹서비스 서비스 시작 완료 (Port: $BackPort)"
    }
    
    # 7. Nginx 설정 업데이트 (백엔드 포트만)
    Update-NginxConfig -Bid $Bid -BackPort $BackPort -AutoPort $null -Nginx $Nginx
    
    # 8. 서비스 상태 확인
    Test-ServiceHealth -BackPort $BackPort -AutoPort $null -Bid $Bid -Nssm $Nssm
    
    Write-Host "`n===========================================`n"
    Write-Host "웹서비스 백엔드 배포 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    Write-Host "• 웹서비스: http://localhost:$BackPort"
    Write-Host "• 로그 디렉토리: $TestLogsPath"
    Write-Host "• Wheel 경로: $WebWheelSource"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "웹서비스 백엔드 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리
    Write-Host "실패 후 정리 시도 중..."
    
    $cleanupWebSvc = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
    if ($cleanupWebSvc) {
        & $Nssm stop "cm-web-$Bid" 2>$null
        & $Nssm remove "cm-web-$Bid" confirm 2>$null
    }
    
    throw $_.Exception
}