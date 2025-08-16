# AutoDoc Service 실행 스크립트 (Windows PowerShell)

param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

# 에러 시 중단
$ErrorActionPreference = "Stop"

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "🏗️  AutoDoc Service 시작 (PowerShell)" -ForegroundColor Cyan  
Write-Host "===============================================" -ForegroundColor Cyan

# 현재 디렉터리를 스크립트 위치로 설정
Set-Location $PSScriptRoot

# Python 명령어 찾기
function Find-PythonCommand {
    $pythonCommands = @("python", "python3", "py")
    
    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd --version 2>$null
            if ($LASTEXITCODE -eq 0) {
                # 버전 확인
                $versionOutput = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $majorMinor = [version]$versionOutput
                    if ($majorMinor -ge [version]"3.8") {
                        Write-Host "🐍 Python 버전: $versionOutput ($cmd)" -ForegroundColor Green
                        return $cmd
                    }
                }
            }
        }
        catch {
            continue
        }
    }
    
    Write-Host "❌ Python 3.8 이상을 찾을 수 없습니다." -ForegroundColor Red
    exit 1
}

# 의존성 설치
function Install-Dependencies {
    param($PythonCmd)
    
    Write-Host "📦 의존성 설치 중..." -ForegroundColor Yellow
    
    if (Test-Path "wheels") {
        Write-Host "🔧 오프라인 모드: wheels 디렉터리에서 설치" -ForegroundColor Blue
        & $PythonCmd -m pip install --no-index --find-links ./wheels -r requirements.txt
    }
    else {
        Write-Host "🌐 온라인 모드: PyPI에서 설치" -ForegroundColor Blue
        & $PythonCmd -m pip install -r requirements.txt
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 의존성 설치 실패" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ 의존성 설치 완료" -ForegroundColor Green
}

# 템플릿 파일 확인
function Test-Templates {
    Write-Host "🔍 템플릿 파일 확인 중..." -ForegroundColor Yellow
    
    $templatesDir = "templates"
    $requiredTemplates = @("template.docx", "template.xlsx", "template_list.xlsx")
    $missingTemplates = @()
    
    foreach ($template in $requiredTemplates) {
        $templatePath = Join-Path $templatesDir $template
        if (Test-Path $templatePath) {
            Write-Host "✅ $template 발견" -ForegroundColor Green
        }
        else {
            $missingTemplates += $template
        }
    }
    
    if ($missingTemplates.Count -gt 0) {
        Write-Host "❌ 누락된 템플릿 파일: $($missingTemplates -join ', ')" -ForegroundColor Red
        Write-Host "템플릿 디렉터리: $(Get-Location)\$templatesDir" -ForegroundColor Red
        return $false
    }
    
    Write-Host "✅ 모든 템플릿 파일 확인됨" -ForegroundColor Green
    return $true
}

# 문서 디렉터리 생성
function New-DocumentsDirectory {
    if (-not (Test-Path "documents")) {
        New-Item -ItemType Directory -Path "documents" -Force | Out-Null
    }
    Write-Host "📁 문서 디렉터리 준비: $(Get-Location)\documents" -ForegroundColor Blue
}

# 메인 실행 함수
function Main {
    try {
        # Python 확인
        $pythonCmd = Find-PythonCommand
        
        # 의존성 확인 및 설치
        try {
            & $pythonCmd -c "import fastapi, uvicorn" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ 주요 의존성이 이미 설치되어 있습니다." -ForegroundColor Green
            }
            else {
                Install-Dependencies $pythonCmd
            }
        }
        catch {
            Install-Dependencies $pythonCmd
        }
        
        # 템플릿 확인
        if (-not (Test-Templates)) {
            Write-Host ""
            Write-Host "⚠️  템플릿 파일이 없어도 서버는 시작할 수 있습니다." -ForegroundColor Yellow
            Write-Host "   API 호출 시 404 오류가 발생할 수 있습니다." -ForegroundColor Yellow
            Write-Host ""
            
            $response = Read-Host "계속 진행하시겠습니까? (y/N)"
            if ($response -notmatch "^[Yy]") {
                Write-Host "❌ 실행이 취소되었습니다." -ForegroundColor Red
                exit 1
            }
        }
        
        # 문서 디렉터리 생성
        New-DocumentsDirectory
        
        # 서버 실행
        Write-Host ""
        Write-Host "🚀 AutoDoc Service 시작 중..." -ForegroundColor Green
        Write-Host "   주소: http://$Host`:$Port" -ForegroundColor Blue
        Write-Host "   API 문서: http://$Host`:$Port/docs" -ForegroundColor Blue
        Write-Host "   종료하려면 Ctrl+C를 누르세요" -ForegroundColor Yellow
        Write-Host ""
        
        & $pythonCmd -m uvicorn app.main:app --host $Host --port $Port --reload
        
    }
    catch {
        Write-Host "❌ 실행 중 오류 발생: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    finally {
        Write-Host ""
        Write-Host "👋 AutoDoc Service가 종료되었습니다." -ForegroundColor Cyan
    }
}

# 메인 실행
Main