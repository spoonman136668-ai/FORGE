param(
  [Parameter(Mandatory=$true)][string]$Root,
  [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'RC2S_LAYOUT_WRAPPER_STA_REQUIRED'}
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase,System.Xaml
# The unmodified historical test assumes a type already compiled in the
# shipping launcher. Restore only this *test setup* dependency, without
# editing the fixture or changing the financial/layout assertions it runs.
if(-not('KTerminal.Appearance.Palette'-as[type])){
  $refs=@('System.dll','System.Core.dll','System.Xml.dll',
     [Windows.FrameworkElement].Assembly.Location,
     [Windows.Media.Brush].Assembly.Location,
     [Windows.DependencyObject].Assembly.Location,
     [System.Xaml.XamlReader].Assembly.Location)
  Add-Type -Path @((Join-Path $Root 'appearance.cs'),(Join-Path $Root 'appearance-menu.cs')) -ReferencedAssemblies $refs
}
if(-not('KTerminal.Appearance.Palette'-as[type])){throw 'RC2S_REQUIRED_THEME_RUNTIME_UNAVAILABLE'}
& (Join-Path $Root 'verification/test-dashboard-resize.ps1') -Root $Root -OutputDirectory $OutputDirectory
if($LASTEXITCODE-ne0 -and $LASTEXITCODE-ne$null){throw 'RC2S_LAYOUT_ORIGINAL_ASSERTION_FAILURE'}
Write-Output 'KTERM_RC2S_LAYOUT_EXISTING_ASSERTIONS=PASS'
