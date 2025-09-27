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
    # CLI를 콘솔 창에서 실행 (URL을 따옴표로 감싸서 전달)
    Start-Process -FilePath $exePath -ArgumentList "`"$url`"" -WorkingDirectory "C:\deploys\apps\cli"
} catch {
    # 오류 발생 시 로그 파일에 기록
    $errorLog = "$env:TEMP\testscenariomaker_error.log"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - Error: $($_.Exception.Message)" | Out-File -FilePath $errorLog -Append -Encoding UTF8
}