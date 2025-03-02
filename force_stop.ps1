# Force stop script for home temperature control application (Windows version)

Write-Host "=== Home Temperature Control System Force Stop ===" -ForegroundColor Blue

# Look for python processes running our scripts
$appScripts = @("home_topology_api.py", "home_temperature_control.py")
$found = $false

foreach ($script in $appScripts) {
    Write-Host "Searching for processes running $script..." -ForegroundColor Yellow
    $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*$script*" }
    
    if ($processes) {
        foreach ($process in $processes) {
            $found = $true
            Write-Host "Found process: $($process.Id) running $script" -ForegroundColor Green
            
            # Try to stop the process gracefully
            Write-Host "Attempting to stop process $($process.Id)..." -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            
            # Check if process was stopped
            Start-Sleep -Seconds 2
            $stillRunning = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
            
            if ($stillRunning) {
                Write-Host "Failed to kill process $($process.Id). Please close it manually." -ForegroundColor Red
            } else {
                Write-Host "Process $($process.Id) successfully terminated." -ForegroundColor Green
            }
        }
    }
}

# Also look for processes on port 8000
Write-Host "`nChecking for processes on default port 8000..." -ForegroundColor Yellow
$portProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }

if ($portProcesses) {
    foreach ($conn in $portProcesses) {
        $found = $true
        $processId = $conn.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        
        if ($process) {
            Write-Host "Found process: $processId ($($process.ProcessName)) using port 8000" -ForegroundColor Green
            Write-Host "Attempting to stop process $processId..." -ForegroundColor Yellow
            
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            
            # Check if process was stopped
            Start-Sleep -Seconds 2
            $stillRunning = Get-Process -Id $processId -ErrorAction SilentlyContinue
            
            if ($stillRunning) {
                Write-Host "Failed to kill process $processId. Please close it manually." -ForegroundColor Red
            } else {
                Write-Host "Process $processId successfully terminated." -ForegroundColor Green
            }
        }
    }
}

if (-not $found) {
    Write-Host "No running application processes found." -ForegroundColor Yellow
    Write-Host "If the application is still running, try:"
    Write-Host "  1. Find the process ID: Get-Process python | Select-Object Id, CommandLine"
    Write-Host "  2. Kill it manually: Stop-Process -Id <PID> -Force"
} else {
    Write-Host "`nForce stop completed." -ForegroundColor Green
}
