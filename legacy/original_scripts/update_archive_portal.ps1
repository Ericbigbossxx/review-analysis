$ErrorActionPreference = 'Stop'

$SummaryPath = '.\review_summary.json'
$ReviewsPath = '.\negative_reviews.json'
$RunId = '2026-07-09-biweekly-review-analysis'
$ReportDate = '2026-07-09'
$ReportTitle = '2026-07-09 双周周会差评分析'
$Period = '2026 双周周会'
$ReportType = 'biweekly'
$ReportUrl = "reports/$RunId.html"
$Notes = 'THD & Lowes Top 10 / 核心新品差评分析'
if ($args.Count -gt 0) {
  $p = @{}
  for ($i = 0; $i -lt $args.Count; $i += 2) { $p[[string]$args[$i]] = [string]$args[$i + 1] }
  foreach ($name in @('SummaryPath','ReviewsPath','RunId','ReportDate','ReportTitle','Period','ReportType','ReportUrl','Notes')) {
    $key = "-$name"
    if ($p.ContainsKey($key)) { Set-Variable -Name $name -Value $p[$key] }
  }
}

function Html([object]$value) {
  if ($null -eq $value) { return '' }
  return [System.Net.WebUtility]::HtmlEncode([string]$value)
}
function Pct([double]$value) { return ('{0:P1}' -f $value) }
function Num([object]$value) { return ('{0:N0}' -f [double]$value) }

$summary = @(Get-Content -LiteralPath $SummaryPath -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$reviews = @(Get-Content -LiteralPath $ReviewsPath -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$platforms = @($summary | Select-Object -ExpandProperty platform -Unique)
foreach ($item in $summary) {
  $low = [int]$item.rating1 + [int]$item.rating2 + [int]$item.rating3
  $item | Add-Member -NotePropertyName lowStarReviews -NotePropertyValue $low -Force
  $item | Add-Member -NotePropertyName lowStarRate -NotePropertyValue $(if ([int]$item.totalReviews -gt 0) { $low / [double]$item.totalReviews } else { 0 }) -Force
}

$totalReviews = ($summary | Measure-Object totalReviews -Sum).Sum
$lowStarReviews = ($summary | Measure-Object lowStarReviews -Sum).Sum
$lowStarRate = if ($totalReviews -gt 0) { $lowStarReviews / [double]$totalReviews } else { 0 }
$strongNegative = ($summary | Measure-Object negativeReviews -Sum).Sum
$p0Count = @($summary | Where-Object { $_.urgency -match '^P0' }).Count
$topRisk = $summary | Sort-Object @{Expression='lowStarReviews';Descending=$true}, @{Expression='lowStarRate';Descending=$true} | Select-Object -First 1
$topThemes = @($reviews | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.theme) } | Group-Object theme | Sort-Object Count -Descending | Select-Object -First 3 | ForEach-Object { "$($_.Name) $($_.Count)" })

$record = [ordered]@{
  run_id = $RunId; title = $ReportTitle; date = $ReportDate; period = $Period
  report_type = $ReportType; platforms = $platforms
  totalReviews = [int]$totalReviews; lowStarReviews = [int]$lowStarReviews
  lowStarRate = [math]::Round([double]$lowStarRate, 4); strongNegativeReviews = [int]$strongNegative
  p0Count = [int]$p0Count; topThemes = $topThemes
  topRiskSku = "$($topRisk.platform) $($topRisk.sku)"; reportUrl = $ReportUrl; notes = $Notes
}

$manifestPath = '.\archive_manifest.json'
$existing = if (Test-Path $manifestPath) { @(Get-Content -LiteralPath $manifestPath -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ }) } else { @() }
$records = @($record) + @($existing | Where-Object { $_.run_id -ne $RunId })
[System.IO.File]::WriteAllText((Join-Path (Get-Location) $manifestPath), (ConvertTo-Json -InputObject $records -Depth 8), [System.Text.UTF8Encoding]::new($true))

$cards = [System.Text.StringBuilder]::new()
$rows = [System.Text.StringBuilder]::new()
foreach ($r in ($records | Sort-Object -Property @{Expression={ [datetime]$_.date }; Descending=$true})) {
  $platformText = $r.platforms -join ', '
  $themeText = $r.topThemes -join ' / '
  [void]$cards.AppendLine('<article class="run" data-type="' + (Html $r.report_type) + '" data-platforms="' + (Html $platformText) + '" data-date="' + (Html $r.date) + '"><div class="run-top"><span class="badge">' + (Html $r.report_type) + '</span><span>' + (Html $r.date) + '</span></div><h2>' + (Html $r.title) + '</h2><p>' + (Html $r.notes) + '</p><div class="metrics"><b>' + (Num $r.lowStarReviews) + '</b><span>1-3星</span><b>' + (Pct ([double]$r.lowStarRate)) + '</b><span>低分率</span><b>' + $r.p0Count + '</b><span>P0</span></div><a href="' + (Html $r.reportUrl) + '">打开报告</a></article>')
  [void]$rows.AppendLine('<tr data-type="' + (Html $r.report_type) + '" data-platforms="' + (Html $platformText) + '" data-date="' + (Html $r.date) + '"><td>' + (Html $r.date) + '</td><td><a href="' + (Html $r.reportUrl) + '">' + (Html $r.title) + '</a></td><td>' + (Html $r.report_type) + '</td><td>' + (Html $platformText) + '</td><td>' + (Num $r.totalReviews) + '</td><td>' + (Num $r.lowStarReviews) + '</td><td>' + (Pct ([double]$r.lowStarRate)) + '</td><td>' + $r.p0Count + '</td><td>' + (Html $r.topRiskSku) + '</td><td>' + (Html $themeText) + '</td></tr>')
}

$allPlatforms = @($records | ForEach-Object { $_.platforms } | Sort-Object -Unique)
$platformOptions = ($allPlatforms | ForEach-Object { '<option>' + (Html $_) + '</option>' }) -join ''
$latest = ($records | Sort-Object -Property @{Expression={ [datetime]$_.date }; Descending=$true} | Select-Object -First 1).reportUrl
$portal = @"
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Review Analysis Archive</title>
<style>body{margin:0;background:#f4f7f6;color:#17212b;font-family:Arial,"Microsoft YaHei",sans-serif;letter-spacing:0}header{background:#fff;border-bottom:1px solid #dbe3e8;padding:30px 42px}main{padding:24px 42px 48px}.head{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.sub{color:#66737f;line-height:1.6}.latest{display:inline-block;background:#25313a;color:#fff;text-decoration:none;padding:10px 14px;border-radius:6px;font-weight:800}.filters{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}.filters input,.filters select{border:1px solid #cbd6dd;border-radius:6px;padding:10px 12px;background:#fff}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}.run{background:#fff;border:1px solid #dbe3e8;border-radius:8px;padding:16px}.run-top{display:flex;justify-content:space-between;color:#66737f;font-size:13px}.badge{background:#edf5f2;color:#216653;border-radius:4px;padding:3px 8px;font-weight:800}.metrics{display:grid;grid-template-columns:repeat(3,auto 1fr);gap:4px 8px;margin:14px 0}.metrics b{font-size:22px}.metrics span{color:#66737f;font-size:12px;align-self:end}.run a{font-weight:800;color:#246b5a}section{margin-bottom:20px}.card{background:#fff;border:1px solid #dbe3e8;border-radius:8px;padding:18px}.tablewrap{max-height:560px;overflow:auto;border:1px solid #dbe3e8;border-radius:6px}table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}th,td{border-bottom:1px solid #e1e8ed;padding:10px 8px;text-align:left;vertical-align:top}th{background:#f8fafb;position:sticky;top:0}@media(max-width:800px){header,main{padding-left:18px;padding-right:18px}.head{display:block}.latest{margin-top:12px}.metrics{grid-template-columns:repeat(3,1fr)}}</style></head><body>
<header><div class="head"><div><h1>Review Analysis Archive</h1><div class="sub">长期存档页：每次分析保存为独立报告，可按日期、类型和平台筛选，并用于双周周会对比。</div></div><a class="latest" href="$latest">打开最新报告</a></div><div class="filters"><input id="q" placeholder="搜索日期/标题/SKU/主题"><select id="type"><option value="">全部类型</option><option value="biweekly">双周周会</option><option value="ad_hoc">日常分析</option></select><select id="platform"><option value="">全部平台</option>$platformOptions</select></div></header>
<main><section class="grid" id="cards">$cards</section><section class="card"><h2>跨期对比</h2><div class="tablewrap"><table><thead><tr><th>日期</th><th>期数/标题</th><th>类型</th><th>平台</th><th>Review</th><th>1-3星</th><th>1-3星率</th><th>P0</th><th>Top风险SKU</th><th>Top主题</th></tr></thead><tbody id="rows">$rows</tbody></table></div></section></main>
<script>const q=document.querySelector('#q'),type=document.querySelector('#type'),platform=document.querySelector('#platform'),items=[...document.querySelectorAll('[data-type]')];function apply(){const s=q.value.toLowerCase(),t=type.value,p=platform.value;items.forEach(el=>{const text=el.innerText.toLowerCase(),ok=(!s||text.includes(s))&&(!t||el.dataset.type===t)&&(!p||el.dataset.platforms.includes(p));el.style.display=ok?'':'none'})}q.oninput=type.onchange=platform.onchange=apply;</script></body></html>
"@
[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'index.html'), $portal, [System.Text.UTF8Encoding]::new($true))
Write-Host "Archive updated with $RunId; $($records.Count) immutable reports indexed."
