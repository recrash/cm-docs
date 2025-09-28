# scripts/deploy_autodoc_only.ps1
# AutoDoc 서비스만 배포하는 스크립트

param(
    # === 분기용 파라미터 ===
    [Parameter(Mandatory=$false)][switch]$IsMainBranch,

    # === Main 브랜치 전용 파라미터 ===
    [Parameter(Mandatory=$false)][string]$MainDeployPath = 'C:\deploys\apps\autodoc_service',
    [Parameter(Mandatory=$false)][string]$MainDataPath = 'C:\deploys\data\autodoc_service',
    [Parameter(Mandatory=$false)][string]$MainServiceName = 'autodoc_service',
    [Parameter(Mandatory=$false)][int]$MainPort = 8001,

    # === Feature 브랜치 전용 파라미터 ===
    [Parameter(Mandatory=$false)][string]$Bid,
    [Parameter(Mandatory=$false)][int]$AutoPort,
    [Parameter(Mandatory=$false)][string]$AutoDst,     # C:\deploys\tests\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$false)][string]$PackagesRoot, # "C:\deploys\tests\{BID}\packages"
    [Parameter(Mandatory=$false)][switch]$ForceUpdateDeps = $false,  # 의존성 강제 업데이트

    # === 공통 파라미터 ===
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$AutoSrc     # repo/autodoc_service
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ==========================================
# Main/Feature 브랜치 분기 처리
# ==========================================

if ($IsMainBranch) {
    # =====================================
    # MAIN 브랜치 프로덕션 배포 로직
    # =====================================
    Write-Host "===========================================`n"
    Write-Host "MAIN 브랜치 AutoDoc 프로덕션 배포 시작`n"
    Write-Host "===========================================`n"
    Write-Host "• Deploy Path: $MainDeployPath"
    Write-Host "• Data Path: $MainDataPath"
    Write-Host "• Service Name: $MainServiceName"
    Write-Host "• Port: $MainPort"
    Write-Host "===========================================`n"

    try {
        # 1. 서비스 중지
        Write-Host "1. 서비스 중지 중..."
        & $Nssm stop $MainServiceName
        Start-Sleep -Seconds 3

        # 2. 소스 파일 복사
        Write-Host "2. 소스 파일 복사 중..."
        if (Test-Path $AutoSrc) {
            Copy-Item -Path "$AutoSrc\*" -Destination $MainDeployPath -Recurse -Force
            Write-Host "소스 파일 복사 완료"
        } else {
            throw "AutoDoc 소스 경로를 찾을 수 없습니다: $AutoSrc"
        }

        # 3. 가상환경 확인 및 의존성 업데이트 (Python 환경 격리 + 폐쇄망 호환)
        Write-Host "3. 가상환경 확인 및 의존성 업데이트 중..."

        # 글로벌 변수 정의 (wheelhouse 감지용)
        $GlobalWheelPath = "C:\deploys\packages"

        if (Test-Path "$MainDeployPath\.venv312") {
            # 기존 가상환경이 있는 경우 의존성만 업데이트
            Write-Host "기존 가상환경 발견 - 의존성 업데이트 중..."

            # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
            $env:PYTHONIOENCODING = 'utf-8'
            $env:LC_ALL = 'C.UTF-8'
            $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
            $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
            $env:PIP_NO_BUILD_ISOLATION = '1'     # 빌드 격리 비활성화로 메모리 절약
            $env:TMPDIR = "$env:TEMP\pip-tmp-autodoc-main-$([System.Guid]::NewGuid())"  # 전용 임시 디렉토리

            # 임시 디렉토리 생성
            New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null

            # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성 (의존성 설치용)
            $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc Main 의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv312\Scripts\pip.exe" %*
"@
            $pipWrapper | Out-File -FilePath "pip_autodoc_main_deps.bat" -Encoding ascii

            try {
                Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
                # 메모리 효율적인 pip 설치 (환경 격리)
                & ".\pip_autodoc_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" --no-cache-dir --disable-pip-version-check
                if ($LASTEXITCODE -ne 0) {
                    throw "AutoDoc Main 의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
                }
                Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
            } finally {
                # pip wrapper 정리
                Remove-Item "pip_autodoc_main_deps.bat" -Force -ErrorAction SilentlyContinue
                # 임시 디렉토리 정리
                if (Test-Path $env:TMPDIR) {
                    Remove-Item -Recurse -Force $env:TMPDIR -ErrorAction SilentlyContinue
                }
            }
        } else {
            # 새 가상환경 생성
            Write-Host "가상환경 생성 중..."

            # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
            $env:PYTHONIOENCODING = 'utf-8'
            $env:LC_ALL = 'C.UTF-8'
            $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
            $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
            $env:TMPDIR = "$env:TEMP\pip-tmp-autodoc-main-$([System.Guid]::NewGuid())"  # 전용 임시 디렉토리

            # 전용 임시 디렉토리 생성
            New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null

            # Python 환경 격리 래퍼 생성
            $pyWrapper = @"
@echo off
set "PYTHONHOME="
set "PYTHONPATH="
py %*
"@
            $pyWrapperPath = "py_autodoc_main_clean.bat"
            $pyWrapper | Out-File -FilePath $pyWrapperPath -Encoding ascii

            try {
                # 격리된 환경에서 가상환경 생성
                & ".\$pyWrapperPath" -3.12 -m venv "$MainDeployPath\.venv312"
                if ($LASTEXITCODE -ne 0) {
                    throw "가상환경 생성 실패 (Exit Code: $LASTEXITCODE)"
                }
                Write-Host "✅ Python 환경 격리로 가상환경 생성 성공"

                Write-Host "pip 업그레이드 중... (메모리 오류 방지 + 환경 격리)"

                # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성
                $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc Main) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv312\Scripts\python.exe" %*
"@
                $pipWrapper | Out-File -FilePath "python_autodoc_main_clean.bat" -Encoding ascii

                try {
                    Write-Host "Python 환경 격리 상태에서 pip 업그레이드 중..."
                    Write-Host "wheelhouse 경로 확인: $GlobalWheelPath\wheelhouse"

                    # wheelhouse 폴더와 pip 파일 존재 확인
                    $wheelhouse_path = "$GlobalWheelPath\wheelhouse"
                    if (Test-Path $wheelhouse_path) {
                        $pip_files = Get-ChildItem -Path $wheelhouse_path -Name "pip-*.whl" -ErrorAction SilentlyContinue
                        if ($pip_files.Count -gt 0) {
                            Write-Host "wheelhouse에서 pip 파일 발견: $($pip_files -join ', ')"
                            & ".\python_autodoc_main_clean.bat" -m pip install --no-index --find-links="$wheelhouse_path" --upgrade pip
                            if ($LASTEXITCODE -ne 0) {
                                throw "pip 오프라인 업그레이드 실패 (Exit Code: $LASTEXITCODE)"
                            }
                            Write-Host "pip 오프라인 업그레이드 완료"
                        } else {
                            Write-Host "경고: wheelhouse 폴더는 존재하지만 pip wheel 파일을 찾을 수 없음"
                            Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀"
                        }
                    } else {
                        Write-Host "경고: wheelhouse 폴더가 존재하지 않음: $wheelhouse_path"
                        Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀 (인터넷 연결 불가)"
                        Write-Host "기존 pip 버전으로 계속 진행"
                    }
                } finally {
                    Remove-Item "python_autodoc_main_clean.bat" -Force -ErrorAction SilentlyContinue
                }

                # 의존성 설치
                Write-Host "  - 의존성 설치 (from wheelhouse)..."

                # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성 (의존성 설치용)
                $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc Main 의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv312\Scripts\pip.exe" %*
"@
                $pipWrapper | Out-File -FilePath "pip_autodoc_main_deps.bat" -Encoding ascii

                try {
                    Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
                    # 메모리 효율적인 pip 설치 (환경 격리)
                    & ".\pip_autodoc_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" --no-cache-dir --disable-pip-version-check
                    if ($LASTEXITCODE -ne 0) {
                        throw "AutoDoc Main 의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
                    }
                    Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
                } finally {
                    # pip wrapper 정리
                    Remove-Item "pip_autodoc_main_deps.bat" -Force -ErrorAction SilentlyContinue
                }

                Write-Host "새 가상환경 생성 및 pip 업그레이드 완료"
            } finally {
                # 임시 래퍼 정리
                Remove-Item $pyWrapperPath -Force -ErrorAction SilentlyContinue
                # 임시 디렉토리 정리
                if (Test-Path $env:TMPDIR) {
                    Remove-Item -Recurse -Force $env:TMPDIR -ErrorAction SilentlyContinue
                }
            }
        }

        # 4. 서비스 시작
        Write-Host "4. 서비스 시작 중..."
        & $Nssm start $MainServiceName
        Start-Sleep -Seconds 5

        Write-Host "===========================================`n"
        Write-Host "MAIN 브랜치 AutoDoc 프로덕션 배포 완료`n"
        Write-Host "===========================================`n"

    } catch {
        Write-Host "MAIN 브랜치 AutoDoc 배포 실패: $($_.Exception.Message)"
        # 서비스 복구 시도
        try {
            & $Nssm start $MainServiceName
        } catch {
            Write-Host "서비스 복구 실패: $($_.Exception.Message)"
        }
        throw
    }

} else {
    # =====================================
    # FEATURE 브랜치 테스트 인스턴스 배포 로직
    # =====================================

    # 공통 함수 로드
    . "$PSScriptRoot\deploy_common.ps1" -Bid $Bid -Nssm $Nssm -Nginx $Nginx -PackagesRoot $PackagesRoot

    # 글로벌 변수 정의 (wheelhouse 감지용)
    $GlobalWheelPath = "C:\deploys\packages"

    Write-Host "===========================================`n"
    Write-Host "AutoDoc 서비스 배포 시작 (독립 배포)`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• AutoDoc Port: $AutoPort"
Write-Host "• Packages Root: $PackagesRoot"
Write-Host "• Global Wheel Path: $GlobalWheelPath"
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
        # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
        $env:PYTHONIOENCODING = 'utf-8'
        $env:LC_ALL = 'C.UTF-8'
        $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
        $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
        $env:TMPDIR = "$env:TEMP\pip-tmp-$([System.Guid]::NewGuid())"  # 전용 임시 디렉토리

        # Python 3.12 가상환경 생성 (환경 격리)
        Write-Host "Python 환경 격리로 가상환경 생성 중..."

        # 배치 래퍼 생성 (PYTHONHOME 격리)
        $wrapperContent = @"
@echo off
set "PYTHONHOME="
set "PYTHONPATH="
py %*
"@
        $wrapperPath = "py_autodoc_clean.bat"
        $wrapperContent | Out-File -FilePath $wrapperPath -Encoding ascii

        # 격리된 환경에서 가상환경 생성
        try {
            & ".\$wrapperPath" -3.12 -m venv "$AutoDst\.venv312"
            if ($LASTEXITCODE -ne 0) {
                throw "가상환경 생성 실패 (Exit Code: $LASTEXITCODE)"
            }
            Write-Host "✅ Python 환경 격리로 가상환경 생성 성공"
        } finally {
            # 임시 래퍼 정리
            Remove-Item $wrapperPath -Force -ErrorAction SilentlyContinue
        }

        # 가상환경 생성 직후 pip 업그레이드 (메모리 오류 방지, 환경 격리)
        Write-Host "pip 업그레이드 중... (메모리 오류 방지 + 환경 격리)"

        # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성
        $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$AutoDst\.venv312\Scripts\python.exe" %*
"@
        $pipWrapper | Out-File -FilePath "python_autodoc_clean.bat" -Encoding ascii

        try {
            Write-Host "Python 환경 격리 상태에서 pip 업그레이드 중..."
            Write-Host "wheelhouse 경로 확인: $GlobalWheelPath\wheelhouse"

            # wheelhouse 폴더와 pip 파일 존재 확인
            $wheelhouse_path = "$GlobalWheelPath\wheelhouse"
            if (Test-Path $wheelhouse_path) {
                $pip_files = Get-ChildItem -Path $wheelhouse_path -Name "pip-*.whl" -ErrorAction SilentlyContinue
                if ($pip_files.Count -gt 0) {
                    Write-Host "wheelhouse에서 pip 파일 발견: $($pip_files -join ', ')"
                    & ".\python_autodoc_clean.bat" -m pip install --no-index --find-links="$wheelhouse_path" --upgrade pip
                    if ($LASTEXITCODE -ne 0) {
                        throw "pip 오프라인 업그레이드 실패 (Exit Code: $LASTEXITCODE)"
                    }
                    Write-Host "pip 오프라인 업그레이드 완료"
                } else {
                    Write-Host "경고: wheelhouse 폴더는 존재하지만 pip wheel 파일을 찾을 수 없음"
                    Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀"
                }
            } else {
                Write-Host "경고: wheelhouse 폴더가 존재하지 않음: $wheelhouse_path"
                Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀 (인터넷 연결 불가)"
                Write-Host "기존 pip 버전으로 계속 진행"
            }
            Write-Host "pip 업그레이드 완료 (Python 환경 격리)"
        } finally {
            Remove-Item "python_autodoc_clean.bat" -Force -ErrorAction SilentlyContinue
        }

        $needsDependencies = $true
        Write-Host "새 가상환경 생성 및 pip 업그레이드 완료"
    } else {
        Write-Host "기존 가상환경 유지 (빠른 배포)"
        if ($ForceUpdateDeps) {
            Write-Host "ForceUpdateDeps 옵션: 의존성 강제 업데이트"
            $needsDependencies = $true
        }
    }
    
    # AutoDoc Wheel 경로 결정
    $BranchAutoWheelPath = "$PackagesRoot\autodoc_service"
    # $GlobalWheelPath는 이미 스크립트 상단에서 정의됨
    
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

        # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
        $env:PYTHONIOENCODING = 'utf-8'
        $env:LC_ALL = 'C.UTF-8'
        $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
        $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
        $env:PIP_NO_BUILD_ISOLATION = '1'     # 빌드 격리 비활성화로 메모리 절약
        $env:TMPDIR = "$env:TEMP\pip-tmp-autodoc-$([System.Guid]::NewGuid())"  # 전용 임시 디렉토리

        # 임시 디렉토리 생성
        New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null

        # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성 (의존성 설치용)
        $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc 의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$AutoDst\.venv312\Scripts\pip.exe" %*
"@
        $pipWrapper | Out-File -FilePath "pip_autodoc_deps.bat" -Encoding ascii

        try {
            Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
            # 메모리 효율적인 pip 설치 (환경 격리)
            & ".\pip_autodoc_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$AutoSrc\requirements.txt" --no-cache-dir --disable-pip-version-check
            if ($LASTEXITCODE -ne 0) {
                throw "AutoDoc 의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
            }
            Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
        } finally {
            # pip wrapper 정리
            Remove-Item "pip_autodoc_deps.bat" -Force -ErrorAction SilentlyContinue
            # 임시 디렉토리 정리
            if (Test-Path $env:TMPDIR) {
                Remove-Item -Recurse -Force $env:TMPDIR -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Host "  - 의존성 스킵 (기존 환경 유지 - 고속 배포)"
    }
    
    # 2. Jenkins와 동일한 wheel 교체 로직 (초고속)
    $autoWheelFile = Get-ChildItem -Path "$AutoWheelSource" -Filter "autodoc_service-*.whl" | Select-Object -First 1
    Write-Host "효율적인 재설치 시작: $($autoWheelFile.Name)"
    
    # Python 환경 격리를 위한 wheel 설치용 wrapper 생성
    $wheelWrapperContent = @"
@echo off
REM === Python 환경 완전 격리 (AutoDoc wheel 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$AutoDst\.venv312\Scripts\pip.exe" %*
"@
    $wheelWrapperContent | Out-File -FilePath "pip_autodoc_wheel.bat" -Encoding ascii

    try {
        # 기존 autodoc_service 패키지만 언인스톨 (의존성은 유지)
        Write-Host "  - 기존 autodoc_service 패키지 제거 중..."
        try {
            & ".\pip_autodoc_wheel.bat" uninstall autodoc_service -y 2>&1 | Out-Null
            Write-Host "  - 기존 패키지 제거 완료"
        } catch {
            Write-Host "  - 기존 패키지가 설치되지 않음 (새 설치)"
        }

        # 휠하우스가 있으면 오프라인 설치로 속도 최적화 (폐쇄망 호환)
        Write-Host "Python 환경 격리 상태에서 wheel 설치 중..."
        if (Test-Path "$GlobalWheelPath\wheelhouse\*.whl") {
            Write-Host "  - 휠하우스 발견 - 오프라인 빠른 설치"
            & ".\pip_autodoc_wheel.bat" install $autoWheelFile.FullName --no-index --find-links="$GlobalWheelPath\wheelhouse" --no-deps
        } else {
            Write-Host "  - 일반 설치 모드"
            & ".\pip_autodoc_wheel.bat" install $autoWheelFile.FullName --no-deps
        }
        if ($LASTEXITCODE -ne 0) {
            throw "AutoDoc wheel 설치 실패 (Exit Code: $LASTEXITCODE)"
        }
        Write-Host "AutoDoc 설치 완료 (Python 환경 격리)"
    } finally {
        # wheel wrapper 정리
        Remove-Item "pip_autodoc_wheel.bat" -Force -ErrorAction SilentlyContinue
    }
    
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
    $errorMessage = $_.Exception.Message
    $errorLine = $_.InvocationInfo.ScriptLineNumber

    Write-Error """
    ❌ AutoDoc 서비스 배포 실패
    ===========================================
    에러 메시지: $errorMessage
    발생 위치: 라인 $errorLine
    BID: $Bid
    AutoPort: $AutoPort

    📋 문제 해결 가이드:
    1. runpy 모듈 에러:
       - Python 환경 오염 문제: 시스템 PYTHONPATH 확인
       - 가상환경 재생성: rmdir /s $AutoDst\.venv312
       - Python 3.12 설치 확인

    2. Permission Denied 에러:
       - NSSM 서비스 수동 중지: nssm stop cm-autodoc-$Bid
       - 프로세스 강제 종료: taskkill /f /im python.exe
       - 가상환경 폴더 접근 권한 확인

    3. 포트 관련 에러:
       - 포트 $AutoPort 사용 여부 확인: netstat -ano | findstr $AutoPort
       - 다른 프로세스가 포트를 사용 중인지 확인

    4. 서비스 등록 실패:
       - 기존 서비스 확인: sc query cm-autodoc-$Bid
       - 서비스 수동 삭제: sc delete cm-autodoc-$Bid
    ===========================================
    """

    # 실패 시 정리
    Write-Host "실패 후 정리 시도 중..."

    try {
        $cleanupAutoSvc = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction SilentlyContinue
        if ($cleanupAutoSvc) {
            Write-Host "  -> 서비스 중지 시도: cm-autodoc-$Bid"
            & $Nssm stop "cm-autodoc-$Bid" 2>$null
            Start-Sleep -Seconds 5

            Write-Host "  -> 서비스 제거 시도: cm-autodoc-$Bid"
            & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
        }

        # 남아있는 프로세스 강제 종료
        $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*cm-autodoc-$Bid*" -or
            ($_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*$AutoPort*")
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

    # Jenkins에 실패 신호 전송
    Write-Host "❌ AutoDoc 서비스 배포 실패 - Jenkins에 실패 신호 전송 중..."
    exit 1
}
}