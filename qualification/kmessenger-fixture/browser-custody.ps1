param([ValidateSet('probe','count','cleanup')][string]$Mode,[int]$Port=0)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($env:RUNNER_TEMP)
$target=[IO.Path]::GetFullPath($env:KM_SCRATCH)
if([IO.Path]::GetDirectoryName($target) -cne $root -or [IO.Path]::GetFileName($target) -cne ('kmessenger-browser-'+$env:GITHUB_RUN_ID)){throw 'KM_CUSTODY_SCOPE'}
$profile=Join-Path $target 'edge-profile'
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$edge=$null
foreach($dir in @($env:ProgramFiles,[Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))){
  if($dir){$candidate=Join-Path $dir 'Microsoft/Edge/Application/msedge.exe';if(Test-Path -LiteralPath $candidate){$edge=[IO.Path]::GetFullPath($candidate);break}}
}
if(!$edge -or (Get-FileHash -LiteralPath $edge -Algorithm SHA256).Hash.ToLowerInvariant() -cne '7b8f341751a1b3ccf73858cf5a5813616976b849748ea3ac6fc796cd93516c0f'){throw 'KM_EDGE_EXECUTABLE_DRIFT'}
$pattern='(?i)(?:^|\s)(?:"--user-data-dir='+[regex]::Escape($profile)+'"|--user-data-dir="'+[regex]::Escape($profile)+'"|--user-data-dir='+[regex]::Escape($profile)+')(?=\s|$)'
function OwnedFixture {
  @(Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine -match $pattern})
}

function VerifyFixtureProcess($p){
 $owner=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid
 if($owner.ReturnValue -ne 0 -or $owner.Sid -cne $sid -or !$p.ExecutablePath -or ![string]::Equals([IO.Path]::GetFullPath($p.ExecutablePath),$edge,[StringComparison]::OrdinalIgnoreCase)){throw 'KM_RESIDUAL_OWNER_UNVERIFIED'}
 $current=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.ProcessId)
 if(!$current -or $current.CreationDate -ne $p.CreationDate -or $current.CommandLine -cne $p.CommandLine -or $current.ExecutablePath -cne $p.ExecutablePath){throw 'KM_RESIDUAL_PROCESS_DRIFT'}
}
if($Mode -eq 'count'){Write-Output @(OwnedFixture).Count;exit 0}
if($Mode -eq 'probe'){
 if($Port -lt 1025 -or $Port -gt 65535){throw 'KM_DEBUG_PORT_SCOPE'}
 $s=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop)
 if(!$s.Count -or @($s|Where-Object {$_.LocalAddress -cnotin @('127.0.0.1','::1')}).Count){throw 'KM_DEBUG_LISTENER_SCOPE'}
 $ids=@($s.OwningProcess|Sort-Object -Unique)
 if($ids.Count -ne 1){throw 'KM_DEBUG_LISTENER_AMBIGUOUS'}
 $owned=@(OwnedFixture|Where-Object {$_.ProcessId -eq $ids[0]})
 if($owned.Count -ne 1){throw 'KM_DEBUG_OWNER_UNVERIFIED'}
 VerifyFixtureProcess $owned[0]
 if(@(Get-NetTCPConnection -OwningProcess $ids[0] -State Listen -ErrorAction Stop|Where-Object {$_.LocalAddress -cnotin @('127.0.0.1','::1')}).Count){throw 'KM_DEBUG_EXTERNAL_LISTENER'}
 Write-Output ([string]$ids[0])
 exit 0
}
$terminated=0
for($pass=0;$pass -lt 3;$pass++){
  $owned=@(OwnedFixture)
  Write-Output "KM_RESIDUAL_FIXTURE_BROWSER_COUNT=$($owned.Count)"
  if(!$owned.Count){break}
  if($owned.Count -gt 32){throw 'KM_RESIDUAL_SCOPE_LIMIT'}
  $handles=[Collections.Generic.List[Diagnostics.Process]]::new()
  try{
    foreach($p in $owned){
      $owner=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid
      if($owner.ReturnValue -ne 0 -or $owner.Sid -cne $sid -or !$p.ExecutablePath -or ![string]::Equals([IO.Path]::GetFullPath($p.ExecutablePath),$edge,[StringComparison]::OrdinalIgnoreCase)){throw 'KM_RESIDUAL_OWNER_UNVERIFIED'}
      $h=[Diagnostics.Process]::GetProcessById([int]$p.ProcessId)
      $handles.Add($h)
      $null=$h.Handle
      if($h.HasExited){continue}
      if(![string]::Equals([IO.Path]::GetFullPath($h.MainModule.FileName),$edge,[StringComparison]::OrdinalIgnoreCase) -or [Math]::Abs(($h.StartTime.ToUniversalTime()-$p.CreationDate.ToUniversalTime()).TotalSeconds) -gt 2){throw 'KM_RESIDUAL_PID_DRIFT'}
      $current=Get-CimInstance Win32_Process -Filter ('ProcessId='+$p.ProcessId)
      if(!$current -or $current.CreationDate -ne $p.CreationDate -or $current.CommandLine -cne $p.CommandLine -or $current.ExecutablePath -cne $p.ExecutablePath){throw 'KM_RESIDUAL_PROCESS_DRIFT'}
    }
    # Complete the whole batch's custody checks before any termination.
    # Held process handles, never a name-wide or recursive process kill.
    foreach($h in $handles){
      if(!$h.HasExited){$h.Kill();$terminated++}
    }
    foreach($h in $handles){if(!$h.WaitForExit(5000)){throw 'KM_RESIDUAL_EXIT_UNVERIFIED'}}
  }finally{foreach($h in $handles){$h.Dispose()}}
}
if(@(OwnedFixture).Count){throw 'KM_RESIDUAL_PROCESS_REMAINS'}
Write-Output "KM_FIXTURE_ONLY_TERMINATED=$terminated"
Write-Output 'KM_PROFILE_PROCESSES_CLEARED=PASS'
