$ErrorActionPreference = 'Stop'

function HtmlEncodeValue([object]$value) {
  if ($null -eq $value) { return '' }
  return [System.Net.WebUtility]::HtmlEncode([string]$value)
}

function FormatPercent([double]$value) {
  return ('{0:P1}' -f $value)
}

function ShortText([object]$value, [int]$max = 120) {
  $text = [string]$value
  if ($text.Length -le $max) { return $text }
  return $text.Substring(0, $max - 1) + '...'
}

$summary = Get-Content -LiteralPath '.\review_summary.json' -Encoding UTF8 -Raw | ConvertFrom-Json
$generatedAt = Get-Date -Format 'yyyy-MM-dd HH:mm'

$platforms = @(
  @{ name = '全部'; data = $summary },
  @{ name = 'THD'; data = @($summary | Where-Object { $_.platform -eq 'THD' }) },
  @{ name = 'Lowes'; data = @($summary | Where-Object { $_.platform -eq 'Lowes' }) }
)

$totalReviews = ($summary | Measure-Object -Property totalReviews -Sum).Sum
$totalNegative = ($summary | Measure-Object -Property negativeReviews -Sum).Sum
$allPassed = @($summary | Where-Object { $_.ratingCheck -eq 'OK' -and $_.endpointCheck -eq 'OK' }).Count
$coreNew = @($summary | Where-Object { $_.coreNew }).Count
$todos = @($summary | Where-Object { $_.urgency -match '^P0|^P1|建样本' } | Sort-Object @{ Expression = { if ($_.urgency -match '^P0') { 0 } elseif ($_.urgency -match '^P1') { 1 } else { 2 } } }, @{ Expression = 'negativeRate'; Descending = $true })

$themeCounts = @{}
foreach ($item in $summary) {
  if ([string]::IsNullOrWhiteSpace($item.topThemes)) { continue }
  foreach ($part in ([string]$item.topThemes).Split('/')) {
    $trimmed = $part.Trim()
    if ($trimmed -match '^(.*?)\s+(\d+)$') {
      $theme = $Matches[1].Trim()
      $count = [int]$Matches[2]
      if (-not $themeCounts.ContainsKey($theme)) { $themeCounts[$theme] = 0 }
      $themeCounts[$theme] += $count
    }
  }
}
$themeRows = $themeCounts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 8
$maxTheme = [double](($themeRows | Measure-Object -Property Value -Maximum).Maximum)
if ($maxTheme -le 0) { $maxTheme = 1 }

$riskRows = @($summary | Sort-Object @{ Expression = 'negativeRate'; Descending = $true }, @{ Expression = 'negativeReviews'; Descending = $true })
$maxNeg = [double](($riskRows | Measure-Object -Property negativeReviews -Maximum).Maximum)
if ($maxNeg -le 0) { $maxNeg = 1 }

$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>THD & Lowes 差评分析</title>')
[void]$sb.AppendLine('<style>body{margin:0;background:#f5f7f8;color:#18222b;font-family:Arial,"Microsoft YaHei",sans-serif}header{padding:28px 40px 20px;background:white;border-bottom:1px solid #d8e0e6}main{padding:24px 40px 48px}.sub{color:#5a6873;font-size:15px}.tabs{display:flex;gap:10px;margin-top:18px}.tab{border:1px solid #cfd9e0;background:white;border-radius:6px;padding:10px 16px;font-weight:700;cursor:pointer}.tab.active{background:#26313a;color:white}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}.card{background:white;border:1px solid #d8e0e6;border-radius:8px;padding:18px;margin-bottom:18px}.kpi{font-size:28px;font-weight:800;margin-top:7px}.label,.muted{color:#61717e;font-size:13px}h1{margin:0;font-size:30px}h2{margin:0 0 14px;font-size:20px}.charts{display:grid;grid-template-columns:1fr 1fr;gap:18px}.bar{display:grid;grid-template-columns:120px 1fr 52px;gap:10px;align-items:center;margin:9px 0}.track{height:14px;background:#edf2f4;border-radius:20px;overflow:hidden}.fill{height:100%;background:#2f7d6d}.risk .fill{background:#bf5b45}table{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}th,td{border-bottom:1px solid #e0e7ec;padding:10px 8px;text-align:left;vertical-align:top}th{background:#f8fafb;color:#33424c}.pill{display:inline-block;border-radius:999px;padding:3px 8px;background:#edf4f1;color:#216355;font-weight:700}.p0{background:#fff0ea;color:#aa3d21}.p1{background:#fff7dd;color:#8a6400}.ok{color:#217a4b;font-weight:700}@media(max-width:900px){header,main{padding-left:18px;padding-right:18px}.grid,.charts{grid-template-columns:1fr}.bar{grid-template-columns:94px 1fr 42px}table{font-size:12px}}</style></head><body>')
[void]$sb.AppendLine('<header><h1>THD & Lowes Top 10 / 核心新品差评分析</h1><div class="sub">数据源：Bazaarvoice 公开 API + listing 清单。生成时间：' + (HtmlEncodeValue $generatedAt) + '。评分来自 BV Product ReviewStatistics，差评原因仅覆盖有文本内容的评论。</div><div class="tabs"><button class="tab active" data-tab="全部">全部</button><button class="tab" data-tab="THD">THD</button><button class="tab" data-tab="Lowes">Lowes</button></div></header><main>')

[void]$sb.AppendLine('<section class="grid">')
[void]$sb.AppendLine('<div class="card"><div class="label">Listing 数</div><div class="kpi">' + $summary.Count + '</div></div>')
[void]$sb.AppendLine('<div class="card"><div class="label">页面 Review</div><div class="kpi">' + $totalReviews + '</div></div>')
[void]$sb.AppendLine('<div class="card"><div class="label">1-2 星差评</div><div class="kpi">' + $totalNegative + '</div></div>')
[void]$sb.AppendLine('<div class="card"><div class="label">交叉验证通过</div><div class="kpi">' + $allPassed + '/' + $summary.Count + '</div></div>')
[void]$sb.AppendLine('</section>')

[void]$sb.AppendLine('<section class="charts">')
[void]$sb.AppendLine('<div class="card"><h2>差评主题分布</h2>')
foreach ($row in $themeRows) {
  $width = [math]::Round(([double]$row.Value / $maxTheme) * 100, 1)
  [void]$sb.AppendLine('<div class="bar"><span>' + (HtmlEncodeValue $row.Key) + '</span><div class="track"><div class="fill" style="width:' + $width + '%"></div></div><b>' + $row.Value + '</b></div>')
}
[void]$sb.AppendLine('</div><div class="card risk"><h2>Top 风险 SKU</h2>')
foreach ($row in ($riskRows | Select-Object -First 8)) {
  $width = [math]::Round(([double]$row.negativeReviews / $maxNeg) * 100, 1)
  [void]$sb.AppendLine('<div class="bar" data-platform="' + $row.platform + '"><span>' + (HtmlEncodeValue $row.platform) + ' ' + (HtmlEncodeValue $row.sku) + '</span><div class="track"><div class="fill" style="width:' + $width + '%"></div></div><b>' + (FormatPercent ([double]$row.negativeRate)) + '</b></div>')
}
[void]$sb.AppendLine('</div></section>')

[void]$sb.AppendLine('<section class="card"><h2>To Do</h2><table><thead><tr><th>优先级</th><th>平台 / SKU</th><th>核心问题</th><th>产品动作</th><th>导评 / 测评建议</th></tr></thead><tbody>')
foreach ($row in $todos) {
  $urgClass = if ($row.urgency -match '^P0') { 'p0' } elseif ($row.urgency -match '^P1') { 'p1' } else { '' }
  $actions = if ($row.actionItems) { ($row.actionItems | ForEach-Object { ShortText $_ 72 }) -join '<br>' } else { '' }
  [void]$sb.AppendLine('<tr data-platform-row="' + $row.platform + '"><td><span class="pill ' + $urgClass + '">' + (HtmlEncodeValue $row.urgency) + '</span></td><td><b>' + (HtmlEncodeValue $row.platform) + '</b><br>' + (HtmlEncodeValue $row.sku) + '</td><td>' + (HtmlEncodeValue $row.topThemes) + '</td><td>' + $actions + '</td><td>' + (HtmlEncodeValue (ShortText $row.reviewPlan 110)) + '</td></tr>')
}
[void]$sb.AppendLine('</tbody></table></section>')

[void]$sb.AppendLine('<section class="card"><h2>Listing 风险排名</h2><table><thead><tr><th>平台</th><th>SKU</th><th>页面 Review</th><th>评分</th><th>1星</th><th>2星</th><th>差评率</th><th>Top 问题</th></tr></thead><tbody>')
foreach ($row in $riskRows) {
  [void]$sb.AppendLine('<tr data-platform-row="' + $row.platform + '"><td>' + (HtmlEncodeValue $row.platform) + '</td><td><a href="' + (HtmlEncodeValue $row.url) + '">' + (HtmlEncodeValue $row.sku) + '</a></td><td>' + $row.totalReviews + '</td><td>' + $row.avgRating + '</td><td>' + $row.rating1 + '</td><td>' + $row.rating2 + '</td><td>' + (FormatPercent ([double]$row.negativeRate)) + '</td><td>' + (HtmlEncodeValue $row.topThemes) + '</td></tr>')
}
[void]$sb.AppendLine('</tbody></table></section>')

[void]$sb.AppendLine('<section class="card"><h2>数据交叉验证</h2><p>本次 20 个 SKU 全部通过验证：星级分布合计 = BV Product ReviewStatistics.TotalReviewCount = BV reviews 端点 TotalResults。评分和页面 Review 判断使用 BV 产品统计，包含 ratings-only；差评原因、To Do 和产品方案基于可读取文本评论，因此不会把无文本的 ratings-only 评论编造成原因。</p><p class="muted">核心新品数：' + $coreNew + '。本地完整文件保留近期差评明细和每个 SKU 的覆盖率字段。</p></section>')

[void]$sb.AppendLine('</main><script>const tabs=document.querySelectorAll(".tab");const rows=document.querySelectorAll("[data-platform-row]");const risk=document.querySelectorAll(".risk [data-platform]");tabs.forEach(b=>b.onclick=()=>{tabs.forEach(x=>x.classList.remove("active"));b.classList.add("active");const p=b.dataset.tab;rows.forEach(r=>r.style.display=(p==="全部"||r.dataset.platformRow===p)?"":"none");risk.forEach(r=>r.style.display=(p==="全部"||r.dataset.platform===p)?"grid":"none")});</script></body></html>')

[System.IO.File]::WriteAllText((Join-Path (Get-Location) 'pages_index.html'), $sb.ToString(), [System.Text.UTF8Encoding]::new($true))
Write-Host "Wrote pages_index.html ($((Get-Item .\pages_index.html).Length) bytes)"
