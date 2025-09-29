# TestscenarioMaker URL Protocol Handler (Production)
param(
    [string]$url,
    [string]$exePath
)

# UTF-8 인코딩 설정
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 작업 디렉토리 설정
Set-Location "C:\deploys\apps\cli"

try {
    # CLI를 직접 실행 (PowerShell 중첩 없이 바로 실행하여 & 파싱 문제 해결)
    Start-Process -FilePath $exePath -ArgumentList "`"$url`"" -WindowStyle Normal
} catch {
    # 오류 발생 시 로그 파일에 기록
    $errorLog = "$env:TEMP\testscenariomaker_error.log"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - Error: $($_.Exception.Message)" | Out-File -FilePath $errorLog -Append -Encoding UTF8
}