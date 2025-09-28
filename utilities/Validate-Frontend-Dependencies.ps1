# utilities/Validate-Frontend-Dependencies.ps1
# 폐쇄망 환경에서 Frontend 의존성 번들 유효성 검증

param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$BundlePath = "C:\deploys\packages\frontend\node_modules"
)

# UTF-8 인코딩 설정
chcp 65001 >$null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "Frontend 의존성 번들 검증 시작" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

function Test-NodeModulesBundle {
    param(
        [string]$FrontendProjectPath,
        [string]$NodeModulesBundlePath
    )

    try {
        # package-lock.json 경로 확인
        $packageLockPath = Join-Path $FrontendProjectPath "package-lock.json"

        if (-not (Test-Path $packageLockPath)) {
            Write-Host "❌ package-lock.json을 찾을 수 없습니다: $packageLockPath" -ForegroundColor Red
            return $false
        }

        # package-lock.json 해시 계산
        $packageLockHash = (Get-FileHash $packageLockPath -Algorithm SHA256).Hash.Substring(0, 8)
        Write-Host "📋 package-lock.json 해시: $packageLockHash"

        # 해시 기반 번들 파일 경로
        $expectedBundleFile = Join-Path $NodeModulesBundlePath "node_modules_$packageLockHash.zip"

        if (Test-Path $expectedBundleFile) {
            Write-Host "✅ 유효한 node_modules 번들 발견: $expectedBundleFile" -ForegroundColor Green

            # 번들 파일 크기 확인
            $bundleSize = (Get-Item $expectedBundleFile).Length
            $bundleSizeMB = [math]::Round($bundleSize / 1MB, 2)
            Write-Host "📦 번들 크기: $bundleSizeMB MB"

            # 번들 파일 생성 시간 확인
            $bundleCreated = (Get-Item $expectedBundleFile).CreationTime
            Write-Host "📅 번들 생성 시간: $bundleCreated"

            return $true
        } else {
            Write-Host "❌ node_modules 번들을 찾을 수 없습니다: $expectedBundleFile" -ForegroundColor Red

            # 사용 가능한 번들 목록 표시
            $availableBundles = Get-ChildItem -Path $NodeModulesBundlePath -Filter "node_modules_*.zip" -ErrorAction SilentlyContinue

            if ($availableBundles.Count -gt 0) {
                Write-Host "`n📂 사용 가능한 번들들:" -ForegroundColor Yellow
                foreach ($bundle in $availableBundles) {
                    $bundleHash = $bundle.Name -replace "node_modules_", "" -replace ".zip", ""
                    $bundleSize = [math]::Round($bundle.Length / 1MB, 2)
                    Write-Host "  - $bundleHash ($bundleSize MB, $($bundle.CreationTime))"
                }
                Write-Host "`n💡 Download-All-Dependencies.ps1을 실행하여 올바른 번들을 생성하세요." -ForegroundColor Cyan
            } else {
                Write-Host "`n📂 사용 가능한 번들이 없습니다." -ForegroundColor Red
                Write-Host "💡 Download-All-Dependencies.ps1을 실행하여 번들을 생성하세요." -ForegroundColor Cyan
            }

            return $false
        }

    } catch {
        Write-Host "❌ 검증 중 오류 발생: $_" -ForegroundColor Red
        return $false
    }
}

function Test-BundleIntegrity {
    param([string]$BundleFile)

    try {
        Write-Host "`n🔍 번들 무결성 검사 중..."

        # ZIP 파일 유효성 확인
        $tempPath = Join-Path ([System.IO.Path]::GetTempPath()) "bundle_test"
        if (Test-Path $tempPath) {
            Remove-Item $tempPath -Recurse -Force
        }
        New-Item -ItemType Directory -Path $tempPath | Out-Null

        # 압축 해제 테스트
        Expand-Archive -Path $BundleFile -DestinationPath $tempPath -Force

        # node_modules 구조 확인
        $nodeModulesPath = Join-Path $tempPath "node_modules"
        if (Test-Path $nodeModulesPath) {
            $packageCount = (Get-ChildItem $nodeModulesPath -Directory).Count
            Write-Host "✅ 번들 무결성 검사 통과 (패키지 수: $packageCount)" -ForegroundColor Green

            # bundle.info 파일 확인
            $bundleInfoPath = Join-Path $nodeModulesPath "bundle.info"
            if (Test-Path $bundleInfoPath) {
                $bundleInfo = Get-Content $bundleInfoPath | ConvertFrom-Json
                Write-Host "📋 번들 정보:"
                Write-Host "   - 생성 시간: $($bundleInfo.created)"
                Write-Host "   - Node 버전: $($bundleInfo.nodeVersion)"
                Write-Host "   - npm 버전: $($bundleInfo.npmVersion)"
                Write-Host "   - 패키지 수: $($bundleInfo.packageCount)"
            }
        } else {
            Write-Host "❌ 번들 구조가 올바르지 않습니다" -ForegroundColor Red
            return $false
        }

        # 임시 폴더 정리
        Remove-Item $tempPath -Recurse -Force
        return $true

    } catch {
        Write-Host "❌ 무결성 검사 중 오류 발생: $_" -ForegroundColor Red
        return $false
    }
}

# 메인 실행
try {
    $frontendPath = Join-Path $ProjectPath "webservice\frontend"

    Write-Host "🔍 검증 대상:"
    Write-Host "   - Frontend 프로젝트: $frontendPath"
    Write-Host "   - 번들 저장소: $BundlePath"
    Write-Host ""

    # 1. 번들 유효성 검증
    $bundleValid = Test-NodeModulesBundle -FrontendProjectPath $frontendPath -NodeModulesBundlePath $BundlePath

    if ($bundleValid) {
        # 2. 번들 무결성 검사
        $packageLockHash = (Get-FileHash "$frontendPath\package-lock.json" -Algorithm SHA256).Hash.Substring(0, 8)
        $bundleFile = Join-Path $BundlePath "node_modules_$packageLockHash.zip"

        $integrityValid = Test-BundleIntegrity -BundleFile $bundleFile

        if ($integrityValid) {
            Write-Host "`n=========================================" -ForegroundColor Green
            Write-Host "✅ Frontend 의존성 번들 검증 성공!" -ForegroundColor Green
            Write-Host "=========================================" -ForegroundColor Green
            Write-Host "폐쇄망 환경에서 정상적으로 사용 가능합니다."
            exit 0
        }
    }

    Write-Host "`n=========================================" -ForegroundColor Red
    Write-Host "❌ Frontend 의존성 번들 검증 실패" -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "폐쇄망 배포 전에 번들을 다시 생성해야 합니다."
    exit 1

} catch {
    Write-Host "`n❌ 검증 스크립트 실행 중 오류 발생: $_" -ForegroundColor Red
    exit 1
}