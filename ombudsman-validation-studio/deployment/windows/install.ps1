# Ombudsman Validation Studio - Windows Server Installation Script
# Run this script as Administrator

# Requires -RunAsAdministrator

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Ombudsman Validation Studio - Windows Installer" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Function to check if a command exists
function Test-CommandExists {
    param($command)
    $null = Get-Command $command -ErrorAction SilentlyContinue
    return $?
}

# Step 1: Install Chocolatey (package manager)
Write-Host "Step 1/7: Installing Chocolatey package manager..." -ForegroundColor Green
if (-not (Test-CommandExists choco)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

    # Refresh environment variables
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Host "Chocolatey installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Chocolatey is already installed." -ForegroundColor Yellow
}

# Step 2: Install Docker Desktop
Write-Host ""
Write-Host "Step 2/7: Installing Docker Desktop..." -ForegroundColor Green
if (-not (Test-CommandExists docker)) {
    choco install docker-desktop -y

    Write-Host "Docker Desktop installed successfully!" -ForegroundColor Green
    Write-Host "NOTE: Docker Desktop requires a restart. Please restart Windows and run this script again." -ForegroundColor Yellow
    Write-Host "After restart, Docker Desktop will start automatically." -ForegroundColor Yellow

    $restart = Read-Host "Do you want to restart now? (Y/N)"
    if ($restart -eq "Y" -or $restart -eq "y") {
        Restart-Computer -Force
    }
    exit 0
} else {
    Write-Host "Docker is already installed." -ForegroundColor Yellow

    # Check if Docker is running
    try {
        docker version | Out-Null
        Write-Host "Docker is running." -ForegroundColor Green
    } catch {
        Write-Host "Docker is installed but not running. Please start Docker Desktop manually." -ForegroundColor Yellow
        Write-Host "After Docker Desktop starts, run this script again." -ForegroundColor Yellow
        exit 1
    }
}

# Step 3: Install Git (optional but recommended)
Write-Host ""
Write-Host "Step 3/7: Installing Git..." -ForegroundColor Green
if (-not (Test-CommandExists git)) {
    choco install git -y
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "Git installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Git is already installed." -ForegroundColor Yellow
}

# Step 4: Create application directory
Write-Host ""
Write-Host "Step 4/7: Setting up application directory..." -ForegroundColor Green
$appDir = "C:\OmbudsmanStudio"
if (-not (Test-Path $appDir)) {
    New-Item -Path $appDir -ItemType Directory | Out-Null
    Write-Host "Created directory: $appDir" -ForegroundColor Green
} else {
    Write-Host "Directory already exists: $appDir" -ForegroundColor Yellow
}

# Step 5: Copy application files
Write-Host ""
Write-Host "Step 5/7: Copying application files..." -ForegroundColor Green

$sourcePaths = @(
    "$env:USERPROFILE\ombudsman-validation-studio",
    "$PSScriptRoot\..\..",
    ".\ombudsman-validation-studio"
)

$copied = $false
foreach ($sourcePath in $sourcePaths) {
    if (Test-Path $sourcePath) {
        Write-Host "Copying from: $sourcePath" -ForegroundColor Cyan
        Copy-Item -Path "$sourcePath\*" -Destination $appDir -Recurse -Force
        $copied = $true
        break
    }
}

if (-not $copied) {
    Write-Host "WARNING: Application files not found. Please copy them manually to $appDir" -ForegroundColor Yellow
    Write-Host "Required files: docker-compose.yml, backend/, frontend/, ombudsman_core/" -ForegroundColor Yellow
}

# Step 6: Create .env file
Write-Host ""
Write-Host "Step 6/7: Creating .env configuration file..." -ForegroundColor Green
$envFile = "$appDir\.env"
if (-not (Test-Path $envFile)) {
    $envContent = @"
# Ombudsman Validation Studio Configuration

# SQL Server Configuration
SQL_SERVER_HOST=your-sqlserver-host
SQL_SERVER_PORT=1433
SQL_SERVER_USER=sa
SQL_SERVER_PASSWORD=YourStrong!Passw0rd
SQL_SERVER_DATABASE=SampleDW

# Snowflake Configuration (Optional)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USER=your-user
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_DATABASE=SAMPLEDW
SNOWFLAKE_SCHEMA=PUBLIC

# Application Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Database for OVS Studio (Authentication, Projects, etc.)
OVS_DB_HOST=your-sqlserver-host
OVS_DB_PORT=1433
OVS_DB_NAME=ovs_studio
OVS_DB_USER=sa
OVS_DB_PASSWORD=YourStrong!Passw0rd

# JWT Secret (Change this to a random string)
JWT_SECRET_KEY=change-this-to-a-random-secret-key-at-least-32-characters-long
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
"@
    Set-Content -Path $envFile -Value $envContent
    Write-Host "Created .env file at: $envFile" -ForegroundColor Green
    Write-Host "IMPORTANT: Please edit .env with your actual database credentials!" -ForegroundColor Yellow
} else {
    Write-Host ".env file already exists, skipping..." -ForegroundColor Yellow
}

# Step 7: Create Windows Task Scheduler for auto-start
Write-Host ""
Write-Host "Step 7/7: Creating Windows Task for auto-start..." -ForegroundColor Green

$taskName = "OmbudsmanValidationStudio"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($null -eq $taskExists) {
    $action = New-ScheduledTaskAction -Execute "docker" -Argument "compose up -d" -WorkingDirectory $appDir
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

    Write-Host "Created scheduled task: $taskName" -ForegroundColor Green
} else {
    Write-Host "Scheduled task already exists: $taskName" -ForegroundColor Yellow
}

# Get local IP address
$ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254.*"} | Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Edit configuration: notepad $envFile" -ForegroundColor White
Write-Host "2. Update database credentials in .env file" -ForegroundColor White
Write-Host "3. Start the application:" -ForegroundColor White
Write-Host "   cd $appDir" -ForegroundColor Cyan
Write-Host "   docker compose up -d" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access the application:" -ForegroundColor Yellow
Write-Host "   Frontend: http://${ipAddress}:3000" -ForegroundColor Cyan
Write-Host "   Backend API: http://${ipAddress}:8000" -ForegroundColor Cyan
Write-Host "   API Docs: http://${ipAddress}:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "View logs:" -ForegroundColor Yellow
Write-Host "   docker compose logs -f" -ForegroundColor Cyan
Write-Host ""
Write-Host "Stop the application:" -ForegroundColor Yellow
Write-Host "   docker compose down" -ForegroundColor Cyan
Write-Host ""
Write-Host "The application will automatically start when Windows boots." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
