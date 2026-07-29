$ErrorActionPreference = "Stop"

$workspace = "C:\Users\admin\Documents\Weekly review analysis"
$summaryPath = Join-Path $workspace "review_summary.json"
$reviewsPath = Join-Path $workspace "negative_reviews.json"
$indexPath = Join-Path $workspace "index.html"
$dashboardPath = Join-Path $workspace "thd_lowes_review_dashboard.html"

function HtmlEncodeValue {
  param($Value)
  if ($null -eq $Value) { return "" }
  return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

function Pct {
  param($Value)
  return "{0:N1}%" -f ([double]$Value * 100)
}

function DateOnly {
  param($Value)
  if (-not $Value) { return "-" }
  return ([string]$Value).Substring(0, [Math]::Min(10, ([string]$Value).Length))
}

function RiskClass {
  param([double]$Rate)
  if ($Rate -ge 0.25) { return "bad" }
  if ($Rate -ge 0.12) { return "mid" }
  return "good"
}

function PriorityClass {
  param([string]$Urgency)
  if ($Urgency -match "^P0") { return "bad" }
  if ($Urgency -match "^P1") { return "mid" }
  return "good"
}

function StatusClass {
  param([string]$Status)
  if ($Status -eq "OK" -or $Status -eq "可用于评分判断") { return "ok" }
  return "warn"
}

function ThemeRows {
  param($Rows, [string]$Platform)
  $scope = if ($Platform -eq "All") { $Rows } else { $Rows | Where-Object { $_.platform -eq $Platform } }
  $groups = $scope | Where-Object { $_.rating -le 2 } | Group-Object theme | Sort-Object Count -Descending | Select-Object -First 10
  if (-not $groups) { return "<p class=`"note`">当前筛选无差评文本。</p>" }
  $max = ($groups | Measure-Object Count -Maximum).Maximum
  return (($groups | ForEach-Object {
    $w = [Math]::Max(4, [Math]::Round($_.Count / $max * 100, 1))
    "<div class=`"bar-row`"><div>$(HtmlEncodeValue $_.Name)</div><div class=`"track`"><div class=`"fill`" style=`"width:$w%`"></div></div><div>$($_.Count)</div></div>"
  }) -join "`n")
}

function ProductRiskRows {
  param($Rows, [string]$Platform)
  $scope = if ($Platform -eq "All") { $Rows } else { $Rows | Where-Object { $_.platform -eq $Platform } }
  $top = $scope | Sort-Object @{ Expression = "negativeRate"; Descending = $true }, @{ Expression = "negativeReviews"; Descending = $true } | Select-Object -First 10
  if (-not $top) { return "<p class=`"note`">当前筛选无 listing。</p>" }
  $max = [Math]::Max(0.01, ($top | Measure-Object negativeRate -Maximum).Maximum)
  return (($top | ForEach-Object {
    $w = [Math]::Max(4, [Math]::Round($_.negativeRate / $max * 100, 1))
    "<div class=`"bar-row risk`"><div><b>$(HtmlEncodeValue $_.sku)</b><br><span class=`"sub`">$(HtmlEncodeValue $_.platform)</span></div><div class=`"track`"><div class=`"fill risk-fill`" style=`"width:$w%`"></div></div><div>$(Pct $_.negativeRate)</div></div>"
  }) -join "`n")
}

$summaries = Get-Content -LiteralPath $summaryPath -Encoding UTF8 -Raw | ConvertFrom-Json
$reviews = Get-Content -LiteralPath $reviewsPath -Encoding UTF8 -Raw | ConvertFrom-Json
$generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$platformCards = @()
foreach ($platform in @("All", "THD", "Lowes")) {
  $rows = if ($platform -eq "All") { $summaries } else { $summaries | Where-Object { $_.platform -eq $platform } }
  $totalReviews = ($rows | Measure-Object totalReviews -Sum).Sum
  $bad = ($rows | Measure-Object negativeReviews -Sum).Sum
  $weighted = if ($totalReviews -gt 0) { (($rows | ForEach-Object { $_.avgRating * $_.totalReviews } | Measure-Object -Sum).Sum / $totalReviews) } else { 0 }
  $core = @($rows | Where-Object { $_.coreNew }).Count
  $platformCards += "<div class=`"card kpi-card`" data-platform-block=`"$platform`"><div class=`"metric`">$(if($platform -eq 'All'){'全部'}else{$platform})</div><div class=`"value`">$($rows.Count) / $("{0:N0}" -f $totalReviews)</div><div class=`"sub`">Listing / Review；差评 $(Pct $(if($totalReviews -gt 0){$bad/$totalReviews}else{0}))；评分 $("{0:N2}" -f $weighted)；核心新品 $core</div></div>"
}

$qaRows = ($summaries | ForEach-Object {
  $tc = Pct $_.textCoverage
  $ntc = Pct $_.negativeTextCoverage
  "<tr data-platform-row=`"$($_.platform)`"><td><span class=`"platform-mark $($_.platform)`">$(HtmlEncodeValue $_.platform)</span></td><td><a href=`"$(HtmlEncodeValue $_.url)`" target=`"_blank`">$(HtmlEncodeValue $_.sku)</a></td><td><span class=`"status $(StatusClass $_.qaStatus)`">$(HtmlEncodeValue $_.qaStatus)</span></td><td>$($_.totalReviews) / $($_.ratingDistributionSum)<br><span class=`"status $(StatusClass $_.ratingCheck)`">$(HtmlEncodeValue $_.ratingCheck)</span></td><td>$($_.endpointAllReviews)<br><span class=`"status $(StatusClass $_.endpointCheck)`">$(HtmlEncodeValue $_.endpointCheck)</span></td><td>$($_.endpointTextReviews) / $($_.expectedTextReviews)<br><span class=`"sub`">$tc</span></td><td>$($_.textNegativeReviews) / $($_.negativeReviews)<br><span class=`"sub`">$ntc</span></td></tr>"
}) -join "`n"

$todoItems = $summaries |
  Sort-Object @{ Expression = { if ($_.urgency -match "^P0") { 0 } elseif ($_.urgency -match "^P1") { 1 } else { 2 } } }, @{ Expression = "negativeReviews"; Descending = $true }, @{ Expression = "negativeRate"; Descending = $true } |
  Select-Object -First 12

$todoRows = ($todoItems | ForEach-Object {
  $items = @($_.actionItems) | ForEach-Object { "<li>$(HtmlEncodeValue $_)</li>" }
  "<tr data-platform-row=`"$($_.platform)`"><td><span class=`"pill $(PriorityClass $_.urgency)`">$(HtmlEncodeValue $_.urgency)</span></td><td><span class=`"platform-mark $($_.platform)`">$(HtmlEncodeValue $_.platform)</span><br><a href=`"$(HtmlEncodeValue $_.url)`" target=`"_blank`">$(HtmlEncodeValue $_.sku)</a><br><span class=`"sub`">$(HtmlEncodeValue $_.category)$(if($_.coreNew){' / 核心新品'}else{''})</span></td><td>$($_.negativeReviews) 条低星 / $(Pct $_.negativeRate)<br><span class=`"sub`">$(HtmlEncodeValue $_.topThemes)</span></td><td>$(HtmlEncodeValue $_.reviewPlan)</td><td><ul class=`"todo-list`">$($items -join '')</ul></td></tr>"
}) -join "`n"

$coreRows = ($summaries | Where-Object { $_.coreNew } | Sort-Object platform, sku | ForEach-Object {
  "<tr data-platform-row=`"$($_.platform)`"><td><span class=`"platform-mark $($_.platform)`">$(HtmlEncodeValue $_.platform)</span></td><td><a href=`"$(HtmlEncodeValue $_.url)`" target=`"_blank`">$(HtmlEncodeValue $_.sku)</a></td><td>$($_.totalReviews)</td><td>$("{0:N2}" -f $_.avgRating)</td><td><span class=`"pill $(RiskClass $_.negativeRate)`">$(Pct $_.negativeRate)</span></td><td>$(HtmlEncodeValue $(if($_.topThemes){$_.topThemes}else{'-' }))</td></tr>"
}) -join "`n"

$productRows = ($summaries | Sort-Object @{ Expression = "negativeRate"; Descending = $true }, @{ Expression = "negativeReviews"; Descending = $true } | ForEach-Object {
  "<tr data-platform-row=`"$($_.platform)`"><td><span class=`"platform-mark $($_.platform)`">$(HtmlEncodeValue $_.platform)</span></td><td><a href=`"$(HtmlEncodeValue $_.url)`" target=`"_blank`">$(HtmlEncodeValue $_.sku)</a></td><td>$(HtmlEncodeValue $_.brand)<br><span class=`"sub`">$(HtmlEncodeValue $_.category)</span></td><td>$($_.totalReviews)</td><td>$("{0:N2}" -f $_.avgRating)</td><td>$($_.rating1)</td><td>$($_.rating2)</td><td><span class=`"pill $(RiskClass $_.negativeRate)`">$(Pct $_.negativeRate)</span></td><td>$(DateOnly $_.lastReview)</td><td>$(HtmlEncodeValue $(if($_.topThemes){$_.topThemes}else{'-' }))</td></tr>"
}) -join "`n"

$recentRows = ($reviews | Where-Object { $_.rating -le 2 } | Sort-Object date -Descending | Select-Object -First 40 | ForEach-Object {
  $excerpt = "$(if($_.title){$_.title + ' - '}else{''})$($_.text)"
  if ($excerpt.Length -gt 420) { $excerpt = $excerpt.Substring(0, 420) + "..." }
  "<tr data-platform-row=`"$($_.platform)`"><td><span class=`"platform-mark $($_.platform)`">$(HtmlEncodeValue $_.platform)</span></td><td><a href=`"$(HtmlEncodeValue $_.url)`" target=`"_blank`">$(HtmlEncodeValue $_.sku)</a></td><td><span class=`"pill bad`">$($_.rating)星</span></td><td>$(HtmlEncodeValue $_.theme)</td><td>$(DateOnly $_.date)</td><td class=`"review-text`">$(HtmlEncodeValue $excerpt)</td></tr>"
}) -join "`n"

$chartBlocks = @()
foreach ($platform in @("All", "THD", "Lowes")) {
  $hidden = if ($platform -eq "All") { "" } else { " hidden" }
  $label = if ($platform -eq "All") { "全部" } else { $platform }
  $chartBlocks += "<div data-chart=`"$platform`"$hidden><h3>$label：差评主题</h3><div class=`"bars`">$(ThemeRows $reviews $platform)</div><h3 class=`"chart-subtitle`">$label：风险 listing</h3><div class=`"bars`">$(ProductRiskRows $summaries $platform)</div></div>"
}

$html = @"
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THD & Lowes Top 10 / 核心新品差评分析</title>
  <style>
    :root { --ink:#172026; --muted:#5f6b73; --line:#d9e0e4; --panel:#fff; --bg:#f5f7f8; --thd:#f96302; --lowes:#004990; --risk:#c83f31; --mid:#a66a00; --ok:#287d5a; }
    *{box-sizing:border-box} body{margin:0;font-family:Arial,"Microsoft YaHei",sans-serif;color:var(--ink);background:var(--bg)} header{padding:24px 28px 16px;background:#fff;border-bottom:1px solid var(--line)} h1{margin:0 0 8px;font-size:28px;line-height:1.25} h2{margin:0 0 12px;font-size:18px} h3{margin:12px 0 8px;font-size:14px} p{margin:0;color:var(--muted);line-height:1.55} main{padding:20px 28px 36px;max-width:1500px;margin:0 auto}.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}button{border:1px solid var(--line);background:#fff;color:var(--ink);height:34px;padding:0 12px;border-radius:6px;cursor:pointer;font-weight:700}button.active[data-platform="THD"]{background:var(--thd);border-color:var(--thd);color:#fff}button.active[data-platform="Lowes"]{background:var(--lowes);border-color:var(--lowes);color:#fff}button.active[data-platform="All"]{background:#25313a;border-color:#25313a;color:#fff}section{margin-top:18px}.grid{display:grid;gap:14px}.kpis{grid-template-columns:repeat(3,minmax(0,1fr))}.two{grid-template-columns:1fr 1fr}.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px}.metric{color:var(--muted);font-size:13px}.value{font-size:28px;font-weight:800;margin-top:8px}.sub,.note{color:var(--muted);font-size:12px}.bars{display:grid;gap:10px}.bar-row{display:grid;grid-template-columns:140px 1fr 56px;gap:10px;align-items:center;font-size:13px}.bar-row.risk{grid-template-columns:160px 1fr 64px}.track{height:12px;background:#edf1f3;border-radius:999px;overflow:hidden}.fill{height:100%;background:var(--risk)}.risk-fill{background:#375a7f}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:#3f4a51;background:#f9fbfc;position:sticky;top:0;z-index:1}a{color:#0b67a3;text-decoration:none}.table-wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:8px;background:#fff}.pill,.status{display:inline-block;min-width:52px;padding:3px 7px;border-radius:999px;font-weight:700;text-align:center;font-size:12px}.bad{background:#ffe5e0;color:#a12216}.mid,.warn{background:#fff2cc;color:#805000}.good,.ok{background:#e1f1ea;color:#176244}.review-text{max-width:620px;color:#2f3b42;line-height:1.45}.platform-mark{font-weight:800}.platform-mark.THD{color:var(--thd)}.platform-mark.Lowes{color:var(--lowes)}.todo-list{margin:0;padding-left:18px;color:#2f3b42;line-height:1.45}.todo-list li{margin:0 0 4px}.chart-subtitle{margin-top:18px}@media(max-width:920px){header,main{padding-left:16px;padding-right:16px}.kpis,.two{grid-template-columns:1fr}.bar-row,.bar-row.risk{grid-template-columns:96px 1fr 44px}h1{font-size:22px}}
  </style>
</head>
<body>
  <header>
    <h1>THD & Lowes Top 10 / 核心新品差评分析</h1>
    <p>静态优先版：表格和 To Do 已直接写入 HTML，脚本只负责筛选。评分来自 BV Product ReviewStatistics；差评原因来自可读文本评论。</p>
    <div class="toolbar"><button class="active" data-platform="All">全部</button><button data-platform="THD">THD</button><button data-platform="Lowes">Lowes</button></div>
  </header>
  <main>
    <section class="grid kpis">$($platformCards -join "`n")</section>
    <section class="grid two"><div class="card"><h2>可视化</h2>$($chartBlocks -join "`n")</div><div class="card"><h2>核心新品概览</h2><div class="table-wrap" style="max-height:420px"><table><thead><tr><th>平台</th><th>SKU</th><th>评论</th><th>评分</th><th>差评率</th><th>主要问题</th></tr></thead><tbody>$coreRows</tbody></table></div></div></section>
    <section class="card"><h2>数据交叉验证</h2><div class="table-wrap"><table><thead><tr><th>平台</th><th>SKU</th><th>评分口径</th><th>总评/星级合计</th><th>BV reviews 端点</th><th>文本覆盖</th><th>低星文本覆盖</th></tr></thead><tbody>$qaRows</tbody></table></div><p class="note">本次校验：星级合计、Product 总评、reviews 端点总数均用于交叉验证；文本覆盖用于说明差评原因分析的样本完整度。</p></section>
    <section class="card"><h2>本周 To Do</h2><div class="table-wrap"><table><thead><tr><th>优先级</th><th>平台/SKU</th><th>风险</th><th>导评/测评建议</th><th>产品与运营动作</th></tr></thead><tbody>$todoRows</tbody></table></div></section>
    <section class="card"><h2>Listing 差评风险排名</h2><div class="table-wrap"><table><thead><tr><th>平台</th><th>SKU</th><th>品牌/品类</th><th>页面 Review</th><th>评分</th><th>1星</th><th>2星</th><th>差评率</th><th>最近评论</th><th>Top 问题</th></tr></thead><tbody>$productRows</tbody></table></div></section>
    <section class="card"><h2>近期差评明细</h2><div class="table-wrap"><table><thead><tr><th>平台</th><th>SKU</th><th>星级</th><th>主题</th><th>日期</th><th>评论摘录</th></tr></thead><tbody>$recentRows</tbody></table></div><p class="note">看板保留最近 40 条 1-2 星文本评论；完整提取结果见本地 negative_reviews.json。生成时间：$generatedAt。</p></section>
  </main>
  <script>
    function setPlatform(platform) {
      document.querySelectorAll('button[data-platform]').forEach(btn => btn.classList.toggle('active', btn.dataset.platform === platform));
      document.querySelectorAll('[data-platform-row]').forEach(row => { row.hidden = platform !== 'All' && row.dataset.platformRow !== platform; });
      document.querySelectorAll('[data-platform-block]').forEach(card => { card.hidden = platform !== 'All' && card.dataset.platformBlock !== platform; });
      document.querySelectorAll('[data-chart]').forEach(chart => { chart.hidden = chart.dataset.chart !== platform; });
    }
    document.querySelectorAll('button[data-platform]').forEach(btn => btn.addEventListener('click', () => setPlatform(btn.dataset.platform)));
  </script>
</body>
</html>
"@

[System.IO.File]::WriteAllText($indexPath, $html, [System.Text.UTF8Encoding]::new($true))
[System.IO.File]::WriteAllText($dashboardPath, $html, [System.Text.UTF8Encoding]::new($true))
Write-Host "Wrote $indexPath"
Write-Host "Wrote $dashboardPath"
