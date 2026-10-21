# F139 single workstation controller, invoked by one Windows scheduled task.
# No credentials embedded in source, no science first-use, no cloud host.
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$PythonExe,
  [Parameter(Mandatory)][string]$RepositoryRoot,
  [Parameter(Mandatory)][string]$Database,
  [Parameter(Mandatory)][string]$EncryptedKeyFile,
  [int]$PollSeconds = 45,
  [switch]$CustodyOriginalNativeNegative
)
$ErrorActionPreference = 'Stop'
if ($PollSeconds -lt 15 -or $PollSeconds -gt 300) { throw 'F139_BAD_POLL_INTERVAL' }
if (!(Test-Path -LiteralPath $PythonExe -PathType Leaf)) { throw 'F139_PYTHON_MISSING' }
if (!(Test-Path -LiteralPath (Join-Path $RepositoryRoot 'f139/local_controller.py') -PathType Leaf)) { throw 'F139_SOURCE_MISSING' }
if (!(Test-Path -LiteralPath $EncryptedKeyFile -PathType Leaf)) { throw 'F139_DPAPI_KEY_MISSING' }
$logRoot = Join-Path ([IO.Path]::GetDirectoryName($Database)) 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$log = Join-Path $logRoot 'controller.log'
$oldDir = (Get-Location).Path
try {
  $secure = Import-Clixml -LiteralPath $EncryptedKeyFile
  if (!($secure -is [Security.SecureString])) { throw 'F139_SECRET_NOT_DPAPI_SECURESTRING' }
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try { $env:F139_WORKER_HMAC_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
  if ($env:F139_WORKER_HMAC_KEY.Length -lt 32) { throw 'F139_SECRET_TOO_SHORT' }
  Set-Location -LiteralPath $RepositoryRoot
  if ($CustodyOriginalNativeNegative) {
    # One-time owner cutover under the existing SID/task/DPAPI custody.
    # This does NOT start a second controller, execute the normal loop,
    # authorize scientific work, dispatch, or print raw HMAC material.
    & $PythonExe -B -m f139.local_controller --db $Database custody-original-native-negative
    if ($LASTEXITCODE -ne 0) { throw 'F139_ORIGINAL_NEGATIVE_CUSTODY_FAILED' }
    Write-Host 'F139_ORIGINAL_NATIVE_NEGATIVE_CUSTODY=QUALIFIED_ONCE'
    return
  }
  # Native Windows job control ensures Python is terminated if Task Scheduler
  # terminates this PowerShell host. Suspend -> assign -> resume closes the
  # orphan creation race, with CREATE_NO_WINDOW for its Python process.
  $jobSource = Join-Path $PSScriptRoot 'F139WindowsJobSupervisor.cs'
  if (!(Test-Path -LiteralPath $jobSource -PathType Leaf)) { throw 'F139_WINDOWS_JOB_SOURCE_MISSING' }
  Add-Type -Path $jobSource -ErrorAction Stop
  Add-Content -LiteralPath $log -Value ("$(Get-Date -Format o) F139_PROCESS_LIFETIME=KILL_ON_JOB_CLOSE") -Encoding UTF8
  try {
    $pythonExit = [F139WindowsJobSupervisor]::Run(
      $PythonExe, $RepositoryRoot, $Database, $PollSeconds, $log
    )
  } catch {
    $failure = $_.Exception
    # Diagnostic metadata only; never print the inherited HMAC secret.
    $errorType = $failure.GetType().FullName
    $message = $failure.Message
    if ($env:F139_WORKER_HMAC_KEY) {
      $message = $message.Replace($env:F139_WORKER_HMAC_KEY, '[REDACTED]')
    }
    Add-Content -LiteralPath $log -Value ("$(Get-Date -Format o) F139_JOB_SUPERVISOR_BLOCKED=$errorType $message") -Encoding UTF8
    throw
  }
  if ($pythonExit -ne 0) { throw 'F139_CONTROLLER_EXITED' }
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
  Set-Location -LiteralPath $oldDir
}
