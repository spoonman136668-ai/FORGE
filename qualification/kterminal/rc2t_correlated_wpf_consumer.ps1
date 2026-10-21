param(
 [Parameter(Mandatory=$true)][string]$Root,
 [Parameter(Mandatory=$true)][string]$OutputPath,
 [Parameter(Mandatory=$true)][string]$SandboxRoot
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'RC2T_STA_REQUIRED'}
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase
. (Join-Path $Root 'json-snapshot-io.ps1')
$source=[IO.File]::ReadAllText((Join-Path $Root 'dashboard-ui.ps1'))
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'RC2T_PRODUCTION_WPF_PARSE_FAILED'}
$consumer=$ast.Find({param($node) $node-is[Management.Automation.Language.IfStatementAst]-and
    $node.Clauses[0].Item1.Extent.Text-eq'Test-Path -LiteralPath $snapshotPath -PathType Leaf'},$true)
if($null-eq$consumer){throw 'RC2T_ORIGINAL_SNAPSHOT_CONSUMER_NOT_FOUND'}
$poll=[scriptblock]::Create($consumer.Extent.Text)
foreach($name in @('Update-Dashboard','Set-ValueText','Tone-Value','Tone-Money')){
  $definition=$ast.Find({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and
    $node.Name-eq$name},$true)
  if($null-eq$definition){throw 'RC2T_PRODUCTION_DASHBOARD_FUNCTION_MISSING'}
  . ([scriptblock]::Create($definition.Extent.Text))
}
$script:actualUpdateDashboard=${function:Update-Dashboard}
$brushConverter=[Windows.Media.BrushConverter]::new()
foreach($match in [regex]::Matches($source,'(?m)^\$brush[A-Za-z]+\s*=\s*\$brushConverter\.ConvertFromString\(''#[A-Fa-f0-9]+''\)')){
  . ([scriptblock]::Create($match.Value))
}
$script:selectedAsset='BTC-USDC'
$script:executionMode='LIVE'
$script:serverPort=0
$script:displayTimeZone='UTC'
$script:reconcileRequested=$false
$script:nativeAuthorityState='DISARMED'
$script:dashboardMetricsView=[pscustomobject]@{Controls=@{};TrancheMetrics=@{}}
$script:currentPositionQuantity=0
$script:currentReservedCash=0
$controls=@{}
foreach($match in [regex]::Matches($source,'x:Name="([A-Za-z][A-Za-z0-9]+)"')){
  $name=$match.Groups[1].Value
  $controls[$name]=[Windows.Controls.TextBlock]::new()
}
function Set-AssetSymbolIcon {}
function Read-DisplayNumber($value){return 0.0}
function Set-AssetSwitchLock {}
function Update-ChartTradeLevels($value){}
function Update-KTerminalDashboardMetrics($view,$snapshot){}
$panel=[Windows.Controls.StackPanel]::new()
foreach($name in @('EquityValue','AccountingValue','PositionStateValue','CostBasisValue','RealizedValue')){
  $control=$controls[$name]
  if($null-eq$control){throw 'RC2T_PRESENTATION_CONTROL_MISSING'}
  $control.FontSize=19
  $panel.Children.Add($control)|Out-Null
}
$window=[Windows.Window]::new()
$window.Width=640
$window.Height=240
$window.Content=$panel
$script:stage='PREPARE_WPF'
$script:watch=[Diagnostics.Stopwatch]::StartNew()
$script:recorded=New-Object 'Collections.Generic.List[object]'
$script:lastSeenUpdated=''
$script:waitingGeneration=0
$script:appliedGeneration=0
$script:publishAtMs=0.0
$script:readMs=0.0
$script:updateMs=0.0
$script:paintMs=0.0
$script:updateCalled=0
$script:lastSnapshotWrite=[datetime]::MinValue
$script:dashboardSnapshotApplied=$false
$sandboxPath=[IO.Path]::GetFullPath($SandboxRoot)
if(-not [IO.Directory]::Exists($sandboxPath)){throw 'RC2T_SANDBOX_MISSING'}
$snapshotPath=Join-Path $sandboxPath 'data\\ui-dashboard.json'
$readyPath=Join-Path $sandboxPath 'receiver-ready.flag'
$timer=[Windows.Threading.DispatcherTimer]::new()
$timer.Interval=[TimeSpan]::FromMilliseconds(50)
$timer.Add_Tick({
  # Execute production source AST and original JSON reader, then the actual
  # Update-Dashboard callback. The test-only WPF target is kept explicit.
  & $poll
})
function Update-Dashboard($snapshot){
  $nextUpdated=[string]$snapshot.updated_at
  if([string]::IsNullOrWhiteSpace($nextUpdated) -or $nextUpdated-eq$script:lastSeenUpdated){return}
  $script:lastSeenUpdated=$nextUpdated
  $script:stage='PRODUCTION_CALLBACK'
  $readAppliedStart=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  $start=$script:watch.Elapsed.TotalMilliseconds
  & $script:actualUpdateDashboard $snapshot
  $script:updateMs=$script:watch.Elapsed.TotalMilliseconds-$start
  if($controls['EquityValue'].Text-ne[string]$snapshot.equity -or
     $controls['AccountingValue'].Text-ne[string]$snapshot.accounting_status){
    throw 'RC2T_FINANCIAL_DISPLAY_INCOHERENT'
  }
  $script:updateCalled++
  $script:appliedGeneration++
  $script:stage='OFFSCREEN_WPF_RENDER'
  $startPaint=$script:watch.Elapsed.TotalMilliseconds
  $panel.Measure([Windows.Size]::new(640,220))
  $panel.Arrange([Windows.Rect]::new(0,0,640,220))
  $panel.UpdateLayout()
  $bitmap=[Windows.Media.Imaging.RenderTargetBitmap]::new(
    640,220,96,96,[Windows.Media.PixelFormats]::Pbgra32)
  $bitmap.Render($panel)
  $script:paintMs=$script:watch.Elapsed.TotalMilliseconds-$startPaint
  $script:recorded.Add([pscustomobject]@{
    generation=$script:appliedGeneration
    model_updated_at=$nextUpdated
    wpf_update_begin_unix_ms=$readAppliedStart
    wpf_render_end_unix_ms=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    production_update_ms=[math]::Round($script:updateMs,3)
    offscreen_layout_render_ms=[math]::Round($script:paintMs,3)
    production_poll_interval_ms=50
    actual_shipping_wpf_paint=$false
  })
}
function Pump-WPF([int]$Milliseconds){
  $frame=[Windows.Threading.DispatcherFrame]::new()
  $release=[Windows.Threading.DispatcherTimer]::new()
  $release.Interval=[TimeSpan]::FromMilliseconds($Milliseconds)
  $release.Add_Tick({$release.Stop();$frame.Continue=$false}.GetNewClosure())
  $release.Start()
  [Windows.Threading.Dispatcher]::PushFrame($frame)
}
try{
  $timer.Start()
  [IO.File]::WriteAllText($readyPath,'READY')
  $script:stage='WAIT_FOR_BACKEND_PUBLICATION'
  $watchStop=[DateTimeOffset]::UtcNow.AddSeconds(130)
  while($script:recorded.Count -lt 2 -and [DateTimeOffset]::UtcNow -lt $watchStop){
    Pump-WPF 100
  }
  if($script:recorded.Count-ne2){throw 'RC2T_CORRELATED_WPF_OBSERVATIONS_INCOMPLETE'}
  $script:stage='TIMING_REPORT'
  $rows=$script:recorded.ToArray()
  $summary=[ordered]@{
    schema='kterminal.rc2t.wpf-source-consumer-v1'
    original_snapshot_poller_AST=$true
    original_JSON_reader=$true
    original_Update_Dashboard=$true
    test_only_offscreen_WPF_render=$true
    actual_shipping_display_measured=$false
    samples=$rows
    result='PASS'
  }
  [IO.File]::WriteAllText($OutputPath,($summary|ConvertTo-Json -Depth 9))
  Write-Output 'KTERM_RC2T_WPF_CONSUMER=PASS'
  Write-Output ('KTERM_RC2T_SAMPLES='+$rows.Count)
}catch{
  Write-Output ('KTERM_RC2T_FAILURE_STAGE='+$script:stage)
  Write-Output ('KTERM_RC2T_FAILURE_CLASS='+$_.Exception.GetType().Name)
  throw
}finally{
  $timer.Stop()
  $window.Close()
  if([IO.File]::Exists($readyPath)){[IO.File]::Delete($readyPath)}
}
