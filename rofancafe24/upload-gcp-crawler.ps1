# GCP_CRAWLER.py를 GCP 서버로 업로드하는 PowerShell 스크립트

$localFile = "$PSScriptRoot\tracker\GCP_CRAWLER.py"
$remoteHost = "45.120.69.179"
$remoteUser = "root"
$remotePath = "/root/mailcenter/sound/GCP_CRAWLER.py"
$password = "dptmxldps12@@"

Write-Host "Uploading GCP_CRAWLER.py to $remoteHost..." -ForegroundColor Green

# WinSCP를 사용한 업로드 (WinSCP가 설치되어 있는 경우)
# 또는 Posh-SSH 모듈 사용

# 방법 1: Posh-SSH 모듈 사용 (설치 필요: Install-Module -Name Posh-SSH)
try {
    Import-Module Posh-SSH -ErrorAction Stop
    
    $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($remoteUser, $securePassword)
    
    $session = New-SFTPSession -ComputerName $remoteHost -Credential $credential -AcceptKey
    
    if ($session) {
        Set-SFTPFile -SessionId $session.SessionId -LocalFile $localFile -RemotePath $remotePath
        Remove-SFTPSession -SessionId $session.SessionId
        Write-Host "✓ Upload successful!" -ForegroundColor Green
    } else {
        Write-Host "✗ Failed to connect" -ForegroundColor Red
    }
} catch {
    Write-Host "Posh-SSH module not found. Installing..." -ForegroundColor Yellow
    Write-Host "Please run: Install-Module -Name Posh-SSH -Scope CurrentUser" -ForegroundColor Yellow
    Write-Host "Or use WinSCP command line:" -ForegroundColor Yellow
    Write-Host "winscp.exe /command `"open sftp://root:dptmxldps12@@@45.120.69.179`" `"put $localFile $remotePath`" `"exit`""
}

