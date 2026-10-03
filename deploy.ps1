# ============================================================================
# FraudShield 360 — Deploy Script (PowerShell)
# Uploads skills and Streamlit apps to Snowflake stage via SnowSQL,
# then refreshes the stage directory.
#
# Prerequisites:
#   - SnowSQL CLI installed and on PATH, OR run the printed PUT commands
#     manually in a Snowflake worksheet
#   - ACCOUNTADMIN role
#
# Usage:
#   1. Run sql/01_complete_setup.sql in Snowflake first
#   2. Then run this script:  .\deploy.ps1 [-Connection <name>]
#   3. Then run sql/02_deploy_agent_apps.sql in Snowflake
#   4. Then run sql/03_seed_demo_data.sql for demo data
# ============================================================================

param(
    [string]$Connection = ""
)

$STAGE = "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE"
$PROJECT_ROOT = $PSScriptRoot
if (-not $PROJECT_ROOT) { $PROJECT_ROOT = Get-Location }

# Check if SnowSQL is available
$hasSnowSQL = $null -ne (Get-Command snowsql -ErrorAction SilentlyContinue)

function Run-SnowSQL {
    param([string]$Query)
    if ($hasSnowSQL) {
        $args = @("-q", $Query, "--option", "auto_compress=false")
        if ($Connection) { $args += @("-c", $Connection) }
        snowsql @args 2>&1
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  FraudShield 360 — Deploy to Snowflake"     -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not $hasSnowSQL) {
    Write-Host "[WARN] SnowSQL not found on PATH." -ForegroundColor Yellow
    Write-Host "       PUT commands will be printed for manual execution." -ForegroundColor Yellow
    Write-Host "       Install SnowSQL or paste the commands into a Snowflake worksheet." -ForegroundColor Yellow
    Write-Host ""
}

$putCommands = @()

# --- Skills ---
$skills = @("detect_fraud_signals", "query_regulatory_docs", "generate_audit_finding",
            "dispatch_verification_alert", "fraudshield_orchestrator")

Write-Host "--- Uploading Skills ---" -ForegroundColor Yellow
foreach ($skill in $skills) {
    $skillDir = Join-Path $PROJECT_ROOT "skills" $skill
    if (-not (Test-Path $skillDir)) {
        Write-Host "  [SKIP] $skill — folder not found at $skillDir" -ForegroundColor Red
        continue
    }
    $files = Get-ChildItem $skillDir -File
    foreach ($f in $files) {
        $path = $f.FullName -replace '\\', '/'
        $cmd = "PUT 'file://$path' $STAGE/skills/$skill/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
        $putCommands += $cmd

        if ($hasSnowSQL) {
            Write-Host "  PUT $($skill)/$($f.Name) ... " -NoNewline
            $result = Run-SnowSQL -Query $cmd
            if ($LASTEXITCODE -eq 0) {
                Write-Host "OK" -ForegroundColor Green
            } else {
                Write-Host "FAILED" -ForegroundColor Red
                Write-Host "    $result" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "  $($skill)/$($f.Name)" -ForegroundColor DarkGray
        }
    }
}

# --- Streamlit Apps ---
Write-Host ""
Write-Host "--- Uploading Streamlit Apps ---" -ForegroundColor Yellow

$ccFile = Join-Path $PROJECT_ROOT "apps" "command_center" "fraudshield_command_center.py"
$csFile = Join-Path $PROJECT_ROOT "apps" "customer_simulator" "fraudshield_customer_simulator.py"

$appFiles = @(
    @{ Path = $ccFile; Stage = "$STAGE/streamlit_command_center/"; Label = "Command Center" },
    @{ Path = $csFile; Stage = "$STAGE/streamlit/";               Label = "Customer Simulator" }
)

foreach ($app in $appFiles) {
    if (-not (Test-Path $app.Path)) {
        Write-Host "  [SKIP] $($app.Label) — file not found" -ForegroundColor Red
        continue
    }
    $path = ($app.Path) -replace '\\', '/'
    $cmd = "PUT 'file://$path' $($app.Stage) AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
    $putCommands += $cmd

    if ($hasSnowSQL) {
        Write-Host "  PUT $($app.Label) ... " -NoNewline
        $result = Run-SnowSQL -Query $cmd
        if ($LASTEXITCODE -eq 0) {
            Write-Host "OK" -ForegroundColor Green
        } else {
            Write-Host "FAILED" -ForegroundColor Red
        }
    } else {
        Write-Host "  $($app.Label)" -ForegroundColor DarkGray
    }
}

# --- Refresh Stage Directory ---
Write-Host ""
Write-Host "--- Refreshing Stage Directory ---" -ForegroundColor Yellow
$refreshCmd = "ALTER STAGE FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE REFRESH;"
if ($hasSnowSQL) {
    Run-SnowSQL -Query $refreshCmd
    Write-Host "  Stage refreshed." -ForegroundColor Green
} else {
    $putCommands += $refreshCmd
}

# --- Summary ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

if ($hasSnowSQL) {
    Write-Host "  Upload complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor White
    Write-Host "    1. Run sql/02_deploy_agent_apps.sql in a worksheet" -ForegroundColor White
    Write-Host "    2. Run sql/03_seed_demo_data.sql for demo data" -ForegroundColor White
} else {
    Write-Host "  Run these commands in a Snowflake worksheet:" -ForegroundColor White
    Write-Host ""
    foreach ($cmd in $putCommands) {
        Write-Host "  $cmd" -ForegroundColor DarkGray
    }
    Write-Host ""
    Write-Host "  Then run:" -ForegroundColor White
    Write-Host "    sql/02_deploy_agent_apps.sql" -ForegroundColor White
    Write-Host "    sql/03_seed_demo_data.sql" -ForegroundColor White
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
