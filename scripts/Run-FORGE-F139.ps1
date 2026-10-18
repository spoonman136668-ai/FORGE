# F139 single workstation controller, invoked by one Windows scheduled task.
# No credentials embedded in source, no science first-use, no cloud host.
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$PythonExe,
  [Parameter(Mandatory)][string]$RepositoryRoot,
  [Parameter(Mandatory)][string]$Database,
  [Parameter(Mandatory)][string]$EncryptedKeyFile,
  [int]$PollSeconds = 45
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
  # Windows PowerShell 5.1 wraps a native process's stderr as a non-terminating
  # NativeCommandError. In strict Stop mode a deliberately disabled controller
  # would kill this launcher before the expected safety marker was logged.
  # Relax ONLY native stderr promotion, not logging or child exit checks.
  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & $PythonExe -B -m f139.local_controller --db $Database loop --seconds $PollSeconds 2>&1 |
      ForEach-Object -ErrorAction Stop { "$(Get-Date -Format o) $_" } |
      Out-File -LiteralPath $log -Append -Encoding utf8 -ErrorAction Stop
    $pythonExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  if ($pythonExit -ne 0) { throw 'F139_CONTROLLER_EXITED' }
} finally {
  Remove-Item Env:F139_WORKER_HMAC_KEY -ErrorAction SilentlyContinue
  Set-Location -LiteralPath $oldDir
}
