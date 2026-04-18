$root = Split-Path -Parent $PSScriptRoot

$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
	$pythonCmd = "`"$venvPython`""
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
	$pythonCmd = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
	$pythonCmd = "python"
} else {
	throw "Python was not found. Create .venv or install Python 3."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
	throw "npm was not found. Install Node.js to run the frontend."
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; $pythonCmd scripts/run_backend.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\\frontend'; npm run dev"
