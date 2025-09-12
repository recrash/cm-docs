# scripts/deploy_common.ps1
# 공통 배포 기능 모듈

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$PackagesRoot
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 공통 함수 정의
function Initialize-CommonDirectories {
    param($PackagesRoot, $Bid)
    
    Write-Host "공통 디렉토리 구조 생성 중..."
    
    # 테스트 브랜치별 데이터 경로
    $TestDataRoot = "$PackagesRoot\..\data"
    $TestLogsPath = "$PackagesRoot\..\logs"
    
    New-Item -ItemType Directory -Force -Path $TestDataRoot, $TestLogsPath | Out-Null
    
    Write-Host "공통 디렉토리 생성 완료"
    Write-Host "  Data Root: $TestDataRoot"
    Write-Host "  Logs: $TestLogsPath"
    
    return @{
        TestDataRoot = $TestDataRoot
        TestLogsPath = $TestLogsPath
    }
}

function Cleanup-OldBranchFolders {
    param($Bid, $Nssm)
    
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
}

function Copy-MasterData {
    param($TestWebDataPath, $TestAutoDataPath)
    
    Write-Host "마스터 데이터 복사 및 로그 정리"
    $MasterWebDataPath = "C:\deploys\data\webservice"
    $MasterAutoDataPath = "C:\deploys\data\autodoc_service"

    # --- Webservice 데이터 복사 ---
    if ($TestWebDataPath -and (Test-Path $MasterWebDataPath)) {
        Write-Host "  -> 웹서비스 마스터 데이터 복사: $MasterWebDataPath -> $TestWebDataPath"
        Copy-Item -Path "$MasterWebDataPath\*" -Destination $TestWebDataPath -Recurse -Force
    }

    # --- AutoDoc 데이터 복사 ---
    if ($TestAutoDataPath -and (Test-Path $MasterAutoDataPath)) {
        Write-Host "  -> AutoDoc 마스터 데이터 복사: $MasterAutoDataPath -> $TestAutoDataPath"
        Copy-Item -Path "$MasterAutoDataPath\*" -Destination $TestAutoDataPath -Recurse -Force
    }

    # --- 복사된 기존 로그 폴더 삭제 ---
    Write-Host "  -> 복사된 기존 로그 폴더 정리..."
    if ($TestWebDataPath) {
        $WebServiceLogPath = Join-Path $TestWebDataPath "logs"
        if (Test-Path $WebServiceLogPath) {
            Remove-Item -Path $WebServiceLogPath -Recurse -Force
            Write-Host "    - 웹서비스 로그 폴더 삭제 완료: $WebServiceLogPath"
        }
    }

    if ($TestAutoDataPath) {
        $AutoDocLogPath = Join-Path $TestAutoDataPath "logs"
        if (Test-Path $AutoDocLogPath) {
            Remove-Item -Path $AutoDocLogPath -Recurse -Force
            Write-Host "    - AutoDoc 로그 폴더 삭제 완료: $AutoDocLogPath"
        }
    }
}

function Update-NginxConfig {
    param($Bid, $BackPort, $AutoPort, $Nginx)
    
    Write-Host "Nginx 설정 적용 중..."
    
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
    
    # Nginx 리로드
    try {
        Write-Host "  PowerShell Restart-Service 사용..."
        Restart-Service -Name "nginx-frontend" -Force
        Start-Sleep -Seconds 3
        
        # Windows 기본 서비스 상태 확인
        $nginxService = Get-Service -Name "nginx-frontend"
        if ($nginxService.Status -eq "Running") {
            Write-Host "Nginx 서비스 재시작 완료"
        } else {
            throw "Nginx 서비스 재시작 후 상태가 비정상입니다: $($nginxService.Status)"
        }
        
    } catch {
        Write-Warning "PowerShell 서비스 재시작 실패, 직접 reload 시도: $($_.Exception.Message)"
        
        # 폴백: 직접 reload 시도
        try {
            & $Nginx -p "$nginxRoot" -s reload 2>$null
            Write-Host "Nginx 직접 리로드 시도 완료"
        } catch {
            Write-Warning "Nginx 리로드 완전 실패: $($_.Exception.Message)"
            Write-Host "참고: 수동으로 nginx 재시작 필요할 수 있습니다"
        }
    }
}

function Test-ServiceHealth {
    param($BackPort, $AutoPort, $Bid, $Nssm)
    
    Write-Host "서비스 확인 및 Smoke 테스트 중..."
    Start-Sleep -Seconds 10
    
    # Windows 기본 서비스 상태 확인
    try {
        $webService = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
        $autodocService = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction SilentlyContinue
        
        if ($webService) {
            Write-Host "웹서비스 상태: $($webService.Status)"
            if ($webService.Status -ne "Running") {
                Write-Warning "웹서비스가 정상 실행되지 않았습니다 (상태: $($webService.Status))"
            }
        }
        
        if ($autodocService) {
            Write-Host "AutoDoc 상태: $($autodocService.Status)"
            if ($autodocService.Status -ne "Running") {
                Write-Warning "AutoDoc 서비스가 정상 실행되지 않았습니다 (상태: $($autodocService.Status))"
            }
        }
        
    } catch {
        Write-Warning "서비스 상태 확인 중 오류: $($_.Exception.Message)"
    }
    
    # HTTP Health Check
    if ($BackPort) {
        Write-Host "웹서비스 HTTP Health Check 수행 중..."
        try {
            $webHealth = Invoke-RestMethod -Uri "http://localhost:$BackPort/api/health" -TimeoutSec 30
            Write-Host "웹서비스 Health Check: 정상"
        } catch {
            Write-Warning "웹서비스 Health Check 실패: $($_.Exception.Message)"
        }
    }
    
    if ($AutoPort) {
        try {
            $autoHealth = Invoke-RestMethod -Uri "http://localhost:$AutoPort/health" -TimeoutSec 30
            Write-Host "AutoDoc Health Check: 정상"
        } catch {
            Write-Warning "AutoDoc Health Check 실패: $($_.Exception.Message)"
        }
    }
}

# 함수들을 외부에서 사용할 수 있도록 내보내기
Export-ModuleMember -Function Initialize-CommonDirectories, Cleanup-OldBranchFolders, Copy-MasterData, Update-NginxConfig, Test-ServiceHealth