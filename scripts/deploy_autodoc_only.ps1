# scripts/deploy_autodoc_only.ps1
# AutoDoc 서비스만 배포하는 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][int]$AutoPort,
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$AutoSrc,     # repo/autodoc_service
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\test\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$true)][string]$PackagesRoot # "C:\deploys\test\{BID}\packages"
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
    
    # 2. AutoDoc 디렉토리 생성
    Write-Host "단계 1: AutoDoc 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $AutoDst, $TestAutoDataPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$PackagesRoot\autodoc_service" | Out-Null
    Write-Host "디렉토리 생성 완료: $AutoDst"
    
    # 3. Config 파일 및 템플릿 준비
    Write-Host "`n단계 2: Config 파일 및 템플릿 준비 중..."
    if (Test-Path "$AutoSrc\data\templates") {
        Copy-Item -Recurse -Force "$AutoSrc\data\templates" "$TestAutoDataPath\templates"
        Write-Host "AutoDoc 템플릿 복사 완료"
    }
    
    # 4. Wheel 설치
    Write-Host "`n단계 3: AutoDoc Wheel 설치 중..."
    
    # Python 경로 확장
    $PythonPath = $Py
    if ($PythonPath.Contains('%LOCALAPPDATA%')) {
        $PythonPath = $PythonPath.Replace('%LOCALAPPDATA%', $env:LOCALAPPDATA)
    }
    
    # 기존 가상환경 정리
    if (Test-Path "$AutoDst\.venv312") {
        Remove-Item -Recurse -Force "$AutoDst\.venv312"
        Write-Host "기존 가상환경 정리 완료"
    }
    
    # AutoDoc 가상환경 생성
    Write-Host "AutoDoc 가상환경 생성 중..."
    & $PythonPath -m venv "$AutoDst\.venv312"
    
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
    
    # 1. AutoDoc 의존성 먼저 설치 (wheelhouse에서)
    Write-Host "  - AutoDoc 의존성 설치 (from wheelhouse)..."
    $autoPip = "$AutoDst\.venv312\Scripts\pip.exe"
    & $autoPip install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt"
    
    # 2. AutoDoc wheel 설치
    Write-Host "  - autodoc_service.whl 패키지 설치..."
    & "$AutoDst\.venv312\Scripts\pip.exe" install --no-index --find-links="$AutoWheelSource" autodoc_service
    
    # AutoDoc 추가 의존성 설치 (안전성을 위해 재실행)
    & "$AutoDst\.venv312\Scripts\pip.exe" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt"
    Write-Host "AutoDoc 설치 완료"
    
    # 5. 마스터 데이터 복사
    Copy-MasterData -TestWebDataPath $null -TestAutoDataPath $TestAutoDataPath
    
    # 6. 서비스 관리
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
        
        if ($isDevelop) {
            Write-Host "  -> develop 브랜치: 서비스 재사용을 위해 중지만 수행"
            & $Nssm stop $autodocServiceName
            Start-Sleep -Seconds 2
        } else {
            Write-Host "  -> 일반 브랜치: 서비스 제거 후 재생성"
            & $Nssm stop $autodocServiceName
            Start-Sleep -Seconds 2
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
        & $Nssm set "cm-autodoc-$Bid" AppEnvironmentExtra "AUTODOC_DATA_PATH=$TestAutoDataPath"
        & $Nssm start "cm-autodoc-$Bid"
        Write-Host "AutoDoc 서비스 시작 완료 (Port: $AutoPort)"
    }
    
    # 7. Nginx 설정 업데이트 (AutoDoc 포트만)
    Update-NginxConfig -Bid $Bid -BackPort $null -AutoPort $AutoPort -Nginx $Nginx
    
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