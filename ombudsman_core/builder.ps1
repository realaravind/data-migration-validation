param(
    [string]$Target = "build",
    [string]$Schema = ""
)

Write-Host ""
Write-Host "============================================================"
Write-Host " Ombudsman Migration Testing Framework - Windows Builder"
Write-Host "============================================================"
Write-Host ""

# ------------------------------------------------------------
# Helper: Run a shell script safely
# ------------------------------------------------------------
function Run-Script {
    param([string]$File)

    if (Test-Path $File) {
        Write-Host "Running $File ..."
        bash $File
    }
    else {
        Write-Host "❌ ERROR: Missing script: $File"
        exit 1
    }
}

# ------------------------------------------------------------
# Auto-Detect Metadata Source
# ------------------------------------------------------------
function Detect-Source {
    Write-Host "Auto-detecting metadata source ..."
    
    if ($env:SQLSERVER_CONN_STR) {
        return @{
            Mode = "sqlserver"
            Args = "--sqlserver --conn-str='$($env:SQLSERVER_CONN_STR)'"
        }
    }

    if ($env:SNOWFLAKE_USER) {
        return @{
            Mode = "snowflake"
            Args = "--snowflake --user='$($env:SNOWFLAKE_USER)' --password='$($env:SNOWFLAKE_PASSWORD)' --account='$($env:SNOWFLAKE_ACCOUNT)' --database='$($env:SNOWFLAKE_DATABASE)' --schema='$($env:SNOWFLAKE_SCHEMA)'"
        }
    }

    return @{
        Mode = ""
        Args = ""
    }
}

# ------------------------------------------------------------
# Manual CLI override
# ------------------------------------------------------------
function Manual-Override {
    param([string]$mode)

    switch ($mode) {
        "sqlserver" {
            if (-not $env:SQLSERVER_CONN_STR) {
                Write-Host "❌ SQLSERVER_CONN_STR environment variable missing."
                exit 1
            }
            return "--sqlserver --conn-str='$($env:SQLSERVER_CONN_STR)'"
        }
        "snowflake" {
            foreach ($v in "SNOWFLAKE_USER","SNOWFLAKE_PASSWORD","SNOWFLAKE_ACCOUNT","SNOWFLAKE_DATABASE") {
                if (-not $env:$v) {
                    Write-Host "❌ Missing required env var: $v"
                    exit 1
                }
            }
            return "--snowflake --user='$($env:SNOWFLAKE_USER)' --password='$($env:SNOWFLAKE_PASSWORD)' --account='$($env:SNOWFLAKE_ACCOUNT)' --database='$($env:SNOWFLAKE_DATABASE)' --schema='$($env:SNOWFLAKE_SCHEMA)'"
        }
        default { return "" }
    }
}

# ------------------------------------------------------------
# Select metadata source
# ------------------------------------------------------------
function Resolve-Build-Source {
    param([string]$UserMode)

    if ($UserMode -ne "") {
        $args = Manual-Override $UserMode
        return @{
            Mode = $UserMode
            Args = $args
        }
    }

    # Try auto-detect
    $detected = Detect-Source
    if ($detected.Mode -ne "") {
        return $detected
    }

    Write-Host "❌ ERROR: No metadata source detected or provided."
    Write-Host ""
    Write-Host "Provide one of the following environment variables:"
    Write-Host "  SQLSERVER_CONN_STR"
    Write-Host "  OR"
    Write-Host "  SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, SNOWFLAKE_ACCOUNT, SNOWFLAKE_DATABASE"
    exit 1
}

# ------------------------------------------------------------
# Main Task Logic
# ------------------------------------------------------------
switch ($Target) {

    "build" {
        Write-Host "== BUILDING (Parts 1 → 6) =="
        Run-Script "build_part1.sh"
        Run-Script "build_part2.sh"
        Run-Script "build_part3.sh"
        Run-Script "build_part4.sh"
        Run-Script "build_part5.sh"

        # Resolve metadata source
        $resolved = Resolve-Build-Source ""
        Write-Host "Using metadata source:" $resolved.Mode

        $command = "build_part6.sh $($resolved.Args)"
        Write-Host "Executing Part 6: bash $command"
        bash $command
        break
    }

    "sqlserver" {
        Write-Host "== MANUAL SQL SERVER EXECUTION =="
        $resolved = Resolve-Build-Source "sqlserver"
        bash "build_part6.sh $($resolved.Args)"
        break
    }

    "snowflake" {
        Write-Host "== MANUAL SNOWFLAKE EXECUTION =="
        $resolved = Resolve-Build-Source "snowflake"
        bash "build_part6.sh $($resolved.Args)"
        break
    }

    "validate" {
        Write-Host "== VALIDATION =="
        bash validate_project.sh
        break
    }

    "test" {
        Write-Host "== RUNNING ALL CONNECTION TESTS =="
        python ombudsman/scripts/test_sqlserver.py
        python ombudsman/scripts/test_snowflake.py
        break
    }

    "zip" {
        Write-Host "== BUILDING ZIP PACKAGE =="
        bash ombudsman/finalize_project.sh
        break
    }

    "clean" {
        Write-Host "== CLEANING OUTPUT DIRECTORY =="
        Remove-Item -Force -Recurse ombudsman/output/* -ErrorAction SilentlyContinue
        break
    }

    default {
        Write-Host "Unknown target: $Target"
        Write-Host ""
        Write-Host "Usage:"
        Write-Host "  pwsh builder.ps1 build"
        Write-Host "  pwsh builder.ps1 sqlserver"
        Write-Host "  pwsh builder.ps1 snowflake"
        Write-Host "  pwsh builder.ps1 validate"
        Write-Host "  pwsh builder.ps1 test"
        Write-Host "  pwsh builder.ps1 zip"
    }
}