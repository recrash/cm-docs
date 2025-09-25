# ========================================
# Python 환경 격리 유틸리티
# ========================================
#
# 목적: Windows 서버의 PYTHONHOME=C:\SDK 전역 설정으로 인한
#       "Could not import runpy module" 에러를 해결
#
# 원리: 배치 래퍼를 생성하여 PYTHONHOME과 PYTHONPATH를 완전히 초기화한 후
#       깨끗한 환경에서 py.exe 실행
#
# 사용법:
#   . .\scripts\python_isolation.ps1
#   New-IsolatedPythonVenv -PythonVersion "3.9" -VenvName ".venv"
#

function New-IsolatedPythonVenv {
    <#
    .SYNOPSIS
    PYTHONHOME 환경 변수 격리된 상태에서 Python 가상환경을 생성합니다.

    .DESCRIPTION
    Windows 서버의 전역 PYTHONHOME 설정(C:\SDK)으로 인한 py.exe 실행 문제를 해결하기 위해
    임시 배치 파일을 생성하여 환경 변수를 완전히 초기화한 후 가상환경을 생성합니다.

    .PARAMETER PythonVersion
    Python 버전 (예: "3.9", "3.12", "3.13")

    .PARAMETER VenvName
    가상환경 디렉토리 이름 (예: ".venv", ".venv312")

    .PARAMETER PyLauncherPath
    Python Launcher 경로 (기본값: 자동 감지)

    .EXAMPLE
    New-IsolatedPythonVenv -PythonVersion "3.9" -VenvName ".venv"

    .EXAMPLE
    New-IsolatedPythonVenv -PythonVersion "3.12" -VenvName ".venv312"
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$PythonVersion,

        [Parameter(Mandatory=$true)]
        [string]$VenvName,

        [Parameter(Mandatory=$false)]
        [string]$PyLauncherPath = ""
    )

    Write-Host "Python 환경 격리로 가상환경 생성 시작..." -ForegroundColor Green
    Write-Host "  - Python 버전: $PythonVersion" -ForegroundColor Cyan
    Write-Host "  - 가상환경 이름: $VenvName" -ForegroundColor Cyan

    # Python Launcher 경로 자동 감지
    if ([string]::IsNullOrEmpty($PyLauncherPath)) {
        $PyLauncherPath = "$env:LOCALAPPDATA\Programs\Python\Launcher\py.exe"
        if (-not (Test-Path $PyLauncherPath)) {
            # 대체 경로 시도
            $alternatePaths = @(
                "C:\Python\Python39\python.exe",
                "C:\Python\Python312\python.exe",
                "C:\Python\Python313\python.exe",
                "py.exe"  # PATH에서 찾기
            )

            foreach ($altPath in $alternatePaths) {
                try {
                    $null = Get-Command $altPath -ErrorAction Stop
                    $PyLauncherPath = $altPath
                    break
                } catch {
                    continue
                }
            }
        }
    }

    Write-Host "  - Python Launcher: $PyLauncherPath" -ForegroundColor Cyan

    # 기존 가상환경 정리 (선택사항)
    if (Test-Path $VenvName) {
        Write-Host "기존 가상환경 제거 중..." -ForegroundColor Yellow
        Remove-Item -Path $VenvName -Recurse -Force -ErrorAction SilentlyContinue
    }

    # 임시 배치 래퍼 파일명 생성 (고유성 보장)
    $wrapperName = "py_isolated_$(Get-Random).bat"

    try {
        Write-Host "배치 래퍼 생성: $wrapperName" -ForegroundColor Yellow

        # 배치 래퍼 생성 (핵심 해결책)
        @"
@echo off
set PYTHONHOME=
set PYTHONPATH=
"$PyLauncherPath" %*
"@ | Out-File -FilePath $wrapperName -Encoding ascii

        # 가상환경 생성 (격리된 환경에서)
        Write-Host "격리된 환경에서 가상환경 생성 중..." -ForegroundColor Green
        $cmd = "& .\$wrapperName -$PythonVersion -m venv $VenvName"

        # 명령 실행
        Invoke-Expression $cmd
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            # 성공 검증
            $pythonExe = Join-Path $VenvName "Scripts\python.exe"
            if (Test-Path $pythonExe) {
                Write-Host "✅ 가상환경 생성 성공!" -ForegroundColor Green
                Write-Host "  - 가상환경 경로: $(Resolve-Path $VenvName)" -ForegroundColor Cyan
                Write-Host "  - Python 실행파일: $(Resolve-Path $pythonExe)" -ForegroundColor Cyan

                # Python 버전 확인
                try {
                    $versionOutput = & $pythonExe --version 2>&1
                    Write-Host "  - Python 버전: $versionOutput" -ForegroundColor Cyan
                } catch {
                    Write-Host "  - Python 버전 확인 실패" -ForegroundColor Yellow
                }

                return $true
            } else {
                Write-Host "❌ 가상환경 생성 실패: python.exe를 찾을 수 없음" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "❌ 가상환경 생성 실패 (Exit Code: $exitCode)" -ForegroundColor Red
            return $false
        }

    } catch {
        Write-Host "❌ 오류 발생: $($_.Exception.Message)" -ForegroundColor Red
        return $false

    } finally {
        # 임시 배치 파일 정리
        if (Test-Path $wrapperName) {
            Remove-Item $wrapperName -Force -ErrorAction SilentlyContinue
            Write-Host "배치 래퍼 정리 완료" -ForegroundColor Yellow
        }
    }
}

function Test-PythonIsolation {
    <#
    .SYNOPSIS
    Python 환경 격리가 올바르게 작동하는지 테스트합니다.

    .DESCRIPTION
    PYTHONHOME이 설정된 환경에서 직접 py.exe 호출과 배치 래퍼를 통한 호출을 비교 테스트합니다.
    #>

    Write-Host "Python 환경 격리 테스트 시작..." -ForegroundColor Green

    # 현재 PYTHONHOME 확인
    $originalPythonHome = $env:PYTHONHOME
    Write-Host "현재 PYTHONHOME: '$originalPythonHome'" -ForegroundColor Cyan

    # 테스트용 임시 PYTHONHOME 설정
    $env:PYTHONHOME = "C:\SDK"
    Write-Host "테스트용 PYTHONHOME 설정: $env:PYTHONHOME" -ForegroundColor Yellow

    try {
        # 테스트 1: 직접 py.exe 실행 (실패 예상)
        Write-Host "`n[테스트 1] 직접 py.exe 실행 (실패 예상)" -ForegroundColor Yellow
        try {
            $directResult = & py -3.9 -c "print('Direct: SUCCESS')" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "예상과 다르게 성공: $directResult" -ForegroundColor Green
            } else {
                Write-Host "예상대로 실패 (PYTHONHOME 문제)" -ForegroundColor Red
            }
        } catch {
            Write-Host "예상대로 실패: $($_.Exception.Message)" -ForegroundColor Red
        }

        # 테스트 2: 배치 래퍼 실행 (성공 예상)
        Write-Host "`n[테스트 2] 배치 래퍼 실행 (성공 예상)" -ForegroundColor Yellow

        $wrapperName = "test_py_wrapper.bat"
        @"
@echo off
set PYTHONHOME=
set PYTHONPATH=
py %*
"@ | Out-File -FilePath $wrapperName -Encoding ascii

        try {
            $wrapperResult = & ".\$wrapperName" -3.9 -c "print('Wrapper: SUCCESS')" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ 래퍼 테스트 성공: $wrapperResult" -ForegroundColor Green
            } else {
                Write-Host "❌ 래퍼 테스트 실패" -ForegroundColor Red
            }
        } finally {
            Remove-Item $wrapperName -Force -ErrorAction SilentlyContinue
        }

    } finally {
        # 원본 PYTHONHOME 복원
        if ($originalPythonHome) {
            $env:PYTHONHOME = $originalPythonHome
        } else {
            Remove-Item env:PYTHONHOME -ErrorAction SilentlyContinue
        }
        Write-Host "`nPYTHONHOME 복원 완료" -ForegroundColor Cyan
    }
}

# Jenkins에서 사용할 단순한 배치 래퍼 생성 함수
function New-JenkinsPythonWrapper {
    <#
    .SYNOPSIS
    Jenkins에서 사용할 간단한 Python 격리 배치 래퍼를 생성합니다.

    .PARAMETER WrapperName
    생성할 배치 파일 이름 (기본값: "py_clean.bat")

    .EXAMPLE
    New-JenkinsPythonWrapper -WrapperName "py_isolated.bat"
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)]
        [string]$WrapperName = "py_clean.bat"
    )

    Write-Host "Jenkins용 Python 래퍼 생성: $WrapperName" -ForegroundColor Green

    @"
@echo off
set PYTHONHOME=
set PYTHONPATH=
py %*
"@ | Out-File -FilePath $WrapperName -Encoding ascii

    if (Test-Path $WrapperName) {
        Write-Host "✅ 래퍼 생성 성공: $WrapperName" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ 래퍼 생성 실패" -ForegroundColor Red
        return $false
    }
}

# 사용 예시 출력
Write-Host "Python 환경 격리 유틸리티 로드 완료" -ForegroundColor Green
Write-Host ""
Write-Host "사용 방법:" -ForegroundColor Yellow
Write-Host "  New-IsolatedPythonVenv -PythonVersion '3.9' -VenvName '.venv'" -ForegroundColor Cyan
Write-Host "  New-IsolatedPythonVenv -PythonVersion '3.12' -VenvName '.venv312'" -ForegroundColor Cyan
Write-Host "  Test-PythonIsolation" -ForegroundColor Cyan
Write-Host "  New-JenkinsPythonWrapper -WrapperName 'py_clean.bat'" -ForegroundColor Cyan