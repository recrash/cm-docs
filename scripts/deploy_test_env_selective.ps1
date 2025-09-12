# scripts/deploy_test_env_selective.ps1
# 선택적 서비스 배포 스크립트 (기존 deploy_test_env.ps1의 개선 버전)

param(
    [Parameter(Mandatory=$true)][string]$Bid,
    [Parameter(Mandatory=$true)][int]$BackPort,
    [Parameter(Mandatory=$true)][int]$AutoPort,
    [Parameter(Mandatory=$true)][string]$Py,
    [Parameter(Mandatory=$true)][string]$Nssm,
    [Parameter(Mandatory=$true)][string]$Nginx,
    [Parameter(Mandatory=$true)][string]$NginxConfDir,
    [Parameter(Mandatory=$true)][string]$WebSrc,      # repo/webservice
    [Parameter(Mandatory=$true)][string]$AutoSrc,     # repo/autodoc_service
    [Parameter(Mandatory=$true)][string]$WebBackDst,  # C:\deploys\test\{BID}\apps\webservice
    [Parameter(Mandatory=$true)][string]$WebFrontDst, # C:\nginx\html\tests\{BID}
    [Parameter(Mandatory=$true)][string]$AutoDst,     # C:\deploys\test\{BID}\apps\autodoc_service
    [Parameter(Mandatory=$true)][string]$UrlPrefix,   # "/tests/{BID}/"
    [Parameter(Mandatory=$true)][string]$PackagesRoot, # "C:\deploys\test\{BID}\packages"
    
    # 선택적 배포 옵션 (기본값: 모두 배포)
    [switch]$DeployFrontend = $true,
    [switch]$DeployWebservice = $true,
    [switch]$DeployAutodoc = $true,
    
    # 개별 서비스만 배포하는 옵션
    [switch]$FrontendOnly = $false,
    [switch]$WebserviceOnly = $false,
    [switch]$AutodocOnly = $false
)

$ErrorActionPreference = "Stop"

# UTF-8 출력 설정 (한글 지원)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 개별 배포 옵션이 지정된 경우 해당 서비스만 배포
if ($FrontendOnly) {
    $DeployFrontend = $true
    $DeployWebservice = $false
    $DeployAutodoc = $false
} elseif ($WebserviceOnly) {
    $DeployFrontend = $false
    $DeployWebservice = $true
    $DeployAutodoc = $false
} elseif ($AutodocOnly) {
    $DeployFrontend = $false
    $DeployWebservice = $false
    $DeployAutodoc = $true
}

Write-Host "===========================================`n"
Write-Host "테스트 인스턴스 선택적 배포 시작`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• Backend Port: $BackPort"
Write-Host "• AutoDoc Port: $AutoPort"
Write-Host "• URL Prefix: $UrlPrefix"
Write-Host "• Packages Root: $PackagesRoot"
Write-Host "• 배포 옵션:"
Write-Host "  - 프론트엔드: $(if($DeployFrontend){'✓'}else{'✗'})"
Write-Host "  - 웹서비스: $(if($DeployWebservice){'✓'}else{'✗'})"
Write-Host "  - AutoDoc: $(if($DeployAutodoc){'✓'}else{'✗'})"
Write-Host "===========================================`n"

try {
    # 공통 초기화 (모든 경우에 필요)
    . "$PSScriptRoot\deploy_common.ps1" -Bid $Bid -Nssm $Nssm -Nginx $Nginx -PackagesRoot $PackagesRoot
    Cleanup-OldBranchFolders -Bid $Bid -Nssm $Nssm
    
    # 배포할 서비스 개수 계산
    $deployCount = 0
    if ($DeployFrontend) { $deployCount++ }
    if ($DeployWebservice) { $deployCount++ }
    if ($DeployAutodoc) { $deployCount++ }
    
    $currentStep = 1
    
    # 1. 프론트엔드 배포
    if ($DeployFrontend) {
        Write-Host "`n[$currentStep/$deployCount] 프론트엔드 배포 실행 중..."
        
        $frontendParams = @{
            Bid = $Bid
            WebSrc = $WebSrc
            WebFrontDst = $WebFrontDst
            UrlPrefix = $UrlPrefix
            PackagesRoot = $PackagesRoot
        }
        
        try {
            & "$PSScriptRoot\deploy_frontend_only.ps1" @frontendParams
            Write-Host "✓ 프론트엔드 배포 성공"
        } catch {
            Write-Error "✗ 프론트엔드 배포 실패: $($_.Exception.Message)"
            if ($FrontendOnly) { throw }
            Write-Warning "프론트엔드 배포 실패했지만 다른 서비스 배포 계속 진행"
        }
        
        $currentStep++
    }
    
    # 2. 웹서비스 배포
    if ($DeployWebservice) {
        Write-Host "`n[$currentStep/$deployCount] 웹서비스 배포 실행 중..."
        
        $webserviceParams = @{
            Bid = $Bid
            BackPort = $BackPort
            Py = $Py
            Nssm = $Nssm
            Nginx = $Nginx
            WebSrc = $WebSrc
            WebBackDst = $WebBackDst
            PackagesRoot = $PackagesRoot
        }
        
        try {
            & "$PSScriptRoot\deploy_webservice_only.ps1" @webserviceParams
            Write-Host "✓ 웹서비스 배포 성공"
        } catch {
            Write-Error "✗ 웹서비스 배포 실패: $($_.Exception.Message)"
            if ($WebserviceOnly) { throw }
            Write-Warning "웹서비스 배포 실패했지만 다른 서비스 배포 계속 진행"
        }
        
        $currentStep++
    }
    
    # 3. AutoDoc 배포
    if ($DeployAutodoc) {
        Write-Host "`n[$currentStep/$deployCount] AutoDoc 서비스 배포 실행 중..."
        
        $autodocParams = @{
            Bid = $Bid
            AutoPort = $AutoPort
            Py = $Py
            Nssm = $Nssm
            Nginx = $Nginx
            AutoSrc = $AutoSrc
            AutoDst = $AutoDst
            PackagesRoot = $PackagesRoot
        }
        
        try {
            & "$PSScriptRoot\deploy_autodoc_only.ps1" @autodocParams
            Write-Host "✓ AutoDoc 서비스 배포 성공"
        } catch {
            Write-Error "✗ AutoDoc 서비스 배포 실패: $($_.Exception.Message)"
            if ($AutodocOnly) { throw }
            Write-Warning "AutoDoc 서비스 배포 실패했지만 다른 서비스 배포 계속 진행"
        }
        
        $currentStep++
    }
    
    # 4. 통합 Nginx 설정 업데이트 (여러 서비스가 배포된 경우)
    if ($deployCount -gt 1) {
        Write-Host "`n통합 Nginx 설정 업데이트 중..."
        
        $backPortParam = if ($DeployWebservice) { $BackPort } else { $null }
        $autoPortParam = if ($DeployAutodoc) { $AutoPort } else { $null }
        
        Update-NginxConfig -Bid $Bid -BackPort $backPortParam -AutoPort $autoPortParam -Nginx $Nginx
    }
    
    # 5. 통합 서비스 상태 확인
    Write-Host "`n최종 서비스 상태 확인 중..."
    
    $backPortParam = if ($DeployWebservice) { $BackPort } else { $null }
    $autoPortParam = if ($DeployAutodoc) { $AutoPort } else { $null }
    
    Test-ServiceHealth -BackPort $backPortParam -AutoPort $autoPortParam -Bid $Bid -Nssm $Nssm
    
    Write-Host "`n===========================================`n"
    Write-Host "테스트 인스턴스 선택적 배포 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 브랜치 ID: $Bid"
    if ($DeployWebservice) {
        Write-Host "• 웹서비스: http://localhost:$BackPort"
    }
    if ($DeployAutodoc) {
        Write-Host "• AutoDoc: http://localhost:$AutoPort"
    }
    if ($DeployFrontend) {
        Write-Host "• 프론트엔드 URL: /tests/$Bid/"
    }
    Write-Host "• 로그 디렉토리: $PackagesRoot\..\logs"
    Write-Host "• Wheel 경로: $PackagesRoot"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "테스트 인스턴스 선택적 배포 실패: $($_.Exception.Message)"
    
    # 실패 시 정리 (배포하려던 서비스들만)
    Write-Host "실패 후 정리 시도 중..."
    
    if ($DeployWebservice) {
        $cleanupWebSvc = Get-Service -Name "cm-web-$Bid" -ErrorAction SilentlyContinue
        if ($cleanupWebSvc) {
            & $Nssm stop "cm-web-$Bid" 2>$null
            & $Nssm remove "cm-web-$Bid" confirm 2>$null
        }
    }
    
    if ($DeployAutodoc) {
        $cleanupAutoSvc = Get-Service -Name "cm-autodoc-$Bid" -ErrorAction SilentlyContinue
        if ($cleanupAutoSvc) {
            & $Nssm stop "cm-autodoc-$Bid" 2>$null
            & $Nssm remove "cm-autodoc-$Bid" confirm 2>$null
        }
    }
    
    throw $_.Exception
}