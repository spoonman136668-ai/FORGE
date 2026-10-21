param(
 [Parameter(Mandatory=$true)][string]$Root,
 [Parameter(Mandatory=$true)][string]$OutputPath
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
if([Threading.Thread]::CurrentThread.ApartmentState-ne'STA'){throw 'RC2S_STA_REQUIRED'}
Add-Type -AssemblyName PresentationFramework,PresentationCore,WindowsBase
. (Join-Path $Root 'json-snapshot-io.ps1')
$source=[IO.File]::ReadAllText((Join-Path $Root 'dashboard-ui.ps1'))
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'RC2S_PRODUCTION_WPF_PARSE_FAILED'}
$consumer=$ast.Find({param($node) $node-is[Management.Automation.Language.IfStatementAst]-and
    $node.Clauses[0].Item1.Extent.Text-eq'Test-Path -LiteralPath $snapshotPath -PathType Leaf'},$true)
if($null-eq$consumer){throw 'RC2S_ORIGINAL_SNAPSHOT_CONSUMER_NOT_FOUND'}
$poll=[scriptblock]::Create($consumer.Extent.Text)
foreach($name in @('Update-Dashboard','Set-ValueText','Tone-Value','Tone-Money')){
  $definition=$ast.Find({param($node)$node-is[Management.Automation.Language.FunctionDefinitionAst]-and
    $node.Name-eq$name},$true)
  if($null-eq$definition){throw 'RC2S_PRODUCTION_DASHBOARD_FUNCTION_MISSING'}
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
  if($null-eq$control){throw 'RC2S_PRESENTATION_CONTROL_MISSING'}
  $control.FontSize=19
  $panel.Children.Add($control)|Out-Null
}
$window=[Windows.Window]::new()
$window.Width=640
$window.Height=240
$window.Content=$panel
$script:watch=[Diagnostics.Stopwatch]::StartNew()
$script:recorded=New-Object 'Collections.Generic.List[object]'
$script:waitingGeneration=0
$script:appliedGeneration=0
$script:publishAtMs=0.0
$script:readMs=0.0
$script:updateMs=0.0
$script:paintMs=0.0
$script:updateCalled=0
$script:lastSnapshotWrite=[datetime]::MinValue
$script:dashboardSnapshotApplied=$false
$folder=Join-Path ([IO.Path]::GetTempPath()) ('kterm-rc2s-'+[guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($folder)|Out-Null
$snapshotPath=Join-Path $folder 'dashboard-ui-snapshot.json'
$timer=[Windows.Threading.DispatcherTimer]::new()
$timer.Interval=[TimeSpan]::FromMilliseconds(50)
$timer.Add_Tick({
  # Execute production source AST and original JSON reader, then the actual
  # Update-Dashboard callback. The test-only WPF target is kept explicit.
  & $poll
})
function Update-Dashboard($snapshot){
  $start=$script:watch.Elapsed.TotalMilliseconds
  & $script:actualUpdateDashboard $snapshot
  $script:updateMs=$script:watch.Elapsed.TotalMilliseconds-$start
  if($controls['EquityValue'].Text-ne[string]$snapshot.equity -or
     $controls['AccountingValue'].Text-ne[string]$snapshot.accounting_status){
    throw 'RC2S_FINANCIAL_DISPLAY_INCOHERENT'
  }
  $script:updateCalled++
  $script:appliedGeneration=[int]$snapshot.generation
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
    source_publish_to_update_ms=[math]::Round($script:watch.Elapsed.TotalMilliseconds-$script:publishAtMs,3)
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
  foreach($generation in 1..6){
    $snapshot=[ordered]@{
      generation=$generation;product_id='BTC-USDC';price='$76500.00';market='LIVE'
      equity=('$'+(500+$generation)+'.00');cash_available='$500.00';reserved_cash='$0.00'
      realized_pnl='+$10.00';current_drawdown='$0.00';max_drawdown='$0.00'
      position_state='FLAT';position_quantity='0.00000000 BTC'
      position_value='$0.00 | 0.00%';cost_basis='$0.00';average_buy='N/A'
      unrealized_pnl='$0.00';accounting_status='VERIFIED'
      sell_floor='N/A';tp_label='TP1 @';tp_price='N/A'
      calculated_tp_pnl='N/A';tp_distance_label='TP STATUS'
      tp_distance='NOT APPLICABLE';tp_targets='0.369%'
      status='LIVE'
    }
    $payload=$snapshot|ConvertTo-Json -Compress -Depth 5
    $candidate=$snapshotPath+'.tmp'
    [IO.File]::WriteAllText($candidate,$payload)
    Move-KTerminalAtomicFile -TemporaryPath $candidate -Path $snapshotPath
    # Changes must be observable even on coarse filesystem timestamp ticks.
    [IO.File]::SetLastWriteTimeUtc($snapshotPath,[datetime]::UtcNow.AddSeconds($generation))
    $script:publishAtMs=$script:watch.Elapsed.TotalMilliseconds
    Pump-WPF 140
    if($script:appliedGeneration-ne$generation){
      throw 'RC2S_SNAPSHOT_NOT_CONSUMED_WITHIN_BOUNDED_DISPATCHER_PUMPS'
    }
  }
  if($script:recorded.Count-ne6 -or $script:updateCalled-ne6){
    throw 'RC2S_MISSED_OR_DUPLICATE_APPLICATION'
  }
  if($script:recorded|Where-Object{$_.source_publish_to_update_ms-lt0 -or
      $_.source_publish_to_update_ms-gt500}){
    throw 'RC2S_PRESENTATION_LATENCY_EXCEEDED_BOUNDED_DIAGNOSTIC'
  }
  $rows=@($script:recorded)
  $summary=[ordered]@{
    schema='kterminal.rc2s.wpf-poll-actual-callback-diagnostic.v1'
    production_wpf_poll_AST=$true
    production_json_reader=$true
    production_Update_Dashboard_callback=$true
    test_only_WPF_textblock_layout_render=$true
    shipping_window_pixel_paint_measured=$false
    backend_refresh_ticker_measured=$false
    no_app_or_broker=$true
    samples=$rows
    result='PASS'
  }
  [IO.File]::WriteAllText($OutputPath,($summary|ConvertTo-Json -Depth 9))
  Write-Output ('KTERM_RC2S_SNAPSHOT_POLL=PASS')
  Write-Output ('KTERM_RC2S_SAMPLES='+$rows.Count)
  Write-Output ('KTERM_RC2S_MAX_PUBLISH_TO_WPF_MS='+([math]::Round((@($rows|ForEach-Object{$_.source_publish_to_update_ms}|Measure-Object -Maximum).Maximum),3)))
  Write-Output ('KTERM_RC2S_SHIPPING_PIXEL_PAINT=NOT_MEASURED')
}finally{
  $timer.Stop()
  $window.Close()
  [IO.Directory]::Delete($folder,$true)
}
