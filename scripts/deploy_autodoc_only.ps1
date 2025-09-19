# scripts/deploy_autodoc_only.ps1
# AutoDoc 서비스만 배포하는 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][int]$AutoPort,
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$AutoSrc,     # repo/autodoc_service
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\tests\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$true)][string]$PackagesRoot, # "C:\deploys\tests\{BID}\packages"
    [Parameter(Mandatory=$false)][switch]$ForceUpdateDeps = $false  # 의존성 강제 업데이트
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 공통 함수 로드
. "$PSScriptRoot\deploy_common.ps1" -Bid $Bid -Nssm $Nssm -Nginx $Nginx -PackagesRoot $PackagesRoot

Write-Host "===========================================`n"
Write-Host "AutoDoc 서비스 배포 시작 (독립 배포)`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• AutoDoc Port: $AutoPort"
Write-Host "• Packages Root: $PackagesRoot"
Write-Host "===========================================`n"

try {
    # 1. 공통 초기화
    $commonDirs = Initialize-CommonDirectories -PackagesRoot $PackagesRoot -Bid $Bid
    $TestAutoDataPath = "$($commonDirs.TestDataRoot)\autodoc_service"
    $TestLogsPath = $commonDirs.TestLogsPath
    
    # 1.5. 포트 유효성 검사 제거 - 아래 서비스 관리 섹션에서 기존 서비스를 정리하므로 불필요
    # Write-Host "`n단계 1.5: 배포 포트 유효성 검사 중..."
    # Validate-DeploymentPorts는 서비스 정리 전에 실행되어 충돌을 일으키므로 제거
    
    # 2. AutoDoc 디렉토리 생성
    Write-Host "`n단계 2: AutoDoc 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $AutoDst, $TestAutoDataPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$PackagesRoot\autodoc_service" | Out-Null
    Write-Host "디렉토리 생성 완료: $AutoDst"
    
    # 3. Config 파일 및 템플릿 준비
    Write-Host "`n단계 3: Config 파일 및 템플릿 준비 중..."
    if (Test-Path "$AutoSrc\data\templates") {
        Copy-Item -Recurse -Force "$AutoSrc\data\templates" "$TestAutoDataPath\templates"
        Write-Host "AutoDoc 템플릿 복사 완료"
    }
    
    # 4. Wheel 설치
    Write-Host "`n단계 4: AutoDoc Wheel 설치 중..."
    
    # Python 경로 확장
    $PythonPath = $Py
    if ($PythonPath.Contains('%LOCALAPPDATA%')) {
        $PythonPath = $PythonPath.Replace('%LOCALAPPDATA%', $env:LOCALAPPDATA)
    }
    
    # 6. 서비스 관리 (가상환경 정리 전에 먼저 수행)
    Write-Host "`n단계 4: AutoDoc 서비스 관리 중..."
    
    # develop 브랜치 여부 확인
    $isDevelop = $Bid -eq "develop"
    
    # AutoDoc 서비스 처리
    $autodocServiceName = "cm-autodoc-$Bid"
    $autodocServiceExists = $false
    
    Write-Host "AutoDoc 서비스 확인: $autodocServiceName"
    
    try {
        $windowsAutodocService = Get-Service -Name $autodocServiceName -ErrorAction Stop
        $autodocServiceExists = $true
        Write-Host "  -> 기존 서비스 발견 (Windows 상태: $($windowsAutodocService.Status))"
        
        Write-Host "  -> 서비스 중지 중..."
        & $Nssm stop $autodocServiceName

        # 프로세스 완전 종료 확인 및 강제 종료
        Write-Host "  -> 프로세스 완전 종료 확인 중..."
        $maxWait = 15  # 최대 15초 대기
        $waited = 0
        do {
            Start-Sleep -Seconds 1
            $waited++
            $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
                $_.CommandLine -like "*$autodocServiceName*" -or
                ($_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*$AutoPort*")
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
            & $Nssm remove $autodocServiceName confirm
            Start-Sleep -Seconds 2
            $autodocServiceExists = $false
            
            # 최종 확인
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
    
    # 스마트 가상환경 관리 (기존 환경 유지 또는 생성)
    $needsDependencies = $false
    if (-not (Test-Path "$AutoDst\.venv312")) {
        Write-Host "가상환경 생성 중..."
        $env:PYTHONIOENCODING='utf-8'; & $PythonPath -m venv "$AutoDst\.venv312"
        $needsDependencies = $true
        Write-Host "새 가상환경 생성 완료"
    } else {
        Write-Host "기존 가상환경 유지 (빠른 배포)"
        if ($ForceUpdateDeps) {
            Write-Host "ForceUpdateDeps 옵션: 의존성 강제 업데이트"
            $needsDependencies = $true
        }
    }
    
    # AutoDoc Wheel 경로 결정
    $BranchAutoWheelPath = "$PackagesRoot\autodoc_service"
    $GlobalWheelPath = "C:\deploys\packages"
    
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
    
    # pip 경로 설정
    $autoPip = "$AutoDst\.venv312\Scripts\pip.exe"
    
    # 1. 선택적 의존성 설치 (새 환경이거나 강제 업데이트 시에만)
    if ($needsDependencies) {
        Write-Host "  - 의존성 설치 (from wheelhouse)..."
        & $autoPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt"
    } else {
        Write-Host "  - 의존성 스킵 (기존 환경 유지 - 고속 배포)"
    }
    
    # 2. Jenkins와 동일한 wheel 교체 로직 (초고속)
    $autoWheelFile = Get-ChildItem -Path "$AutoWheelSource" -Filter "autodoc_service-*.whl" | Select-Object -First 1
    Write-Host "효율적인 재설치 시작: $($autoWheelFile.Name)"
    
    # 기존 autodoc_service 패키지만 언인스톨 (의존성은 유지)
    Write-Host "  - 기존 autodoc_service 패키지 제거 중..."
    & $autoPip uninstall autodoc_service -y 2>&1 | Out-Null
    Write-Host "  - 기존 패키지 제거 완료"
    
    # 휠하우스가 있으면 오프라인 설치로 속도 최적화 (폐쇄망 호환)
    if (Test-Path "$GlobalWheelPath\wheelhouse\*.whl") {
        Write-Host "  - 휠하우스 발견 - 오프라인 빠른 설치"
        & $autoPip install $autoWheelFile.FullName --no-index --find-links="$GlobalWheelPath\wheelhouse" --no-deps
    } else {
        Write-Host "  - 일반 설치 모드"
        & $autoPip install $autoWheelFile.FullName --no-deps
    }
    Write-Host "AutoDoc 설치 완료 (Jenkins 스타일 고속 배포)"
    
    # 5. 마스터 데이터 복사
    Copy-MasterData -TestWebDataPath $null -TestAutoDataPath $TestAutoDataPath
    
    # 6. AutoDoc 서비스 등록 또는 재시작
    if ($isDevelop -and $autodocServiceExists) {
        Write-Host "AutoDoc develop 브랜치 처리 중..."
        # develop 브랜치인 경우 환경변수 설정 후 재시작
        & $Nssm set "cm-autodoc-$Bid" AppDirectory $AutoDst
        & $Nssm set "cm-autodoc-$Bid" AppStdout "$TestLogsPath\autodoc-$Bid.out.log"
        & $Nssm set "cm-autodoc-$Bid" AppStderr "$TestLogsPath\autodoc-$Bid.err.log"
        & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath" "PYTHONIOENCODING=utf-8"
        
        # 환경변수 설정 후 서비스 시작
        Write-Host "환경변수 설정 완료, AutoDoc 서비스 재시작 중..."
        & $Nssm start "cm-autodoc-$Bid"
        Write-Host "AutoDoc 서비스 재시작 완료 (Port: $AutoPort)"
    } else {
        # 새 서비스 등록 - webservice 스크립트와 동일한 방식 사용
        Write-Host "AutoDoc 서비스 등록 중... (시작하지 않음)"

        # 새 서비스 설치 (시작하지 않음)
        Write-Host "  -> 서비스 설치 중..."
        & $Nssm install "cm-autodoc-$Bid" "$AutoDst\.venv312\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $AutoPort"

        # 환경변수 및 설정 먼저 적용
        Write-Host "  -> 환경변수 및 설정 적용 중..."
        & $Nssm set "cm-autodoc-$Bid" AppDirectory $AutoDst
        & $Nssm set "cm-autodoc-$Bid" AppStdout "$TestLogsPath\autodoc-$Bid.out.log"
        & $Nssm set "cm-autodoc-$Bid" AppStderr "$TestLogsPath\autodoc-$Bid.err.log"
        # 환경변수 설정
        & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath" "PYTHONIOENCODING=utf-8"

        # 모든 설정 완료 후 서비스 시작
        Write-Host "  -> 모든 설정 완료, 서비스 시작 중..."
        & $Nssm start "cm-autodoc-$Bid"
        Write-Host "AutoDoc 서비스 등록 및 시작 완료 (Port: $AutoPort)"
    }
    
    # 7. Nginx 설정 업데이트 (서비스별 분리 설정)
    Update-NginxConfig -Bid $Bid -ServiceType "autodoc" -Port $AutoPort -Nginx $Nginx
    
    # 8. 서비스 상태 확인
    Test-ServiceHealth -BackPort $null -AutoPort $AutoPort -Bid $Bid -Nssm $Nssm
    
    Write-Host "`n===========================================`n"
    Write-Host "AutoDoc 서비스 배포 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    Write-Host "• AutoDoc: http://localhost:$AutoPort"
    Write-Host "• 로그 디렉토리: $TestLogsPath"
    Write-Host "• Wheel 경로: $AutoWheelSource"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "AutoDoc 서비스 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리
    Write-Host "실패 후 정리 시도 중..."
    
    $cleanupAutoSvc = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction SilentlyContinue
    if ($cleanupAutoSvc) {
        & $Nssm stop "cm-autodoc-$Bid" 2>$null
        & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
    }
    
    throw $_.Exception
}