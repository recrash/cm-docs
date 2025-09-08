# scripts/cleanup_test_env.ps1
# 브랜치별 테스트 인스턴스 정리 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid
)

$ErrorActionPreference = "Stop"

# develop 브랜치 보호
if ($Bid -eq "develop") {
    Write-Error "===========================================" 
    Write-Error "경고: develop 브랜치는 삭제할 수 없습니다!"
    Write-Error "===========================================" 
    Write-Error "develop 브랜치는 상시 운영되는 테스트 환경입니다."
    Write-Error "삭제가 필요한 경우 관리자에게 문의하세요."
    Write-Error "===========================================" 
    exit 1
}

$root = "C:\deploys\tests\$Bid"
$Nssm = "nssm"
$Nginx = "C:\nginx\nginx.exe"
# nginx include 방식 설정 파일 경로
$nginxRoot = Split-Path $Nginx -Parent
$upstreamConf = "$nginxRoot\conf\include\tests-$Bid.upstream.conf"
$locationConf = "$nginxRoot\conf\include\tests-$Bid.location.conf"
# 기존 conf.d 방식 파일 (하위 호환성)
$oldConf = "$nginxRoot\conf\conf.d\tests-$Bid.conf"

Write-Host "===========================================`n"
Write-Host "테스트 인스턴스 정리 시작`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• 정리 대상: $root"
Write-Host "• Nginx 설정:"
Write-Host "  - Upstream: $upstreamConf"
Write-Host "  - Location: $locationConf"
Write-Host "===========================================`n"

try {
    # 1. NSSM 서비스 중지 및 제거
    Write-Host "단계 1: NSSM 서비스 중지 중..."
    
    $webServiceName = "cm-web-$Bid"
    $autodocServiceName = "cm-autodoc-$Bid"
    
    # 웹서비스 정리
    try {
        $webStatus = & $Nssm status $webServiceName 2>$null
        if ($webStatus) {
            Write-Host "웹서비스 중지 중: $webServiceName (현재 상태: $webStatus)"
            & $Nssm stop $webServiceName 2>$null
            Start-Sleep -Seconds 2
            & $Nssm remove $webServiceName confirm 2>$null
            Write-Host "웹서비스 제거 완료: $webServiceName"
        } else {
            Write-Host "웹서비스가 이미 없음: $webServiceName"
        }
    } catch {
        Write-Warning "웹서비스 정리 중 오류 (무시): $($_.Exception.Message)"
    }
    
    # AutoDoc 서비스 정리
    try {
        $autodocStatus = & $Nssm status $autodocServiceName 2>$null
        if ($autodocStatus) {
            Write-Host "AutoDoc 서비스 중지 중: $autodocServiceName (현재 상태: $autodocStatus)"
            & $Nssm stop $autodocServiceName 2>$null
            Start-Sleep -Seconds 2
            & $Nssm remove $autodocServiceName confirm 2>$null
            Write-Host "AutoDoc 서비스 제거 완료: $autodocServiceName"
        } else {
            Write-Host "AutoDoc 서비스가 이미 없음: $autodocServiceName"
        }
    } catch {
        Write-Warning "AutoDoc 서비스 정리 중 오류 (무시): $($_.Exception.Message)"
    }
    
    # 2. Nginx 설정 파일 제거 및 리로드
    Write-Host "`n단계 2: Nginx 설정 정리 중..."
    
    # Include 방식 설정 파일 제거
    $configsRemoved = $false
    
    if (Test-Path $upstreamConf) {
        Remove-Item $upstreamConf -Force -ErrorAction SilentlyContinue
        Write-Host "Nginx upstream 설정 파일 제거 완료: $upstreamConf"
        $configsRemoved = $true
    } else {
        Write-Host "Nginx upstream 설정 파일이 이미 없음: $upstreamConf"
    }
    
    if (Test-Path $locationConf) {
        Remove-Item $locationConf -Force -ErrorAction SilentlyContinue
        Write-Host "Nginx location 설정 파일 제거 완료: $locationConf"
        $configsRemoved = $true
    } else {
        Write-Host "Nginx location 설정 파일이 이미 없음: $locationConf"
    }
    
    # 기존 conf.d 방식 파일도 제거 (하위 호환성)
    if (Test-Path $oldConf) {
        Remove-Item $oldConf -Force -ErrorAction SilentlyContinue
        Write-Host "기존 conf.d 설정 파일 제거 완료: $oldConf"
        $configsRemoved = $true
    }
    
    # Nginx 리로드 (설정 파일이 제거된 경우에만)
    if ($configsRemoved) {
        try {
            # PowerShell 서비스 재시작 사용
            Restart-Service -Name "nginx-frontend" -Force
            Write-Host "Nginx 서비스 재시작 완료"
        } catch {
            Write-Warning "Nginx 서비스 재시작 실패, 직접 reload 시도: $($_.Exception.Message)"
            try {
                & $Nginx -p "$nginxRoot" -s reload 2>$null
                Write-Host "Nginx 직접 리로드 완료"
            } catch {
                Write-Warning "Nginx 리로드 실패: $($_.Exception.Message)"
            }
        }
    }
    
    # 3. 배포 디렉토리 제거
    Write-Host "`n단계 3: 배포 디렉토리 정리 중..."
    
    if (Test-Path $root) {
        # 파일 잠금 해제를 위한 대기
        Start-Sleep -Seconds 3
        
        try {
            Remove-Item $root -Recurse -Force -ErrorAction Stop
            Write-Host "배포 디렉토리 제거 완료: $root"
        } catch {
            Write-Warning "배포 디렉토리 제거 중 일부 파일 잠김: $($_.Exception.Message)"
            Write-Host "잠긴 파일이 있으면 수동으로 정리해주세요: $root"
        }
    } else {
        Write-Host "배포 디렉토리가 이미 없음: $root"
    }
    
    # 4. 포트 사용 확인 (정보성)
    Write-Host "`n단계 4: 포트 사용 상태 확인..."
    
    $backPort = [int]$Bid.GetHashCode() % 200 + 8100
    $autoPort = [int]$Bid.GetHashCode() % 200 + 8500
    
    try {
        $portCheck = netstat -an | Select-String ":$backPort " -Quiet
        if (-not $portCheck) {
            Write-Host "백엔드 포트 해제 확인: $backPort"
        } else {
            Write-Warning "백엔드 포트가 여전히 사용 중일 수 있음: $backPort"
        }
        
        $autoPortCheck = netstat -an | Select-String ":$autoPort " -Quiet
        if (-not $autoPortCheck) {
            Write-Host "AutoDoc 포트 해제 확인: $autoPort"
        } else {
            Write-Warning "AutoDoc 포트가 여전히 사용 중일 수 있음: $autoPort"
        }
    } catch {
        Write-Warning "포트 상태 확인 실패: $($_.Exception.Message)"
    }
    
    Write-Host "`n===========================================`n"
    Write-Host "테스트 인스턴스 정리 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 정리된 BID: $Bid"
    Write-Host "• 제거된 서비스: $webServiceName, $autodocServiceName"
    Write-Host "• 제거된 설정: upstream, location 설정 파일"
    Write-Host "• 제거된 디렉토리: $root"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "테스트 인스턴스 정리 실패: $($_.Exception.Message)"
    Write-Host "`n수동 정리가 필요할 수 있습니다:"
    Write-Host "1. nssm stop cm-web-$Bid; nssm remove cm-web-$Bid confirm"
    Write-Host "2. nssm stop cm-autodoc-$Bid; nssm remove cm-autodoc-$Bid confirm"
    Write-Host "3. Remove-Item $upstreamConf -Force"
    Write-Host "4. Remove-Item $locationConf -Force"
    Write-Host "5. Restart-Service -Name nginx-frontend -Force"
    Write-Host "6. Remove-Item $root -Recurse -Force"
    
    throw $_.Exception
}