# PowerShell script to add all modified temperature control system files to git

Write-Host "=== Home Temperature Control System - Git Add Files ===" -ForegroundColor Blue

# Get the directory where the script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Files to add
$files = @(
  "security_utils.py",
  "config_loader.py",
  "temperature_control.py",
  "home_topology_api.py",
  "home_temperature_control.py",
  "house_topology.yaml",
  "config.yaml",
  "run_test_environment.py",
  "stop_app.py",
  "kill_app.py",
  "force_stop.sh",
  "force_stop.ps1"
)

# Check if we are in a git repository
$inGitRepo = $null
try {
    $inGitRepo = git rev-parse --is-inside-work-tree 2>$null
} catch {
    $inGitRepo = $null
}

if (-not $inGitRepo) {
  Write-Host "Not a git repository. Initializing git..." -ForegroundColor Yellow
  git init
  "# Home Temperature Control System" | Out-File -FilePath README.md -Encoding utf8
  git add README.md
  git commit -m "Initial commit"
}

# Add each file, checking for existence
foreach ($file in $files) {
  if (Test-Path $file) {
    Write-Host "Adding file: $file" -ForegroundColor Green
    git add $file
  } else {
    Write-Host "Warning: File not found: $file" -ForegroundColor Yellow
  }
}

# Also add any new files that might have been created
Write-Host "`nChecking for other new/modified files..." -ForegroundColor Blue
git add -A

# Show status
Write-Host "`nCurrent git status:" -ForegroundColor Blue
git status

# Ask about committing
$commit = Read-Host "`nDo you want to commit these changes? (y/n)"
if ($commit -like 'y*') {
  $commitMsg = Read-Host "Enter commit message (or press Enter for default message)"
  
  if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "Update home temperature control system files"
  }
  
  git commit -m $commitMsg
  
  # Ask about pushing
  $push = Read-Host "`nDo you want to push these changes? (y/n)"
  if ($push -like 'y*') {
    $branchName = Read-Host "Enter branch name (or press Enter for 'main')"
    
    if ([string]::IsNullOrWhiteSpace($branchName)) {
      $branchName = "main"
    }
    
    git push -u origin $branchName
  }
}

Write-Host "`nGit operation completed!" -ForegroundColor Green
