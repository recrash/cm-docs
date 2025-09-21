# scripts/deploy_frontend_only.ps1
# 프론트엔드만 배포하는 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][string]$WebSrc,      # repo/webservice
    [Parameter(Mandatory=$true)][string]$WebFrontDst, # C:\nginx\html\tests\{BID}
    [Parameter(Mandatory=$true)][string]$UrlPrefix,   # "/tests/{BID}/"
    [Parameter(Mandatory=$true)][string]$PackagesRoot # "C:\deploys\tests\{BID}\packages"
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "===========================================`n"
Write-Host "프론트엔드 배포 시작 (독립 배포)`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• URL Prefix: $UrlPrefix"
Write-Host "• Frontend Destination: $WebFrontDst"
Write-Host "===========================================`n"

try {
    # 1. 디렉토리 구조 생성
    Write-Host "단계 1: 프론트엔드 디렉토리 생성 중..."
    New-Item -ItemType Directory -Force -Path $WebFrontDst | Out-Null
    Write-Host "프론트엔드 디렉토리 생성 완료: $WebFrontDst"
    
    # 2. 프론트엔드 아티팩트 배포
    Write-Host "`n단계 2: 프론트엔드 아티팩트 배포 중..."
    
    # 현재 작업 공간에 복사된 frontend.zip 아티팩트 경로
    $FrontendZip = "$WebSrc\frontend.zip"
    
    if (Test-Path $FrontendZip) {
        Write-Host "프론트엔드 아티팩트 발견: $FrontendZip"
        
        # 기존 프론트엔드 파일 정리
        if (Test-Path "$WebFrontDst\*") {
            Remove-Item -Path "$WebFrontDst\*" -Recurse -Force
            Write-Host "기존 프론트엔드 파일 정리 완료"
        }
        
        # frontend.zip을 임시 폴더에 압축 해제
        $TempExtractDir = "$WebFrontDst\temp_extract"
        if (Test-Path $TempExtractDir) {
            Remove-Item -Recurse -Force $TempExtractDir
        }
        New-Item -ItemType Directory -Path $TempExtractDir | Out-Null
        
        # 압축 해제 및 복사
        Expand-Archive -Path $FrontendZip -DestinationPath $TempExtractDir -Force
        Copy-Item -Recurse -Force "$TempExtractDir\*" $WebFrontDst
        
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
    
    # 임시 폴더 정리
    $TempExtractDir = "$WebFrontDst\temp_extract"
    if (Test-Path $TempExtractDir) {
        Remove-Item -Recurse -Force $TempExtractDir -ErrorAction SilentlyContinue
    }
    
    throw $_.Exception
}