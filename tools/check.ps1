$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Push-Location $repoRoot
try {
    & $python -m coverage erase
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m coverage run --source=app,core,web -m pytest tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m coverage report --show-missing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m ruff check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
