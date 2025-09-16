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
                
                # 프로세스 완전 종료 확인 및 강제 종료
                Write-Host "  - 프로세스 완전 종료 확인 중..."
                $maxWait = 15  # 최대 15초 대기
                $waited = 0
                do {
                    Start-Sleep -Seconds 1
                    $waited++
                    $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$oldWebService*" -or $_.CommandLine -like "*uvicorn*" }
                    if (-not $remainingProcess) { break }
                    Write-Host "    프로세스 종료 대기 중... ($waited/$maxWait)"
                } while ($waited -lt $maxWait)
                
                # 강제 종료가 필요한 경우
                if ($remainingProcess) {
                    Write-Warning "  - 프로세스가 완전히 종료되지 않았습니다. 강제 종료를 시도합니다."
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
                
                & $Nssm remove $oldWebService confirm 2>$null
                Write-Host "  - 웹서비스 제거 완료"
            }
            
            # AutoDoc 서비스 정리
            $oldAutoSvc = Get-Service -Name $oldAutoService -ErrorAction SilentlyContinue
            if ($oldAutoSvc) {
                Write-Host "기존 AutoDoc 서비스 중지: $oldAutoService"
                & $Nssm stop $oldAutoService 2>$null
                
                # 프로세스 완전 종료 확인 및 강제 종료
                Write-Host "  - 프로세스 완전 종료 확인 중..."
                $maxWait = 15  # 최대 15초 대기
                $waited = 0
                do {
                    Start-Sleep -Seconds 1
                    $waited++
                    $remainingProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$oldAutoService*" -or $_.CommandLine -like "*autodoc*" }
                    if (-not $remainingProcess) { break }
                    Write-Host "    프로세스 종료 대기 중... ($waited/$maxWait)"
                } while ($waited -lt $maxWait)
                
                # 강제 종료가 필요한 경우
                if ($remainingProcess) {
                    Write-Warning "  - 프로세스가 완전히 종료되지 않았습니다. 강제 종료를 시도합니다."
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
                
                & $Nssm remove $oldAutoService confirm 2>$null
                Write-Host "  - AutoDoc 서비스 제거 완료"
            }
            
            # 추가 대기 시간 (파일 잠금 해제 보장)
            Write-Host "파일 잠금 해제를 위한 추가 대기..."
            Start-Sleep -Seconds 5  # 10초에서 5초로 단축 (프로세스 확인 로직 추가로)
            
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
    
    # 파라미터 검증 강화 (Jenkins 문자열 "null" 처리)
    $backPortType = if ($BackPort -eq $null) { "null" } else { $BackPort.GetType().Name }
    $autoPortType = if ($AutoPort -eq $null) { "null" } else { $AutoPort.GetType().Name }
    
    Write-Host "DEBUG: BackPort 원본 값: [$BackPort] (타입: $backPortType)"
    Write-Host "DEBUG: AutoPort 원본 값: [$AutoPort] (타입: $autoPortType)"
    
    # Jenkins에서 전달되는 문자열 "null" 처리
    if ($BackPort -eq "null" -or $BackPort -eq "") {
        $BackPort = $null
        Write-Host "INFO: BackPort 문자열 'null'을 실제 null로 변환"
    }
    
    if ($AutoPort -eq "null" -or $AutoPort -eq "") {
        $AutoPort = $null
        Write-Host "INFO: AutoPort 문자열 'null'을 실제 null로 변환"
    }
    
    # 단일 서비스 배포 시 파라미터 검증
    if ($BackPort -eq $null -and $AutoPort -eq $null) {
        throw "BackPort와 AutoPort 모두 null입니다. 최소 하나의 포트는 지정되어야 합니다.`n해결방법: PowerShell에서 `$null 대신 문자열 'null'이 전달되었을 가능성을 확인하세요."
    }
    
    # BackPort 검증
    if ($BackPort -ne $null) {
        if ($BackPort -is [int] -and $BackPort -gt 0) {
            $BackPortStr = "$BackPort"
        } elseif ($BackPort -eq "null" -or $BackPort -eq "") {
            Write-Host "INFO: BackPort가 null 또는 빈 값입니다. 스킵합니다."
            $BackPortStr = $null
        } else {
            # 문자열 형태의 포트 번호 처리
            try {
                $BackPortInt = [int]$BackPort
                if ($BackPortInt -gt 0) {
                    $BackPortStr = "$BackPortInt"
                } else {
                    throw "유효하지 않은 포트 번호"
                }
            } catch {
                throw "BackPort는 유효한 포트 번호여야 합니다: [$BackPort]"
            }
        }
    } else {
        $BackPortStr = $null
    }
    
    # AutoPort 검증
    if ($AutoPort -ne $null) {
        if ($AutoPort -is [int] -and $AutoPort -gt 0) {
            $AutoPortStr = "$AutoPort"
        } elseif ($AutoPort -eq "null" -or $AutoPort -eq "") {
            Write-Host "INFO: AutoPort가 null 또는 빈 값입니다. 스킵합니다."
            $AutoPortStr = $null
        } else {
            # 문자열 형태의 포트 번호 처리
            try {
                $AutoPortInt = [int]$AutoPort
                if ($AutoPortInt -gt 0) {
                    $AutoPortStr = "$AutoPortInt"
                } else {
                    throw "유효하지 않은 포트 번호"
                }
            } catch {
                throw "AutoPort는 유효한 포트 번호여야 합니다: [$AutoPort]"
            }
        }
    } else {
        $AutoPortStr = $null
    }
    
    Write-Host "DEBUG: 처리된 BackPortStr: [$BackPortStr]"
    Write-Host "DEBUG: 처리된 AutoPortStr: [$AutoPortStr]"
    
    # 기존 upstream 설정 보존을 위한 로직
    $upstreamOut = Join-Path $includeDir "tests-$Bid.upstream.conf"
    $existingUpstream = ""
    $existingWebUpstream = ""
    $existingAutoUpstream = ""
    
    # 기존 upstream 파일이 있으면 내용 파싱
    if (Test-Path $upstreamOut) {
        $existingUpstream = Get-Content -Raw $upstreamOut
        Write-Host "기존 upstream 설정 발견, 보존할 부분 추출 중..."
        
        # 기존 webservice upstream 추출
        if ($existingUpstream -match "(?ms)(upstream test-$Bid-web \{[^}]*\})") {
            $existingWebUpstream = $matches[1]
            Write-Host "  -> 기존 webservice upstream 보존: $existingWebUpstream"
        }
        
        # 기존 autodoc upstream 추출
        if ($existingUpstream -match "(?ms)(upstream test-$Bid-autodoc \{[^}]*\})") {
            $existingAutoUpstream = $matches[1]
            Write-Host "  -> 기존 autodoc upstream 보존: $existingAutoUpstream"
        }
    }
    
    # 새로운 upstream 설정 생성
    $upstreamParts = @()
    $upstreamParts += "# tests-$Bid.upstream.conf"
    $upstreamParts += "# Upstream configuration for test branch: $Bid"
    $upstreamParts += ""
    
    # BackPort 처리 (새로 지정되거나 기존 것 보존)
    if ($BackPortStr) {
        $upstreamParts += "upstream test-$Bid-web {"
        $upstreamParts += "    server 127.0.0.1:$BackPortStr;"
        $upstreamParts += "}"
        Write-Host "webservice upstream 업데이트: 포트 $BackPortStr"
    } elseif ($existingWebUpstream) {
        $upstreamParts += $existingWebUpstream
        Write-Host "webservice upstream 기존 설정 보존"
    }
    
    # AutoPort 처리 (새로 지정되거나 기존 것 보존)
    if ($AutoPortStr) {
        if ($upstreamParts.Count -gt 3) { $upstreamParts += "" }  # 구분을 위한 빈 줄
        $upstreamParts += "upstream test-$Bid-autodoc {"
        $upstreamParts += "    server 127.0.0.1:$AutoPortStr;"
        $upstreamParts += "}"
        Write-Host "autodoc upstream 업데이트: 포트 $AutoPortStr"
    } elseif ($existingAutoUpstream) {
        if ($upstreamParts.Count -gt 3) { $upstreamParts += "" }  # 구분을 위한 빈 줄
        $upstreamParts += $existingAutoUpstream
        Write-Host "autodoc upstream 기존 설정 보존"
    }
    
    $upstreamConf = $upstreamParts -join "`n"
    
    # Location 설정 파일 생성 (기존 설정 보존)
    $locationOut = Join-Path $includeDir "tests-$Bid.location.conf"
    $existingLocation = ""
    $existingWebLocation = ""
    $existingAutoLocation = ""
    $existingFrontendLocation = ""
    
    # 기존 location 파일이 있으면 내용 파싱
    if (Test-Path $locationOut) {
        $existingLocation = Get-Content -Raw $locationOut
        Write-Host "기존 location 설정 발견, 보존할 부분 추출 중..."
        
        # 기존 webservice location 추출
        if ($existingLocation -match "(?ms)(# Webservice backend API proxy.*?location /tests/$Bid/api/webservice/.*?\})") {
            $existingWebLocation = $matches[1]
            Write-Host "  -> 기존 webservice location 보존"
        }
        
        # 기존 autodoc location 추출
        if ($existingLocation -match "(?ms)(# AutoDoc Service backend API proxy.*?location /tests/$Bid/api/autodoc/.*?\})") {
            $existingAutoLocation = $matches[1]
            Write-Host "  -> 기존 autodoc location 보존"
        }
        
        # 기존 frontend location 추출 (항상 보존)
        if ($existingLocation -match "(?ms)(# Frontend static file serving.*?location /tests/$Bid/.*?\})") {
            $existingFrontendLocation = $matches[1]
            Write-Host "  -> 기존 frontend location 보존"
        }
    }
    
    # 새로운 location 설정 생성
    $locationParts = @()
    $locationParts += "# tests-$Bid.location.conf"
    $locationParts += "# Location blocks for test branch: $Bid"
    $locationParts += "# Windows Nginx: forward slash (/) recommended for path separators"
    $locationParts += ""
    
    # BackPort 처리 (새로 지정되거나 기존 것 보존)
    if ($BackPortStr) {
        $locationParts += "# Webservice backend API proxy (using upstream) - MUST come first!"
        $locationParts += "location /tests/$Bid/api/webservice/ {"
        $locationParts += "    proxy_pass http://test-$Bid-web/api/webservice/;"
        $locationParts += "    proxy_set_header Host `$host;"
        $locationParts += "    proxy_set_header X-Real-IP `$remote_addr;"
        $locationParts += "    proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;"
        $locationParts += "    proxy_set_header X-Forwarded-Proto `$scheme;"
        $locationParts += "    "
        $locationParts += "    # WebSocket support"
        $locationParts += "    proxy_http_version 1.1;"
        $locationParts += "    proxy_set_header Upgrade `$http_upgrade;"
        $locationParts += "    proxy_set_header Connection `"upgrade`";"
        $locationParts += "    "
        $locationParts += "    # Timeout configuration"
        $locationParts += "    proxy_connect_timeout 60s;"
        $locationParts += "    proxy_send_timeout 60s;"
        $locationParts += "    proxy_read_timeout 60s;"
        $locationParts += "}"
        Write-Host "webservice location 업데이트"
    } elseif ($existingWebLocation) {
        $locationParts += $existingWebLocation
        Write-Host "webservice location 기존 설정 보존"
    }
    
    # AutoPort 처리 (새로 지정되거나 기존 것 보존)
    if ($AutoPortStr) {
        if ($locationParts.Count -gt 4) { $locationParts += "" }  # 구분을 위한 빈 줄
        $locationParts += "# AutoDoc Service backend API proxy (using upstream)"
        $locationParts += "location /tests/$Bid/api/autodoc/ {"
        $locationParts += "    proxy_pass http://test-$Bid-autodoc/api/autodoc/;"
        $locationParts += "    proxy_set_header Host `$host;"
        $locationParts += "    proxy_set_header X-Real-IP `$remote_addr;"
        $locationParts += "    proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;"
        $locationParts += "    proxy_set_header X-Forwarded-Proto `$scheme;"
        $locationParts += "    "
        $locationParts += "    # File upload configuration"
        $locationParts += "    client_max_body_size 50M;"
        $locationParts += "    "
        $locationParts += "    # Timeout configuration"
        $locationParts += "    proxy_connect_timeout 30s;"
        $locationParts += "    proxy_send_timeout 30s;"
        $locationParts += "    proxy_read_timeout 30s;"
        $locationParts += "}"
        Write-Host "autodoc location 업데이트"
    } elseif ($existingAutoLocation) {
        if ($locationParts.Count -gt 4) { $locationParts += "" }  # 구분을 위한 빈 줄
        $locationParts += $existingAutoLocation
        Write-Host "autodoc location 기존 설정 보존"
    }
    
    # Frontend location (항상 포함 - 새로 생성하거나 기존 것 보존)
    if ($locationParts.Count -gt 4) { $locationParts += "" }  # 구분을 위한 빈 줄
    if ($existingFrontendLocation) {
        $locationParts += $existingFrontendLocation
        Write-Host "frontend location 기존 설정 보존"
    } else {
        $locationParts += "# Frontend static file serving (comes after API routes)"
        $locationParts += "location /tests/$Bid/ {"
        $locationParts += "    sendfile off;"
        $locationParts += "    alias C:/nginx/html/tests/$Bid/;"
        $locationParts += "    try_files `$uri `$uri/ /tests/$Bid/index.html;"
        $locationParts += "    "
        $locationParts += "    # Static file caching configuration"
        $locationParts += "    # location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {"
        $locationParts += "    #     expires 1h;"
        $locationParts += "    #     add_header Cache-Control `"public, immutable`";"
        $locationParts += "    # }"
        $locationParts += "}"
        Write-Host "frontend location 새로 생성"
    }
    
    $locationConf = $locationParts -join "`n"
    
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

# PowerShell 스크립트에서 함수들이 자동으로 사용 가능