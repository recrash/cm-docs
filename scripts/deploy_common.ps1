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

# ===============================================
# 배포 락 메커니즘 함수들
# ===============================================

function Acquire-DeploymentLock {
    param(
        [Parameter(Mandatory=$true)]
        [string]$LockType,

        [Parameter(Mandatory=$false)]
        [int]$TimeoutSeconds = 60,

        [Parameter(Mandatory=$false)]
        [string]$LockReason = "배포 작업"
    )

    $lockDir = "C:\deploys\locks"
    $lockFile = "$lockDir\$LockType.lock"
    $processId = $PID
    $hostName = $env:COMPUTERNAME
    $userName = $env:USERNAME
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    # 락 디렉토리 생성
    if (-not (Test-Path $lockDir)) {
        New-Item -ItemType Directory -Force -Path $lockDir | Out-Null
    }

    $startTime = Get-Date
    $lockAcquired = $false

    Write-Host "[$LockType] 락 획득 시도 중... (최대 ${TimeoutSeconds}초 대기)"

    while (-not $lockAcquired -and ((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        try {
            # 기존 락 파일 확인
            if (Test-Path $lockFile) {
                $lockContent = Get-Content $lockFile -Raw -ErrorAction SilentlyContinue
                if ($lockContent) {
                    $lockInfo = $lockContent | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($lockInfo) {
                        $lockAge = (Get-Date) - [DateTime]::Parse($lockInfo.Timestamp)

                        # 락이 10분 이상 오래되었으면 삭제 (좀비 락 방지)
                        if ($lockAge.TotalMinutes -gt 10) {
                            Write-Host "[$LockType] 오래된 락 파일 발견 (${lockAge.TotalMinutes:F1}분). 정리합니다."
                            Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
                        } else {
                            Write-Host "[$LockType] 락이 사용 중입니다. 소유자: $($lockInfo.UserName)@$($lockInfo.HostName) (PID: $($lockInfo.ProcessId))"
                            Start-Sleep -Seconds 2
                            continue
                        }
                    }
                }
            }

            # 락 파일 생성 시도
            $lockData = @{
                LockType = $LockType
                ProcessId = $processId
                HostName = $hostName
                UserName = $userName
                Timestamp = $timestamp
                Reason = $LockReason
            } | ConvertTo-Json -Compress

            # 원자적 락 파일 생성 (임시 파일 → 이동)
            $tempFile = "$lockFile.tmp.$processId"
            $lockData | Out-File -FilePath $tempFile -Encoding UTF8 -NoNewline
            Move-Item $tempFile $lockFile -ErrorAction Stop

            $lockAcquired = $true
            Write-Host "[$LockType] 락 획득 성공! (프로세스: $processId, 사용자: $userName)"

        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    if (-not $lockAcquired) {
        throw "[$LockType] 락 획득 실패: ${TimeoutSeconds}초 내에 락을 획득할 수 없습니다."
    }

    return $lockFile
}

function Release-DeploymentLock {
    param(
        [Parameter(Mandatory=$true)]
        [string]$LockType
    )

    $lockDir = "C:\deploys\locks"
    $lockFile = "$lockDir\$LockType.lock"

    try {
        if (Test-Path $lockFile) {
            # 락 소유권 확인
            $lockContent = Get-Content $lockFile -Raw -ErrorAction SilentlyContinue
            if ($lockContent) {
                $lockInfo = $lockContent | ConvertFrom-Json -ErrorAction SilentlyContinue
                if ($lockInfo -and $lockInfo.ProcessId -eq $PID) {
                    Remove-Item $lockFile -Force
                    Write-Host "[$LockType] 락 해제 완료 (프로세스: $PID)"
                } else {
                    Write-Host "[$LockType] 경고: 다른 프로세스가 소유한 락입니다. 강제 해제하지 않습니다."
                }
            } else {
                # 빈 락 파일이면 제거
                Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
                Write-Host "[$LockType] 빈 락 파일 정리 완료"
            }
        }
    } catch {
        Write-Host "[$LockType] 락 해제 중 에러: $($_.Exception.Message)"
    }
}

function Test-LockAvailable {
    param(
        [Parameter(Mandatory=$true)]
        [string]$LockType
    )

    $lockDir = "C:\deploys\locks"
    $lockFile = "$lockDir\$LockType.lock"

    if (-not (Test-Path $lockFile)) {
        return $true
    }

    try {
        $lockContent = Get-Content $lockFile -Raw -ErrorAction SilentlyContinue
        if (-not $lockContent) {
            return $true
        }

        $lockInfo = $lockContent | ConvertFrom-Json -ErrorAction SilentlyContinue
        if (-not $lockInfo) {
            return $true
        }

        $lockAge = (Get-Date) - [DateTime]::Parse($lockInfo.Timestamp)

        # 10분 이상 오래된 락은 사실상 사용 가능
        if ($lockAge.TotalMinutes -gt 10) {
            return $true
        }

        return $false
    } catch {
        return $true
    }
}

# ===============================================
# NSSM 서비스 관리 함수들 (락 보호)
# ===============================================

function Register-Service-WithLock {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,

        [Parameter(Mandatory=$true)]
        [string]$ExecutablePath,

        [Parameter(Mandatory=$true)]
        [string]$Arguments,

        [Parameter(Mandatory=$true)]
        [string]$NssmPath,

        [Parameter(Mandatory=$false)]
        [int]$TimeoutSeconds = 60
    )

    $lockFile = $null
    try {
        # NSSM 서비스 등록 락 획득
        $lockFile = Acquire-DeploymentLock -LockType "nssm-service" -TimeoutSeconds $TimeoutSeconds -LockReason "NSSM 서비스 등록 ($ServiceName)"

        Write-Host "NSSM 서비스 등록 중... (락 보호됨): $ServiceName"

        # 기존 서비스 확인 및 제거
        $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Host "기존 서비스 발견, 제거 중: $ServiceName"

            # 서비스 중지
            if ($existingService.Status -eq "Running") {
                Write-Host "  -> 서비스 중지 중..."
                & $NssmPath stop $ServiceName 2>$null
                Start-Sleep -Seconds 5
            }

            # 서비스 제거
            Write-Host "  -> 서비스 제거 중..."
            & $NssmPath remove $ServiceName confirm 2>$null
            Start-Sleep -Seconds 2
        }

        # 새 서비스 설치
        Write-Host "  -> 새 서비스 설치: $ServiceName"
        $installResult = & $NssmPath install $ServiceName $ExecutablePath $Arguments 2>&1

        if ($LASTEXITCODE -ne 0) {
            throw "NSSM 서비스 설치 실패 (ExitCode: $LASTEXITCODE): $installResult"
        }

        # 서비스 시작
        Write-Host "  -> 서비스 시작 중..."
        $startResult = & $NssmPath start $ServiceName 2>&1

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "NSSM 서비스 시작 실패 (ExitCode: $LASTEXITCODE): $startResult"
            Write-Host "Windows 서비스로 시작 시도..."
            Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
        }

        # 서비스 상태 확인
        Start-Sleep -Seconds 3
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service -and $service.Status -eq "Running") {
            Write-Host "✓ NSSM 서비스 등록 및 시작 완료: $ServiceName (상태: $($service.Status))"
        } else {
            $statusText = if ($service) { $service.Status } else { 'N/A' }
            Write-Warning "NSSM 서비스 등록은 완료되었으나 상태가 비정상입니다: $ServiceName (상태: $statusText)"
        }

    } catch {
        Write-Error "NSSM 서비스 등록 실패: $ServiceName - $($_.Exception.Message)"
        throw
    } finally {
        # NSSM 서비스 등록 락 해제
        if ($lockFile) {
            Release-DeploymentLock -LockType "nssm-service"
        }
    }
}

function Unregister-Service-WithLock {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,

        [Parameter(Mandatory=$true)]
        [string]$NssmPath,

        [Parameter(Mandatory=$false)]
        [int]$TimeoutSeconds = 60
    )

    $lockFile = $null
    try {
        # NSSM 서비스 등록 락 획득
        $lockFile = Acquire-DeploymentLock -LockType "nssm-service" -TimeoutSeconds $TimeoutSeconds -LockReason "NSSM 서비스 제거 ($ServiceName)"

        Write-Host "NSSM 서비스 제거 중... (락 보호됨): $ServiceName"

        $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($existingService) {
            # 서비스 중지
            if ($existingService.Status -eq "Running") {
                Write-Host "  -> 서비스 중지 중..."
                & $NssmPath stop $ServiceName 2>$null
                Start-Sleep -Seconds 5

                # 강제 프로세스 종료
                $processName = $ServiceName.Replace("cm-", "").Replace("-$Bid", "")
                Get-Process -Name "*python*" -ErrorAction SilentlyContinue |
                Where-Object { $_.CommandLine -like "*$ServiceName*" -or $_.CommandLine -like "*$processName*" } |
                ForEach-Object {
                    Write-Host "  -> 관련 프로세스 강제 종료: $($_.ProcessName) (PID: $($_.Id))"
                    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
                }
                Start-Sleep -Seconds 2
            }

            # 서비스 제거
            Write-Host "  -> 서비스 제거 중..."
            & $NssmPath remove $ServiceName confirm 2>$null
            Write-Host "✓ NSSM 서비스 제거 완료: $ServiceName"
        } else {
            Write-Host "제거할 서비스가 존재하지 않습니다: $ServiceName"
        }

    } catch {
        Write-Error "NSSM 서비스 제거 실패: $ServiceName - $($_.Exception.Message)"
        throw
    } finally {
        # NSSM 서비스 등록 락 해제
        if ($lockFile) {
            Release-DeploymentLock -LockType "nssm-service"
        }
    }
}

# ===============================================
# 향상된 프로세스 정리 시스템
# ===============================================

function Stop-ServiceGracefully {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,

        [Parameter(Mandatory=$true)]
        [string]$NssmPath,

        [Parameter(Mandatory=$false)]
        [int]$MaxWaitSeconds = 30,

        [Parameter(Mandatory=$false)]
        [switch]$ForceKill
    )

    Write-Host "서비스 안전 중지 중: $ServiceName"

    # 1. 서비스 존재 확인
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Host "  -> 서비스가 존재하지 않습니다: $ServiceName"
        return $true
    }

    Write-Host "  -> 현재 상태: $($service.Status)"

    # 2. 이미 중지된 경우 빠른 리턴
    if ($service.Status -eq "Stopped") {
        Write-Host "  -> 이미 중지된 상태입니다"
        return $true
    }

    # 3. NSSM을 통한 정상 중지 시도
    try {
        Write-Host "  -> NSSM 정상 중지 시도..."
        & $NssmPath stop $ServiceName 2>$null
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "  -> NSSM 중지 실패: $($_.Exception.Message)"
    }

    # 4. 프로세스 완전 종료 확인
    $startTime = Get-Date
    $processTerminated = $false

    while (((Get-Date) - $startTime).TotalSeconds -lt $MaxWaitSeconds -and -not $processTerminated) {
        # 서비스 상태 재확인
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if (-not $service -or $service.Status -eq "Stopped") {
            $processTerminated = $true
            break
        }

        # 관련 프로세스 확인
        $relatedProcesses = Get-Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ProcessName -like "*python*" -and
            ($_.CommandLine -like "*$ServiceName*" -or $_.CommandLine -like "*uvicorn*")
        }

        if ($relatedProcesses.Count -eq 0) {
            $processTerminated = $true
            break
        }

        Write-Host "  -> 프로세스 종료 대기 중... ($([int]((Get-Date) - $startTime).TotalSeconds)/$MaxWaitSeconds 초)"
        Start-Sleep -Seconds 2
    }

    # 5. 강제 종료 (필요시)
    if (-not $processTerminated) {
        if ($ForceKill) {
            Write-Host "  -> 강제 프로세스 종료 시작..."

            # Python 프로세스 강제 종료
            Get-Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.ProcessName -like "*python*" -and
                ($_.CommandLine -like "*$ServiceName*" -or $_.CommandLine -like "*uvicorn*")
            } |
            ForEach-Object {
                Write-Host "    - 프로세스 강제 종료: $($_.ProcessName) (PID: $($_.Id))"
                try {
                    Stop-Process -Id $_.Id -Force -ErrorAction Stop
                } catch {
                    Write-Warning "    - 프로세스 강제 종료 실패 (PID: $($_.Id)): $($_.Exception.Message)"
                }
            }

            # Windows 서비스 강제 중지
            try {
                Stop-Service -Name $ServiceName -Force -ErrorAction Stop
                Write-Host "    - Windows 서비스 강제 중지 완료"
            } catch {
                Write-Warning "    - Windows 서비스 강제 중지 실패: $($_.Exception.Message)"
            }

            Start-Sleep -Seconds 3
            $processTerminated = $true
        } else {
            Write-Warning "  -> 프로세스가 ${MaxWaitSeconds}초 내에 종료되지 않았습니다. 강제 종료가 필요할 수 있습니다."
            return $false
        }
    }

    # 6. 파일 잠금 해제 확인
    Write-Host "  -> 파일 잠금 해제 확인 중..."
    Start-Sleep -Seconds 2

    # 7. 최종 상태 확인
    $finalService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($finalService -and $finalService.Status -eq "Stopped") {
        Write-Host "✓ 서비스 안전 중지 완료: $ServiceName"
        return $true
    } elseif (-not $finalService) {
        Write-Host "✓ 서비스 제거 확인: $ServiceName"
        return $true
    } else {
        Write-Warning "✗ 서비스 중지 실패: $ServiceName (상태: $($finalService.Status))"
        return $false
    }
}

function Test-FileLockStatus {
    param(
        [Parameter(Mandatory=$true)]
        [string]$FilePath,

        [Parameter(Mandatory=$false)]
        [int]$TimeoutSeconds = 10
    )

    if (-not (Test-Path $FilePath)) {
        return $true  # 파일이 없으면 잠금도 없음
    }

    $startTime = Get-Date
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        try {
            # 파일 쓰기 시도로 잠금 상태 확인
            $testFile = "$FilePath.locktest"
            "test" | Out-File -FilePath $testFile -ErrorAction Stop
            Remove-Item $testFile -Force -ErrorAction SilentlyContinue
            return $true  # 잠금 없음
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false  # 잠금 상태
}

function Remove-DirectoryGracefully {
    param(
        [Parameter(Mandatory=$true)]
        [string]$DirectoryPath,

        [Parameter(Mandatory=$false)]
        [int]$MaxRetries = 3,

        [Parameter(Mandatory=$false)]
        [int]$DelayBetweenRetries = 2
    )

    if (-not (Test-Path $DirectoryPath)) {
        Write-Host "  -> 디렉토리가 이미 존재하지 않습니다: $DirectoryPath"
        return $true
    }

    Write-Host "  -> 디렉토리 안전 제거 중: $DirectoryPath"

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            # 디렉토리 내 실행 파일들의 잠금 상태 확인
            $executableFiles = Get-ChildItem -Path $DirectoryPath -Recurse -Include "*.exe", "*.dll" -ErrorAction SilentlyContinue
            $lockedFiles = @()

            foreach ($file in $executableFiles) {
                if (-not (Test-FileLockStatus -FilePath $file.FullName -TimeoutSeconds 2)) {
                    $lockedFiles += $file.FullName
                }
            }

            if ($lockedFiles.Count -gt 0) {
                Write-Host "    - 잠금된 파일 발견 (시도 $attempt/$MaxRetries): $($lockedFiles.Count)개"
                if ($attempt -lt $MaxRetries) {
                    Write-Host "    - ${DelayBetweenRetries}초 후 재시도..."
                    Start-Sleep -Seconds $DelayBetweenRetries
                    continue
                }
            }

            # 디렉토리 제거 시도
            Remove-Item -Path $DirectoryPath -Recurse -Force -ErrorAction Stop
            Write-Host "  ✓ 디렉토리 제거 완료: $DirectoryPath"
            return $true

        } catch {
            Write-Host "    - 디렉토리 제거 실패 (시도 $attempt/$MaxRetries): $($_.Exception.Message)"
            if ($attempt -lt $MaxRetries) {
                Start-Sleep -Seconds $DelayBetweenRetries
            }
        }
    }

    Write-Warning "  ✗ 디렉토리 제거 실패 (최대 재시도 도달): $DirectoryPath"
    return $false
}

# ===============================================
# 포트 충돌 방지 시스템
# ===============================================

function Test-PortAvailable {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$false)]
        [string]$ProcessName = $null
    )
    
    Write-Host "포트 가용성 확인: $Port"
    
    try {
        # 1. 포트 사용 중인 프로세스 확인
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        
        if ($connections) {
            foreach ($conn in $connections) {
                $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "  -> 포트 $Port 사용 중: PID=$($process.Id), 프로세스=$($process.ProcessName)"
                    
                    # 지정된 프로세스명과 일치하는지 확인
                    if ($ProcessName -and $process.ProcessName -like "*$ProcessName*") {
                        Write-Host "  -> 동일 서비스 프로세스로 판단됨: $ProcessName"
                        return $false, "SAME_SERVICE", $process
                    } else {
                        Write-Host "  -> 다른 프로세스가 포트를 사용 중"
                        return $false, "CONFLICT", $process
                    }
                }
            }
        }
        
        # 2. TCP 리스너 확인
        $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if ($listeners) {
            Write-Host "  -> 포트 $Port 에서 리스너 발견"
            return $false, "LISTENER", $null
        }
        
        Write-Host "  -> 포트 $Port 사용 가능"
        return $true, "AVAILABLE", $null
        
    } catch {
        Write-Warning "포트 확인 중 오류: $($_.Exception.Message)"
        return $false, "ERROR", $null
    }
}

function Wait-ForPortRelease {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$false)]
        [int]$MaxWaitSeconds = 60,
        
        [Parameter(Mandatory=$false)]
        [int]$CheckIntervalSeconds = 2
    )
    
    Write-Host "포트 해제 대기: $Port (최대 ${MaxWaitSeconds}초)"
    
    $elapsed = 0
    while ($elapsed -lt $MaxWaitSeconds) {
        $available, $status, $process = Test-PortAvailable -Port $Port
        
        if ($available) {
            Write-Host "  -> 포트 $Port 해제 완료 (${elapsed}초 경과)"
            return $true
        }
        
        Write-Host "  -> 포트 해제 대기 중... (${elapsed}/${MaxWaitSeconds}초)"
        Start-Sleep -Seconds $CheckIntervalSeconds
        $elapsed += $CheckIntervalSeconds
    }
    
    Write-Warning "포트 $Port 해제 시간 초과 (${MaxWaitSeconds}초)"
    return $false
}

function Resolve-PortConflict {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [Parameter(Mandatory=$false)]
        [string]$ServiceName = $null,
        
        [Parameter(Mandatory=$false)]
        [string]$NssmPath = $null,
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceKill
    )
    
    Write-Host "포트 충돌 해결 시도: $Port"
    
    $available, $status, $process = Test-PortAvailable -Port $Port
    
    if ($available) {
        Write-Host "  -> 포트 사용 가능"
        return $true
    }
    
    switch ($status) {
        "SAME_SERVICE" {
            if ($ServiceName -and $NssmPath) {
                Write-Host "  -> 동일 서비스 프로세스 감지: $ServiceName"
                Write-Host "  -> 기존 서비스 정상 중지 시도..."
                
                $stopResult = Stop-ServiceGracefully -ServiceName $ServiceName -NssmPath $NssmPath -MaxWaitSeconds 30 -ForceKill:$ForceKill
                if ($stopResult) {
                    $waitResult = Wait-ForPortRelease -Port $Port -MaxWaitSeconds 30
                    return $waitResult
                } else {
                    Write-Warning "서비스 중지 실패: $ServiceName"
                    return $false
                }
            } else {
                Write-Warning "서비스 정보 부족으로 자동 해결 불가"
                return $false
            }
        }
        
        "CONFLICT" {
            if ($ForceKill -and $process) {
                Write-Warning "  -> 강제 종료 옵션 활성화: PID=$($process.Id)"
                try {
                    Stop-Process -Id $process.Id -Force
                    $waitResult = Wait-ForPortRelease -Port $Port -MaxWaitSeconds 15
                    return $waitResult
                } catch {
                    Write-Error "프로세스 강제 종료 실패: $($_.Exception.Message)"
                    return $false
                }
            } else {
                Write-Error "포트 $Port 가 다른 프로세스에 의해 사용 중입니다. PID=$($process.Id), 프로세스=$($process.ProcessName)"
                Write-Error "해결 방법:"
                Write-Error "  1. 해당 프로세스를 수동으로 종료"
                Write-Error "  2. -ForceKill 옵션 사용 (주의 필요)"
                Write-Error "  3. 다른 포트 사용"
                return $false
            }
        }
        
        "LISTENER" {
            Write-Error "포트 $Port 에서 리스너가 활성화되어 있습니다"
            return $false
        }
        
        default {
            Write-Error "알 수 없는 포트 상태: $status"
            return $false
        }
    }
}

function Validate-DeploymentPorts {
    param(
        [Parameter(Mandatory=$false)]
        [int]$BackPort = $null,
        
        [Parameter(Mandatory=$false)]
        [int]$AutoPort = $null,
        
        [Parameter(Mandatory=$false)]
        [string]$Bid = $null,
        
        [Parameter(Mandatory=$false)]
        [string]$NssmPath = $null,
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceResolve
    )
    
    Write-Host "배포 포트 유효성 검사 시작"
    
    # 필수 포트 범위 검증
    $validPorts = @()
    $conflicts = @()
    
    if ($BackPort) {
        if ($BackPort -lt 1024 -or $BackPort -gt 65535) {
            throw "잘못된 백엔드 포트 범위: $BackPort (1024-65535 범위 필요)"
        }
        $validPorts += @{ Type="Backend"; Port=$BackPort; Service="cm-web-$Bid" }
    }
    
    if ($AutoPort) {
        if ($AutoPort -lt 1024 -or $AutoPort -gt 65535) {
            throw "잘못된 AutoDoc 포트 범위: $AutoPort (1024-65535 범위 필요)"
        }
        $validPorts += @{ Type="AutoDoc"; Port=$AutoPort; Service="cm-autodoc-$Bid" }
    }
    
    # 포트 중복 검사
    if ($BackPort -and $AutoPort -and $BackPort -eq $AutoPort) {
        throw "포트 중복: 백엔드와 AutoDoc 서비스가 동일한 포트를 사용할 수 없습니다 (포트: $BackPort)"
    }
    
    # 각 포트별 충돌 검사 및 해결
    foreach ($portInfo in $validPorts) {
        $port = $portInfo.Port
        $service = $portInfo.Service
        $type = $portInfo.Type
        
        Write-Host "  -> $type 포트 검사: $port"
        
        if ($ForceResolve) {
            $resolved = Resolve-PortConflict -Port $port -ServiceName $service -NssmPath $NssmPath -ForceKill
            if (-not $resolved) {
                $conflicts += "포트 $port ($type) 충돌 해결 실패"
            }
        } else {
            $available, $status, $process = Test-PortAvailable -Port $port
            if (-not $available) {
                $conflicts += "포트 $port ($type) 사용 불가: $status"
            }
        }
    }
    
    # 충돌 결과 보고
    if ($conflicts.Count -gt 0) {
        Write-Error "포트 유효성 검사 실패:"
        foreach ($conflict in $conflicts) {
            Write-Error "  - $conflict"
        }
        
        if (-not $ForceResolve) {
            Write-Error ""
            Write-Error "해결 방법:"
            Write-Error "  1. 충돌하는 서비스를 수동으로 중지"
            Write-Error "  2. Validate-DeploymentPorts -ForceResolve 옵션 사용"
            Write-Error "  3. 다른 포트 번호 사용"
        }
        
        throw "포트 충돌로 인한 배포 실패"
    }
    
    Write-Host "✓ 모든 포트 유효성 검사 통과"
    return $true
}

# ===============================================
# 공통 함수 정의
# ===============================================

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

    Write-Host "단계 0: 기존 폴더 정리 중... (향상된 프로세스 정리 시스템)"
    $testRoot = "C:\deploys\tests"
    $currentBranch = $Bid
    $lowerBranch = $currentBranch.ToLower()

    # 소문자 버전 폴더가 존재하고 현재 브랜치명과 다른 경우 정리
    $lowerBranchPath = "$testRoot\$lowerBranch"
    if (($currentBranch -ne $lowerBranch) -and (Test-Path $lowerBranchPath)) {
        Write-Host "기존 소문자 브랜치 폴더 발견: $lowerBranchPath"

        # 기존 서비스 안전 중지
        try {
            $oldWebService = "cm-web-$lowerBranch"
            $oldAutoService = "cm-autodoc-$lowerBranch"

            # 향상된 웹서비스 정리
            $webStopResult = Stop-ServiceGracefully -ServiceName $oldWebService -NssmPath $Nssm -MaxWaitSeconds 30 -ForceKill
            if ($webStopResult) {
                Unregister-Service-WithLock -ServiceName $oldWebService -NssmPath $Nssm
            } else {
                Write-Warning "웹서비스 중지에 실패했지만 계속 진행합니다: $oldWebService"
            }

            # 향상된 AutoDoc 서비스 정리
            $autoStopResult = Stop-ServiceGracefully -ServiceName $oldAutoService -NssmPath $Nssm -MaxWaitSeconds 30 -ForceKill
            if ($autoStopResult) {
                Unregister-Service-WithLock -ServiceName $oldAutoService -NssmPath $Nssm
            } else {
                Write-Warning "AutoDoc 서비스 중지에 실패했지만 계속 진행합니다: $oldAutoService"
            }

        } catch {
            Write-Warning "기존 서비스 정리 중 오류: $($_.Exception.Message)"
        }

        # 향상된 디렉토리 안전 제거
        $directoryRemoved = Remove-DirectoryGracefully -DirectoryPath $lowerBranchPath -MaxRetries 3 -DelayBetweenRetries 3

        if ($directoryRemoved) {
            Write-Host "✓ 기존 브랜치 폴더 정리 완료: $lowerBranchPath"
        } else {
            Write-Warning "기존 브랜치 폴더 제거 실패 (배포는 계속 진행): $lowerBranchPath"
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
    param(
        [Parameter(Mandatory=$true)]
        [string]$Bid,

        [Parameter(Mandatory=$false)]
        $BackPort = $null,

        [Parameter(Mandatory=$false)]
        $AutoPort = $null,

        [Parameter(Mandatory=$true)]
        [string]$Nginx
    )

    # Nginx 설정 락 획득 (병렬 배포 충돌 방지)
    $lockFile = $null
    try {
        $lockFile = Acquire-DeploymentLock -LockType "nginx-config" -TimeoutSeconds 120 -LockReason "Nginx 설정 업데이트 (Branch: $Bid)"

        Write-Host "Nginx 설정 적용 중... (락 보호됨)"
    
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
        Write-Host "WARNING: BackPort와 AutoPort 모두 null입니다. 기존 upstream 설정을 보존합니다."
        Write-Host "INFO: 이는 정상적인 상황일 수 있습니다 (변경사항이 없거나 기존 설정 유지)"
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

    } finally {
        # Nginx 설정 락 해제
        if ($lockFile) {
            Release-DeploymentLock -LockType "nginx-config"
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