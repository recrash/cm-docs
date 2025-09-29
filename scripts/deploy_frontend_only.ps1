# scripts/deploy_frontend_only.ps1
# 프론트엔드만 배포하는 스크립트

param(
    # Main/Feature 브랜치 구분
    [switch]$IsMainBranch,

    # Main 브랜치용 파라미터
    [string]$MainNginxRoot = 'C:\nginx\html',

    # Feature 브랜치용 파라미터 (기존 로직 보존)
    [string]$Bid,
    [string]$WebSrc,      # repo/webservice
    [string]$WebFrontDst, # C:\nginx\html\tests\{BID}
    [string]$UrlPrefix,   # "/tests/{BID}/"
    [string]$PackagesRoot # "C:\deploys\tests\{BID}\packages"
)

$ErrorActionPreference = "Stop"

# UTF-8 인코딩 설정 (폐쇄망 환경 Windows 호환성)
chcp 65001 >$null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

if ($IsMainBranch) {
    Write-Host "===========================================`n"
    Write-Host "MAIN 브랜치 프론트엔드 배포 시작`n"
    Write-Host "===========================================`n"
    Write-Host "• 배포 대상: 프로덕션 (nginx 루트)"
    Write-Host "• Nginx Root: $MainNginxRoot"
    Write-Host "===========================================`n"

    try {
        # Main 브랜치 프로덕션 배포 로직
        Write-Host "Jenkins Workspace에서 빌드된 프론트엔드 아티팩트를 nginx 루트로 배포 중..."

        # 백업 생성
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupPath = "C:\deploys\backup\apps\webservice\frontend\backup_$timestamp"
        if (Test-Path $MainNginxRoot) {
            Write-Host "기존 파일 백업 중: $backupPath"
            if (-not (Test-Path "C:\deploys\backup\apps\webservice\frontend")) {
                New-Item -ItemType Directory -Path "C:\deploys\backup\apps\webservice\frontend" -Force | Out-Null
            }
            Copy-Item -Path "$MainNginxRoot\*" -Destination $backupPath -Recurse -Force -ErrorAction SilentlyContinue
        }

        # 기존 파일 제거 (백업 제외)
        if (Test-Path $MainNginxRoot) {
            Get-ChildItem -Path $MainNginxRoot -Exclude 'backup' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }

        # Jenkins Workspace에서 빌드된 frontend.zip 배포
        $frontendZip = Join-Path $env:WORKSPACE "webservice\frontend.zip"
        if (Test-Path $frontendZip) {
            Write-Host "빌드된 아티팩트 배포: $frontendZip → $MainNginxRoot"
            Expand-Archive -Path $frontendZip -DestinationPath $MainNginxRoot -Force
        } else {
            throw "빌드된 프론트엔드 아티팩트를 찾을 수 없습니다: $frontendZip"
        }

        # 배포 검증
        Write-Host "배포 검증 중..."
        
        # index.html 존재 확인
        $indexFile = "$MainNginxRoot\index.html"
        if (Test-Path $indexFile) {
            Write-Host "index.html 확인: 정상"
        } else {
            throw "index.html을 찾을 수 없습니다: $indexFile"
        }
        
        # 정적 파일들 확인
        $staticFiles = Get-ChildItem -Path $MainNginxRoot -Recurse | Measure-Object
        Write-Host "배포된 파일 수: $($staticFiles.Count)개"

        Write-Host "✅ Main 브랜치 프론트엔드 배포 완료"

    } catch {
        Write-Error "❌ Main 브랜치 프론트엔드 배포 실패: $($_.Exception.Message)"

        # 롤백 시도
        if (Test-Path $backupPath) {
            Write-Host "백업에서 롤백 시도 중..."
            Remove-Item -Path "$MainNginxRoot\*" -Recurse -Force -ErrorAction SilentlyContinue
            Copy-Item -Path "$backupPath\*" -Destination $MainNginxRoot -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "롤백 완료"
        }

        exit 1
    }

} else {
    # 기존 Feature 브랜치 배포 로직 보존
    Write-Host "===========================================`n"
    Write-Host "프론트엔드 배포 시작 (독립 배포)`n"
    Write-Host "===========================================`n"
    Write-Host "• BID: $Bid"
    Write-Host "• URL Prefix: $UrlPrefix"
    Write-Host "• Frontend Destination: $WebFrontDst"
    Write-Host "===========================================`n"

    try {
        # 경로 정규화 (백슬래시 일관성 처리)
        $WebFrontDst = $WebFrontDst -replace '/', '\'
        $WebSrc = $WebSrc -replace '/', '\'

    # 1. 디렉토리 구조 생성
    Write-Host "단계 1: 프론트엔드 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $WebFrontDst | Out-Null
    Write-Host "프론트엔드 디렉토리 생성 완료: $WebFrontDst"
    
    # 2. 프론트엔드 아티팩트 배포
    Write-Host "`n단계 2: 프론트엔드 아티팩트 배포 중..."
    
    # 현재 작업 공간에 복사된 frontend.zip 아티팩트 경로 (경로 정규화)
    $FrontendZip = Join-Path $WebSrc "frontend.zip"
    
    if (Test-Path $FrontendZip) {
        Write-Host "프론트엔드 아티팩트 발견: $FrontendZip"
        
        # 기존 프론트엔드 파일 정리
        if (Test-Path "$WebFrontDst\*") {
            Remove-Item -Path "$WebFrontDst\*" -Recurse -Force
            Write-Host "기존 프론트엔드 파일 정리 완료"
        }
        
        # frontend.zip을 임시 폴더에 압축 해제 (경로 정규화)
        $TempExtractDir = Join-Path $WebFrontDst "temp_extract"
        if (Test-Path $TempExtractDir) {
            Remove-Item -Recurse -Force $TempExtractDir
        }
        New-Item -ItemType Directory -Path $TempExtractDir | Out-Null
        
        # 압축 해제 및 복사
        Expand-Archive -Path $FrontendZip -DestinationPath $TempExtractDir -Force
        Copy-Item -Recurse -Force (Join-Path $TempExtractDir "*") $WebFrontDst
        
        # 임시 폴더 정리
        Remove-Item -Recurse -Force $TempExtractDir
        
        Write-Host "프론트엔드 아티팩트 배포 완료"
    } else {
        throw "프론트엔드 아티팩트를 찾을 수 없습니다: $FrontendZip`nJenkinsfile의 copyArtifacts 단계가 성공했는지 확인하세요."
    }
    
    # 3. 배포 검증
    Write-Host "`n단계 3: 배포 검증 중..."
    
    # index.html 존재 확인
    $indexFile = "$WebFrontDst\index.html"
    if (Test-Path $indexFile) {
        Write-Host "index.html 확인: 정상"
    } else {
        throw "index.html을 찾을 수 없습니다: $indexFile"
    }
    
    # 정적 파일들 확인
    $staticFiles = Get-ChildItem -Path $WebFrontDst -Recurse | Measure-Object
    Write-Host "배포된 파일 수: $($staticFiles.Count)개"
    
    Write-Host "`n===========================================`n"
    Write-Host "프론트엔드 배포 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    Write-Host "• 프론트엔드 URL: /tests/$Bid/"
    Write-Host "• 배포 경로: $WebFrontDst"
    Write-Host "• 배포된 파일 수: $($staticFiles.Count)개"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "프론트엔드 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리
    Write-Host "실패 후 정리 시도 중..."
    
    # 임시 폴더 정리 (실패 시)
    $TempExtractDir = Join-Path $WebFrontDst "temp_extract"
    if (Test-Path $TempExtractDir) {
        Remove-Item -Recurse -Force $TempExtractDir -ErrorAction SilentlyContinue
    }

    throw $_.Exception
}
}