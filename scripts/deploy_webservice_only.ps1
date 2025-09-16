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
    [Parameter(Mandatory=$true)][string]$PackagesRoot, # "C:\deploys\test\{BID}\packages"
    [Parameter(Mandatory=$false)][switch]$ForceUpdateDeps = $false  # 의존성 강제 업데이트
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
    
    # 1.5. 포트 유효성 검사 제거 - 아래 서비스 관리 섹션에서 기존 서비스를 정리하므로 불필요
    # Write-Host "`n단계 1.5: 포트 유효성 검사 중..."
    # Validate-DeploymentPorts는 서비스 정리 전에 실행되어 충돌을 일으키므로 제거
    
    # 2. 웹서비스 디렉토리 생성
    Write-Host "`n단계 2: 웹서비스 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $WebBackDst, $TestWebDataPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$PackagesRoot\webservice" | Out-Null
    Write-Host "디렉토리 생성 완료: $WebBackDst"
    
    # 3. Config 파일 준비
    Write-Host "`n단계 3: Config 파일 준비 중..."
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
        
        # 프로세스 완전 종료 확인 및 강제 종료
        Write-Host "  -> 프로세스 완전 종료 확인 중..."
        $maxWait = 15  # 최대 15초 대기
        $waited = 0
        do {
            Start-Sleep -Seconds 1
            $waited++
            $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
                $_.CommandLine -like "*$webServiceName*" -or 
                ($_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*$BackPort*")
            }
            if (-not $remainingProcess) { break }
            Write-Host "    프로세스 종료 대기 중... ($waited/$maxWait)"
        } while ($waited -lt $maxWait)
        
        # 강제 종료가 필요한 경우
        if ($remainingProcess) {
            Write-Warning "  -> 프로세스가 완전히 종료되지 않았습니다. 강제 종료를 시도합니다."
            $remainingProcess | ForEach-Object { 
                try {
                    Stop-Process -Id $_.Id -Force -ErrorAction Stop
                    Write-Host "    강제 종료: PID $($_.Id)"
                } catch {
                    Write-Warning "    강제 종료 실패: PID $($_.Id) - $($_.Exception.Message)"
                }
            }
            Start-Sleep -Seconds 3
        }
        
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
    
    # 스마트 가상환경 관리 (기존 환경 유지 또는 생성)
    $needsDependencies = $false
    if (-not (Test-Path "$WebBackDst\.venv")) {
        Write-Host "가상환경 생성 중..."
        & $PythonPath -m venv "$WebBackDst\.venv"
        $needsDependencies = $true
        Write-Host "새 가상환경 생성 완료"
    } else {
        Write-Host "기존 가상환경 유지 (빠른 배포)"
        if ($ForceUpdateDeps) {
            Write-Host "ForceUpdateDeps 옵션: 의존성 강제 업데이트"
            $needsDependencies = $true
        }
    }
    
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
    
    # pip 경로 설정
    $webPip = "$WebBackDst\.venv\Scripts\pip.exe"
    
    # 1. 선택적 의존성 설치 (새 환경이거나 강제 업데이트 시에만)
    if ($needsDependencies) {
        Write-Host "  - 의존성 설치 (from wheelhouse)..."
        if (Test-Path "$WebSrc\pip.constraints.txt") {
            & $webPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt" -c "$WebSrc\pip.constraints.txt"
        } else {
            & $webPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt"
        }
    } else {
        Write-Host "  - 의존성 스킵 (기존 환경 유지 - 고속 배포)"
    }
    
    # 2. Jenkins와 동일한 wheel 교체 로직 (초고속)
    $webWheelFile = Get-ChildItem -Path "$WebWheelSource" -Filter "webservice-*.whl" | Select-Object -First 1
    Write-Host "효율적인 재설치 시작: $($webWheelFile.Name)"
    
    # 기존 webservice 패키지만 언인스톨 (의존성은 유지)
    Write-Host "  - 기존 webservice 패키지 제거 중..."
    & $webPip uninstall webservice -y 2>&1 | Out-Null
    Write-Host "  - 기존 패키지 제거 완료"
    
    # 휠하우스가 있으면 오프라인 설치로 속도 최적화 (폐쇄망 호환)
    if (Test-Path "$GlobalWheelPath\wheelhouse\*.whl") {
        Write-Host "  - 휠하우스 발견 - 오프라인 빠른 설치"
        & $webPip install $webWheelFile.FullName --no-index --find-links="$GlobalWheelPath\wheelhouse" --no-deps
    } else {
        Write-Host "  - 일반 설치 모드"
        & $webPip install $webWheelFile.FullName --no-deps
    }
    Write-Host "웹서비스 설치 완료 (Jenkins 스타일 고속 배포)"
    
    # 5. 마스터 데이터 복사
    Copy-MasterData -TestWebDataPath $TestWebDataPath -TestAutoDataPath $null
    
    # 6. 웹서비스 서비스 등록 또는 재시작
    if ($isDevelop -and $webServiceExists) {
        Write-Host "웹서비스 재시작 중 (develop 브랜치)..."
        & $Nssm start "cm-web-$Bid"
        Write-Host "웹서비스 재시작 완료 (Port: $BackPort)"
    } else {
        # 락 보호된 NSSM 서비스 등록 사용
        Register-Service-WithLock -ServiceName "cm-web-$Bid" -ExecutablePath "$WebBackDst\.venv\Scripts\python.exe" -Arguments "-m uvicorn app.main:app --host 0.0.0.0 --port $BackPort" -NssmPath $Nssm

        # 추가 NSSM 설정 (webservice 루트 디렉토리로 설정)
        $WebServiceRoot = Split-Path $WebBackDst -Parent
        & $Nssm set "cm-web-$Bid" AppDirectory $WebServiceRoot
        & $Nssm set "cm-web-$Bid" AppStdout "$TestLogsPath\web-$Bid.out.log"
        & $Nssm set "cm-web-$Bid" AppStderr "$TestLogsPath\web-$Bid.err.log"
        & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath"
        Write-Host "웹서비스 서비스 등록 및 시작 완료 (Port: $BackPort)"
    }
    
    # 7. Nginx 설정 업데이트 (서비스별 분리 설정)
    Update-NginxConfig -Bid $Bid -ServiceType "web" -Port $BackPort -Nginx $Nginx
    
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
    $errorMessage = $_.Exception.Message
    $errorLine = $_.InvocationInfo.ScriptLineNumber
    
    Write-Error """
    ❌ 웹서비스 백엔드 배포 실패
    ===========================================
    에러 메시지: $errorMessage
    발생 위치: 라인 $errorLine
    BID: $Bid
    BackPort: $BackPort
    
    📋 문제 해결 가이드:
    1. Permission Denied 에러:
       - NSSM 서비스 수동 중지: nssm stop cm-web-$Bid
       - 프로세스 강제 종료: taskkill /f /im python.exe
       - 가상환경 폴더 접근 권한 확인
    
    2. 포트 관련 에러:
       - 포트 $BackPort 사용 여부 확인: netstat -ano | findstr $BackPort
       - 다른 프로세스가 포트를 사용 중인지 확인
    
    3. 서비스 등록 실패:
       - 기존 서비스 확인: sc query cm-web-$Bid
       - 서비스 수동 삭제: sc delete cm-web-$Bid
    
    4. 가상환경 문제:
       - 가상환경 재생성: rmdir /s $WebBackDst\.venv
       - Python 경로 확인: $PythonPath
    ===========================================
    """
    
    # 실패 시 정리
    Write-Host "실패 후 정리 시도 중..."
    
    try {
        $cleanupWebSvc = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
        if ($cleanupWebSvc) {
            Write-Host "  -> 서비스 중지 시도: cm-web-$Bid"
            & $Nssm stop "cm-web-$Bid" 2>$null
            Start-Sleep -Seconds 5
            
            Write-Host "  -> 서비스 제거 시도: cm-web-$Bid"
            & $Nssm remove "cm-web-$Bid" confirm 2>$null
        }
        
        # 남아있는 프로세스 강제 종료
        $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { 
            $_.CommandLine -like "*cm-web-$Bid*" -or 
            ($_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*$BackPort*")
        }
        if ($remainingProcess) {
            Write-Host "  -> 남아있는 프로세스 강제 종료"
            $remainingProcess | ForEach-Object { 
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
        
        Write-Host "정리 완료"
    } catch {
        Write-Warning "정리 중 오류 발생: $($_.Exception.Message)"
    }
    
    throw $_.Exception
}