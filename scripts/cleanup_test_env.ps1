# scripts/cleanup_test_env.ps1
# 브랜치별 테스트 인스턴스 정리 스크립트

param(
    [Parameter(Mandatory=$true)][string]$Bid
)

$ErrorActionPreference = "Stop"

$root = "C:\deploys\tests\$Bid"
$Nssm = "nssm"
$Nginx = "C:\nginx\nginx.exe"
$Conf = "C:\nginx\conf\conf.d\tests-$Bid.conf"

Write-Host "===========================================`n"
Write-Host "🧹 테스트 인스턴스 정리 시작`n"
Write-Host "===========================================`n"
Write-Host "• BID: $Bid"
Write-Host "• 정리 대상: $root"
Write-Host "• Nginx 설정: $Conf"
Write-Host "===========================================`n"

try {
    # 1. NSSM 서비스 중지 및 제거
    Write-Host "⏹️ 1단계: NSSM 서비스 중지 중..."
    
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
    Write-Host "`n🌐 2단계: Nginx 설정 정리 중..."
    
    if (Test-Path $Conf) {
        Remove-Item $Conf -Force -ErrorAction SilentlyContinue
        Write-Host "Nginx 설정 파일 제거 완료: $Conf"
        
        # Nginx 리로드
        try {
            & $Nginx -s reload
            Write-Host "Nginx 리로드 완료"
        } catch {
            Write-Warning "Nginx 리로드 실패: $($_.Exception.Message)"
        }
    } else {
        Write-Host "Nginx 설정 파일이 이미 없음: $Conf"
    }
    
    # 3. 배포 디렉토리 제거
    Write-Host "`n🗂️ 3단계: 배포 디렉토리 정리 중..."
    
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
    Write-Host "`n🔍 4단계: 포트 사용 상태 확인..."
    
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
    Write-Host "✅ 테스트 인스턴스 정리 완료!`n"
    Write-Host "===========================================`n"
    Write-Host "• 정리된 BID: $Bid"
    Write-Host "• 제거된 서비스: $webServiceName, $autodocServiceName"
    Write-Host "• 제거된 설정: $Conf"
    Write-Host "• 제거된 디렉토리: $root"
    Write-Host "===========================================`n"
    
} catch {
    Write-Error "테스트 인스턴스 정리 실패: $($_.Exception.Message)"
    Write-Host "`n수동 정리가 필요할 수 있습니다:"
    Write-Host "1. nssm stop cm-web-$Bid; nssm remove cm-web-$Bid confirm"
    Write-Host "2. nssm stop cm-autodoc-$Bid; nssm remove cm-autodoc-$Bid confirm"
    Write-Host "3. Remove-Item $Conf -Force"
    Write-Host "4. C:\nginx\nginx.exe -s reload"
    Write-Host "5. Remove-Item $root -Recurse -Force"
    
    throw $_.Exception
}