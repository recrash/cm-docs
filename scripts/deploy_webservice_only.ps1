# scripts/deploy_webservice_only.ps1
# 웹서비스 백엔드만 배포하는 스크립트

param(
    # === 분기용 파라미터 ===
    [Parameter(Mandatory=$false)][switch]$IsMainBranch,

    # === Main 브랜치 전용 파라미터 ===
    [Parameter(Mandatory=$false)][string]$MainDeployPath = 'C:\deploys\apps\webservice',
    [Parameter(Mandatory=$false)][string]$MainDataPath = 'C:\deploys\data\webservice',
    [Parameter(Mandatory=$false)][string]$MainServiceName = 'webservice',
    [Parameter(Mandatory=$false)][int]$MainPort = 8000,

    # === Feature 브랜치 전용 파라미터 ===
    [Parameter(Mandatory=$false)][string]$Bid,
    [Parameter(Mandatory=$false)][int]$BackPort,
    [Parameter(Mandatory=$false)][string]$WebBackDst,  # C:\deploys\tests\{BID}\apps\webservice
    [Parameter(Mandatory=$false)][string]$PackagesRoot, # "C:\deploys\tests\{BID}\packages"
    [Parameter(Mandatory=$false)][string]$AutoDocServiceUrl,  # AUTODOC_SERVICE_URL 환경변수
    [Parameter(Mandatory=$false)][string]$UrlPrefix,  # URL_PREFIX 환경변수 (테스트 브랜치용)
    [Parameter(Mandatory=$false)][switch]$ForceUpdateDeps = $false,  # 의존성 강제 업데이트

    # === 공통 파라미터 ===
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$WebSrc      # repo/webservice
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
    Write-Host "MAIN 브랜치 프로덕션 배포 시작`n"
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
        if (Test-Path $WebSrc) {
            Copy-Item -Path "$WebSrc\*" -Destination $MainDeployPath -Recurse -Force
            Write-Host "소스 파일 복사 완료"
        } else {
            throw "웹서비스 소스 경로를 찾을 수 없습니다: $WebSrc"
        }

        # 3. 가상환경 확인 및 의존성 업데이트 (Python 환경 격리 + 폐쇄망 호환)
        Write-Host "3. 가상환경 확인 및 의존성 업데이트 중..."

        # 글로벌 변수 정의 (wheelhouse 감지용)
        $GlobalWheelPath = "C:\deploys\packages"

        if (Test-Path "$MainDeployPath\.venv") {
            # 기존 가상환경이 있는 경우 의존성만 업데이트
            Write-Host "기존 가상환경 발견 - 의존성 업데이트 중..."

            # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
            $env:PYTHONIOENCODING = 'utf-8'
            $env:LC_ALL = 'C.UTF-8'
            $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
            $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
            $env:PIP_NO_BUILD_ISOLATION = '1'     # 빌드 격리 비활성화로 메모리 절약

            # Windows 경로 길이 제한 우회를 위한 짧은 임시 디렉토리 사용
            $shortGuid = [System.Guid]::NewGuid().ToString().Substring(0,8)
            $tempPipDir = "C:\tmp\pip-web-$shortGuid"
            $buildDir = "C:\tmp\build-web-$shortGuid"

            # 루트 tmp 디렉토리 생성
            New-Item -ItemType Directory -Force -Path "C:\tmp" | Out-Null
            New-Item -ItemType Directory -Force -Path $tempPipDir | Out-Null
            New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

            # 모든 임시 및 빌드 디렉토리를 짧은 경로로 설정
            $env:TMPDIR = $tempPipDir
            $env:TEMP = $tempPipDir
            $env:TMP = $tempPipDir
            $env:PIP_BUILD_DIR = $tempPipDir
            $env:BUILD_DIR = $buildDir

            # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성 (의존성 설치용)
            $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (Webservice Main 의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv\Scripts\pip.exe" %*
"@
            $pipWrapper | Out-File -FilePath "pip_webservice_main_deps.bat" -Encoding ascii

            try {
                Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
                # 메모리 효율적인 pip 설치 (환경 격리)
                if (Test-Path "$MainDeployPath\pip.constraints.txt") {
                    & ".\pip_webservice_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" -c "$MainDeployPath\pip.constraints.txt" --no-cache-dir --disable-pip-version-check
                } else {
                    & ".\pip_webservice_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" --no-cache-dir --disable-pip-version-check
                }
                if ($LASTEXITCODE -ne 0) {
                    throw "Webservice Main 의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
                }
                Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
            } finally {
                # pip wrapper 정리
                Remove-Item "pip_webservice_main_deps.bat" -Force -ErrorAction SilentlyContinue
                # 임시 디렉토리 정리
                if (Test-Path $env:TMPDIR) {
                    Remove-Item -Recurse -Force $env:TMPDIR -ErrorAction SilentlyContinue
                }
            }
        } else {
            # 새 가상환경 생성
            Write-Host "가상환경 생성 중..."

            # UTF-8 인코딩 및 메모리 최적화 환경변수 설정 (경로 단축)
            $shortGuid = ([System.Guid]::NewGuid()).ToString().Substring(0, 8)
            $env:PYTHONIOENCODING = 'utf-8'
            $env:LC_ALL = 'C.UTF-8'
            $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
            $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
            $env:TMPDIR = "C:\tmp\pip-web-$shortGuid"  # 단축된 임시 디렉토리

            # 전용 임시 디렉토리 생성
            New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null

            # Python 환경 격리 래퍼 생성
            $pyWrapper = @"
@echo off
set "PYTHONHOME="
set "PYTHONPATH="
py %*
"@
            $pyWrapperPath = "py_webservice_main_clean.bat"
            $pyWrapper | Out-File -FilePath $pyWrapperPath -Encoding ascii

            try {
                # 격리된 환경에서 가상환경 생성
                & ".\$pyWrapperPath" -3.9 -m venv "$MainDeployPath\.venv"
                if ($LASTEXITCODE -ne 0) {
                    throw "가상환경 생성 실패 (Exit Code: $LASTEXITCODE)"
                }
                Write-Host "✅ Python 환경 격리로 가상환경 생성 성공"

                Write-Host "pip 업그레이드 중... (메모리 오류 방지 + 환경 격리)"

                # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성
                $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (Webservice Main) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv\Scripts\python.exe" %*
"@
                $pipWrapper | Out-File -FilePath "python_webservice_main_clean.bat" -Encoding ascii

                try {
                    Write-Host "Python 환경 격리 상태에서 pip 업그레이드 중..."
                    Write-Host "wheelhouse 경로 확인: $GlobalWheelPath\wheelhouse"

                    # wheelhouse 폴더와 pip 파일 존재 확인
                    $wheelhouse_path = "$GlobalWheelPath\wheelhouse"
                    if (Test-Path $wheelhouse_path) {
                        $pip_files = Get-ChildItem -Path $wheelhouse_path -Name "pip-*.whl" -ErrorAction SilentlyContinue
                        if ($pip_files.Count -gt 0) {
                            Write-Host "wheelhouse에서 pip 파일 발견: $($pip_files -join ', ')"
                            & ".\python_webservice_main_clean.bat" -m pip install --no-index --find-links="$wheelhouse_path" --upgrade pip setuptools wheel
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
                    Remove-Item "python_webservice_main_clean.bat" -Force -ErrorAction SilentlyContinue
                }

                # 의존성 설치
                Write-Host "  - 의존성 설치 (from wheelhouse)..."

                # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성 (의존성 설치용)
                $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 (Webservice Main 의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$MainDeployPath\.venv\Scripts\pip.exe" %*
"@
                $pipWrapper | Out-File -FilePath "pip_webservice_main_deps.bat" -Encoding ascii

                try {
                    Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
                    # 메모리 효율적인 pip 설치 (환경 격리)
                    if (Test-Path "$MainDeployPath\pip.constraints.txt") {
                        & ".\pip_webservice_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" -c "$MainDeployPath\pip.constraints.txt" --no-cache-dir --disable-pip-version-check --prefer-binary --no-build-isolation
                    } else {
                        & ".\pip_webservice_main_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$MainDeployPath\requirements.txt" --no-cache-dir --disable-pip-version-check --prefer-binary --no-build-isolation
                    }
                    if ($LASTEXITCODE -ne 0) {
                        throw "Webservice Main 의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
                    }
                    Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
                } finally {
                    # pip wrapper 정리
                    Remove-Item "pip_webservice_main_deps.bat" -Force -ErrorAction SilentlyContinue
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
        Write-Host "MAIN 브랜치 프로덕션 배포 완료`n"
        Write-Host "===========================================`n"

    } catch {
        Write-Host "MAIN 브랜치 배포 실패: $($_.Exception.Message)"
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
    Write-Host "웹서비스 백엔드 배포 시작 (독립 배포)`n"
    Write-Host "===========================================`n"
    Write-Host "• BID: $Bid"
    Write-Host "• Backend Port: $BackPort"
    Write-Host "• Packages Root: $PackagesRoot"
    Write-Host "• Global Wheel Path: $GlobalWheelPath"
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
    
    # Python 3.9 경로 설정 (Jenkins와 동일한 방식)
    $Python39Path = "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe"
    Write-Host "Python 3.9 Launcher 경로: $Python39Path"
    
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
        Write-Host "가상환경 생성 중 (Python 3.9 + 메모리 최적화)..."

        # UTF-8 인코딩 및 메모리 최적화 환경변수 설정
        $env:PYTHONIOENCODING = 'utf-8'
        $env:LC_ALL = 'C.UTF-8'
        $env:PIP_NO_CACHE_DIR = '1'           # 캐시 비활성화로 메모리 절약
        $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'  # 버전 체크 비활성화
        $env:TMPDIR = "$env:TEMP\pip-tmp-$([System.Guid]::NewGuid())"  # 전용 임시 디렉토리

        # 전용 임시 디렉토리 생성
        New-Item -ItemType Directory -Force -Path $env:TMPDIR | Out-Null

        try {
            # Jenkins와 동일한 Python 3.9 가상환경 생성 방식 사용 (환경 격리)
            Write-Host "Python 환경 격리로 가상환경 생성 중..."

            # 배치 래퍼 생성 (PYTHONHOME 격리)
            $wrapperContent = @"
@echo off
set "PYTHONHOME="
set "PYTHONPATH="
py %*
"@
            $wrapperPath = "py_webservice_clean.bat"
            $wrapperContent | Out-File -FilePath $wrapperPath -Encoding ascii

            # 격리된 환경에서 가상환경 생성
            try {
                & ".\$wrapperPath" -3.9 -m venv "$WebBackDst\.venv"
                if ($LASTEXITCODE -ne 0) {
                    throw "가상환경 생성 실패 (Exit Code: $LASTEXITCODE)"
                }
                Write-Host "✅ Python 환경 격리로 가상환경 생성 성공"
            } finally {
                # 임시 래퍼 정리
                Remove-Item $wrapperPath -Force -ErrorAction SilentlyContinue
            }

            Write-Host "pip 자동 업그레이드 중... (메모리 에러 방지)"

            # Python 환경 완전 격리를 위한 강화된 배치 래퍼 생성
            $pipWrapper = @"
@echo off
REM === Python 환경 완전 격리 ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$WebBackDst\.venv\Scripts\python.exe" %*
"@
            $pipWrapper | Out-File -FilePath "python_web_clean.bat" -Encoding ascii

            # pip 업그레이드 (wheelhouse에서 오프라인)
            Write-Host "Python 환경 격리 상태에서 pip 업그레이드 중..."
            Write-Host "wheelhouse 경로 확인: $GlobalWheelPath\wheelhouse"

            # wheelhouse 폴더와 pip 파일 존재 확인
            $wheelhouse_path = "$GlobalWheelPath\wheelhouse"
            if (Test-Path $wheelhouse_path) {
                $pip_files = Get-ChildItem -Path $wheelhouse_path -Name "pip-*.whl" -ErrorAction SilentlyContinue
                if ($pip_files.Count -gt 0) {
                    Write-Host "wheelhouse에서 pip 파일 발견: $($pip_files -join ', ')"
                    & ".\python_web_clean.bat" -m pip install --no-index --find-links="$wheelhouse_path" --upgrade pip setuptools wheel
                    if ($LASTEXITCODE -ne 0) {
                        throw "pip 오프라인 업그레이드 실패 (Exit Code: $LASTEXITCODE)"
                    }
                    Write-Host "pip 오프라인 업그레이드 완료"
                } else {
                    Write-Host "경고: wheelhouse 폴더는 존재하지만 pip wheel 파일을 찾을 수 없음"
                    # 폐쇄망 환경에서는 온라인 업그레이드 시도하지 않음
                    Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀"
                }
            } else {
                Write-Host "경고: wheelhouse 폴더가 존재하지 않음: $wheelhouse_path"
                Write-Host "폐쇄망 환경: pip 온라인 업그레이드 건너뜀 (인터넷 연결 불가)"
                Write-Host "기존 pip 버전으로 계속 진행"
            }

            # 임시 래퍼 정리
            Remove-Item "python_web_clean.bat" -Force -ErrorAction SilentlyContinue

            $needsDependencies = $true
            Write-Host "새 가상환경 생성 완료 (Python 3.9 + pip 최적화)"

        } finally {
            # 임시 디렉토리 정리
            if (Test-Path $env:TMPDIR) {
                Remove-Item -Recurse -Force $env:TMPDIR -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Host "기존 가상환경 유지 (빠른 배포)"
        if ($ForceUpdateDeps) {
            Write-Host "ForceUpdateDeps 옵션: 의존성 강제 업데이트"
            $needsDependencies = $true
        }
    }
    
    # Wheel 경로 결정 (브랜치 → 글로벌 폴백)
    $BranchWebWheelPath = "$PackagesRoot\webservice"
    # $GlobalWheelPath는 이미 스크립트 상단에서 정의됨
    
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
        Write-Host "  - 의존성 설치 (메모리 최적화 모드)..."

        # 메모리 최적화 환경변수 설정
        $env:PYTHONIOENCODING = 'utf-8'
        $env:LC_ALL = 'C.UTF-8'
        $env:PIP_NO_CACHE_DIR = '1'
        $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
        $env:PIP_NO_BUILD_ISOLATION = '1'

        # 전용 임시 디렉토리 사용
        # Windows 경로 길이 제한 우회를 위한 짧은 임시 디렉토리 사용
        $shortGuid = [System.Guid]::NewGuid().ToString().Substring(0,8)
        $tempPipDir = "C:\tmp\pip-$shortGuid"
        $buildDir = "C:\tmp\build-$shortGuid"
        
        # 루트 tmp 디렉토리 생성
        New-Item -ItemType Directory -Force -Path "C:\tmp" | Out-Null
        New-Item -ItemType Directory -Force -Path $tempPipDir | Out-Null
        New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
        
        # 모든 임시 및 빌드 디렉토리를 짧은 경로로 설정
        $env:TMPDIR = $tempPipDir
        $env:TEMP = $tempPipDir
        $env:TMP = $tempPipDir
        $env:PIP_BUILD_DIR = $tempPipDir
        $env:BUILD_DIR = $buildDir

        # Python 환경 완전 격리를 위한 강화된 pip wrapper 생성
        $pipWrapperDeps = @"
@echo off
REM === Python 환경 완전 격리 (의존성 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$WebBackDst\.venv\Scripts\pip.exe" %*
"@
        $pipWrapperDeps | Out-File -FilePath "pip_web_deps.bat" -Encoding ascii

        try {
            Write-Host "Python 환경 격리 상태에서 의존성 설치 중..."
            if (Test-Path "$WebSrc\pip.constraints.txt") {
                & ".\pip_web_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt" -c "$WebSrc\pip.constraints.txt" --no-cache-dir --disable-pip-version-check --prefer-binary --no-build-isolation
            } else {
                & ".\pip_web_deps.bat" install --no-index --find-links="$GlobalWheelPath\wheelhouse" -r "$WebSrc\requirements.txt" --no-cache-dir --disable-pip-version-check --prefer-binary --no-build-isolation
            }
            if ($LASTEXITCODE -ne 0) {
                throw "의존성 설치 실패 (Exit Code: $LASTEXITCODE)"
            }
            Write-Host "  - 의존성 설치 완료 (Python 환경 격리)"
        } finally {
            # pip wrapper 정리
            Remove-Item "pip_web_deps.bat" -Force -ErrorAction SilentlyContinue
            # 임시 디렉토리 정리 (짧은 경로 포함)
            if (Test-Path $tempPipDir) {
                Remove-Item -Recurse -Force $tempPipDir -ErrorAction SilentlyContinue
            }
            if (Test-Path $buildDir) {
                Remove-Item -Recurse -Force $buildDir -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Host "  - 의존성 스킵 (기존 환경 유지 - 고속 배포)"
    }
    
    # 2. Jenkins와 동일한 wheel 교체 로직 (초고속)
    $webWheelFile = Get-ChildItem -Path "$WebWheelSource" -Filter "webservice-*.whl" | Select-Object -First 1
    Write-Host "효율적인 재설치 시작: $($webWheelFile.Name)"
    
    # Python 환경 격리를 위한 wheel 설치용 wrapper 생성
    $wheelWrapperContent = @"
@echo off
REM === Python 환경 완전 격리 (wheel 설치용) ===
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONUSERBASE="
set "PYTHON_EGG_CACHE="
set "PYTHONDONTWRITEBYTECODE=1"
REM 시스템 Python 경로 완전 차단
set "PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem"
"$WebBackDst\.venv\Scripts\pip.exe" %*
"@
    $wheelWrapperContent | Out-File -FilePath "pip_web_wheel.bat" -Encoding ascii

    try {
        # 기존 webservice 패키지만 언인스톨 (의존성은 유지)
        Write-Host "  - 기존 webservice 패키지 제거 중..."
        try {
            & ".\pip_web_wheel.bat" uninstall webservice -y 2>&1 | Out-Null
            Write-Host "  - 기존 패키지 제거 완료"
        } catch {
            Write-Host "  - 기존 패키지가 설치되지 않음 (새 설치)"
        }

        # 휠하우스가 있으면 오프라인 설치로 속도 최적화 (폐쇄망 호환)
        Write-Host "Python 환경 격리 상태에서 wheel 설치 중..."
        if (Test-Path "$GlobalWheelPath\wheelhouse\*.whl") {
            Write-Host "  - 휠하우스 발견 - 오프라인 빠른 설치"
            & ".\pip_web_wheel.bat" install $webWheelFile.FullName --no-index --find-links="$GlobalWheelPath\wheelhouse" --no-deps
        } else {
            Write-Host "  - 일반 설치 모드 (오프라인 강제)"
            & ".\pip_web_wheel.bat" install $webWheelFile.FullName --no-index --no-deps
        }
        if ($LASTEXITCODE -ne 0) {
            throw "웹서비스 wheel 설치 실패 (Exit Code: $LASTEXITCODE)"
        }
        Write-Host "웹서비스 설치 완료 (Python 환경 격리)"
    } finally {
        # wheel wrapper 정리
        Remove-Item "pip_web_wheel.bat" -Force -ErrorAction SilentlyContinue
    }
    
    # 5. 마스터 데이터 복사
    Copy-MasterData -TestWebDataPath $TestWebDataPath -TestAutoDataPath $null
    
    # 6. 웹서비스 서비스 등록 (서비스 설정 먼저, 시작은 나중에)
    if ($isDevelop -and $webServiceExists) {
        Write-Host "웹서비스 develop 브랜치 처리 중..."
        # develop 브랜치인 경우 환경변수 설정 후 재시작
        & $Nssm set "cm-web-$Bid" AppDirectory $WebBackDst
        & $Nssm set "cm-web-$Bid" AppStdout "$TestLogsPath\web-$Bid.out.log"
        & $Nssm set "cm-web-$Bid" AppStderr "$TestLogsPath\web-$Bid.err.log"
        # 환경변수 설정
        & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath" "PYTHONIOENCODING=utf-8" "AUTODOC_SERVICE_URL=$AutoDocServiceUrl" "URL_PREFIX=$UrlPrefix"
            
        Write-Host "환경변수 설정 완료, 웹서비스 재시작 중..."
        & $Nssm start "cm-web-$Bid"
        Write-Host "웹서비스 재시작 완료 (Port: $BackPort)"
    } else {
        # 새 서비스 등록 - 서비스만 등록하고 시작하지 않음
        Write-Host "웹서비스 서비스 등록 중... (시작하지 않음)"

        # 새 서비스 설치 (시작하지 않음)
        Write-Host "  -> 서비스 설치 중..."
        & $Nssm install "cm-web-$Bid" "$WebBackDst\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port $BackPort"

        # 환경변수 및 설정 먼저 적용
        Write-Host "  -> 환경변수 및 설정 적용 중..."
        & $Nssm set "cm-web-$Bid" AppDirectory $WebBackDst
        & $Nssm set "cm-web-$Bid" AppStdout "$TestLogsPath\web-$Bid.out.log"
        & $Nssm set "cm-web-$Bid" AppStderr "$TestLogsPath\web-$Bid.err.log"
        # 환경변수 설정
        & $Nssm set "cm-web-$Bid" AppEnvironmentExtra "WEBSERVICE_DATA_PATH=$TestWebDataPath" "PYTHONIOENCODING=utf-8" "AUTODOC_SERVICE_URL=$AutoDocServiceUrl" "URL_PREFIX=$UrlPrefix"

        # 모든 설정 완료 후 서비스 시작
        Write-Host "  -> 모든 설정 완료, 서비스 시작 중..."
        & $Nssm start "cm-web-$Bid"

        # 서비스 상태 확인
        Start-Sleep -Seconds 3
        $service = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
        if ($service -and $service.Status -eq "Running") {
            Write-Host "✓ 웹서비스 서비스 등록 및 시작 완료 (Port: $BackPort)"
        } else {
            Write-Warning "웹서비스 시작 상태 확인 필요: $(if ($service) { $service.Status } else { 'N/A' })"
        }
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
    1. runpy 모듈 에러:
       - Python 환경 오염 문제: 시스템 PYTHONPATH 확인
       - 가상환경 재생성: rmdir /s $WebBackDst\.venv
       - Python 3.9 Launcher 확인: $Python39Path

    2. Permission Denied 에러:
       - NSSM 서비스 수동 중지: nssm stop cm-web-$Bid
       - 프로세스 강제 종료: taskkill /f /im python.exe
       - 가상환경 폴더 접근 권한 확인

    3. 포트 관련 에러:
       - 포트 $BackPort 사용 여부 확인: netstat -ano | findstr $BackPort
       - 다른 프로세스가 포트를 사용 중인지 확인

    4. 서비스 등록 실패:
       - 기존 서비스 확인: sc query cm-web-$Bid
       - 서비스 수동 삭제: sc delete cm-web-$Bid
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

    # Jenkins에 실패 신호 전송
    Write-Host "❌ 웹서비스 배포 실패 - Jenkins에 실패 신호 전송 중..."
    exit 1
}

} # else (feature 브랜치) 블록 닫기