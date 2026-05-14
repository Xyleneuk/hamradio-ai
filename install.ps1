# Ham Radio AI - Windows Installation Script (PowerShell)

Write-Host ""
Write-Host "========================================"
Write-Host "Ham Radio AI - Installation Script"
Write-Host "========================================"
Write-Host ""

# Check Python
Write-Host "Checking Python installation..."
$pythonCheck = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Python found: $pythonCheck"
} else {
    Write-Host "[ERROR] Python not found!"
    Write-Host "Please install Python 3.11+ from https://www.python.org/"
    Write-Host "Make sure to check 'Add Python to PATH'"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Git
Write-Host "Checking Git installation..."
$gitCheck = git --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Git found: $gitCheck"
} else {
    Write-Host "[ERROR] Git not found!"
    Write-Host "Please install Git from https://git-scm.com/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Hamlib
Write-Host "Checking Hamlib installation..."
$hamlibFound = $false

# Check if rigctld is in PATH
$hamlibCheck = where.exe rigctld 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Hamlib found in PATH: $hamlibCheck"
    $hamlibFound = $true
}

# Check default installation locations
if (-not $hamlibFound) {
    $defaultLocations = @(
        "C:\Program Files\hamlib-w64-4.7.1\bin\rigctld.exe",
        "C:\Program Files\hamlib\bin\rigctld.exe",
        "C:\Program Files (x86)\hamlib\bin\rigctld.exe"
    )

    foreach ($location in $defaultLocations) {
        if (Test-Path $location) {
            Write-Host "[OK] Hamlib found at: $location"
            $hamlibPath = Split-Path -Parent (Split-Path -Parent $location)
            $binPath = Join-Path $hamlibPath "bin"
            Write-Host "Adding to PATH: $binPath"

            # Add to PATH for current session
            $env:PATH = "$env:PATH;$binPath"

            # Add to PATH permanently (requires admin)
            try {
                [Environment]::SetEnvironmentVariable("PATH", "$env:PATH;$binPath", "User")
            } catch {
                Write-Host "[NOTE] Could not update permanent PATH (not admin), but added to current session"
            }

            $hamlibFound = $true
            break
        }
    }
}

if (-not $hamlibFound) {
    Write-Host "[WARNING] Hamlib not found!"
    Write-Host ""
    Write-Host "Please install Hamlib:"
    Write-Host "1. Download from: https://hamlib.sourceforge.io/"
    Write-Host "2. Run hamlib-w64-4.7.1.exe installer"
    Write-Host "3. Use default installation path"
    Write-Host "4. Restart PowerShell after installation"
    Write-Host ""
} else {
    Write-Host "[OK] Hamlib is ready"
}
Write-Host ""

# Upgrade pip and install build tools
Write-Host ""
Write-Host "Installing/upgrading pip, wheel, setuptools..."
python -m pip install --upgrade pip wheel setuptools

# Install requirements
Write-Host ""
Write-Host "Installing Python dependencies..."
Write-Host "This may take a few minutes..."
Write-Host ""

python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Installation failed!"
    Write-Host ""
    Write-Host "If PyAudio failed, try:"
    Write-Host "1. Install Visual Studio C++ Build Tools from:"
    Write-Host "   https://visualstudio.microsoft.com/visual-cpp-build-tools/"
    Write-Host "2. Then run this script again"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host "Installation Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "To run the app:"
Write-Host "  python main.py"
Write-Host ""
Read-Host "Press Enter to close"
