# ============================================================================
# FraudShield 360 — Deploy Script (PowerShell)
# Uploads skills and Streamlit apps to Snowflake stage, then creates objects.
#
# Prerequisites:
#   - SnowSQL CLI installed and configured (or run PUT commands in a worksheet)
#   - ACCOUNTADMIN role
#
# Usage:
#   1. Run sql/01_complete_setup.sql in Snowflake first
#   2. Then run this script: .\deploy.ps1
#   3. Then run sql/02_deploy_agent_apps.sql in Snowflake
# ============================================================================

$STAGE = "@FRAUDSHIELD_360_DB.AGENTS.SKILL_STAGE"

Write-Host "=== FraudShield 360 — Deploying to Snowflake ===" -ForegroundColor Cyan

# Skills
$skills = @("detect_fraud_signals", "query_regulatory_docs", "generate_audit_finding", "dispatch_verification_alert", "fraudshield_orchestrator")

foreach ($skill in $skills) {
    Write-Host "Uploading skill: $skill" -ForegroundColor Yellow
    $files = Get-ChildItem "skills/$skill" -File
    foreach ($f in $files) {
        $path = $f.FullName -replace '\\', '/'
        $cmd = "PUT 'file://$path' $STAGE/skills/$skill/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
        Write-Host "  -> $($f.Name)"
        # Run via SnowSQL:
        # snowsql -q $cmd
        Write-Host "  SQL: $cmd" -ForegroundColor DarkGray
    }
}

# Streamlit Apps
Write-Host "`nUploading Streamlit: Command Center" -ForegroundColor Yellow
$ccPath = (Resolve-Path "apps/command_center/fraudshield_command_center.py").Path -replace '\\', '/'
Write-Host "  SQL: PUT 'file://$ccPath' $STAGE/streamlit_command_center/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;" -ForegroundColor DarkGray

Write-Host "Uploading Streamlit: Customer Simulator" -ForegroundColor Yellow
$csPath = (Resolve-Path "apps/customer_simulator/fraudshield_customer_simulator.py").Path -replace '\\', '/'
Write-Host "  SQL: PUT 'file://$csPath' $STAGE/streamlit/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;" -ForegroundColor DarkGray

Write-Host "`n=== Upload commands generated ===" -ForegroundColor Cyan
Write-Host "Run the PUT commands above in a Snowflake worksheet or via SnowSQL." -ForegroundColor White
Write-Host "Then run sql/02_deploy_agent_apps.sql to create the agent and Streamlit objects." -ForegroundColor White
