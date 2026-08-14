$ErrorActionPreference = 'Stop'

$SummaryPath = '.\review_summary.json'
$ReviewsPath = '.\negative_reviews.json'
$ReportPath = '.\reports\2026-07-09-biweekly-review-analysis.html'
$ReportDate = '2026-07-09'
$Period = '双周周会'
$ReportTitle = 'THD & Lowes Top 10 / 核心新品差评分析'
$SourceNote = 'Bazaarvoice 公开 API + listing 清单'
$ComparisonPath = $null
if ($args.Count -gt 0) {
  $parsed = @{}
  for ($i = 0; $i -lt $args.Count; $i += 2) { $parsed[[string]$args[$i]] = [string]$args[$i + 1] }
  if ($parsed.ContainsKey('-SummaryPath')) { $SummaryPath = $parsed['-SummaryPath'] }
  if ($parsed.ContainsKey('-ReviewsPath')) { $ReviewsPath = $parsed['-ReviewsPath'] }
  if ($parsed.ContainsKey('-ReportPath')) { $ReportPath = $parsed['-ReportPath'] }
  if ($parsed.ContainsKey('-ReportDate')) { $ReportDate = $parsed['-ReportDate'] }
  if ($parsed.ContainsKey('-Period')) { $Period = $parsed['-Period'] }
  if ($parsed.ContainsKey('-ReportTitle')) { $ReportTitle = $parsed['-ReportTitle'] }
  if ($parsed.ContainsKey('-SourceNote')) { $SourceNote = $parsed['-SourceNote'] }
  if ($parsed.ContainsKey('-ComparisonPath')) { $ComparisonPath = $parsed['-ComparisonPath'] }
}

function ProductLine([string]$category) {
  switch -Regex ($category) {
    '^String Trimmer' { return '打草机' }
    '^Lawn Mower' { return '手推割草机' }
    '^Robot' { return '智能割草机' }
    '^Leaf Blower' { return '吹叶机' }
    '^Pole Saws?' { return '高枝锯' }
    '^Garden Tiller' { return '松土机' }
    default { return $category }
  }
}

$summary = @(Get-Content -LiteralPath $SummaryPath -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$negative = @(Get-Content -LiteralPath $ReviewsPath -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$comparison = if ($ComparisonPath -and (Test-Path -LiteralPath $ComparisonPath)) {
  Get-Content -LiteralPath $ComparisonPath -Encoding UTF8 -Raw | ConvertFrom-Json
} else {
  [pscustomobject]@{ currentReportDate = $ReportDate; priorReportDate = $null; comparisonScope = 'NOT_AVAILABLE'; platforms = @(); totals = $null }
}

# Only readable 1-3 star reviews may contribute to reason hits.
$readable = @($negative | Where-Object {
  !([string]::IsNullOrWhiteSpace([string]$_.title)) -or
  !([string]::IsNullOrWhiteSpace([string]$_.text))
})

$hitMap = @{}
foreach ($review in $readable) {
  if ([string]::IsNullOrWhiteSpace([string]$review.theme)) { continue }
  $key = '{0}|{1}|{2}' -f $review.platform, $review.sku, $review.theme
  if (-not $hitMap.ContainsKey($key)) { $hitMap[$key] = 0 }
  $hitMap[$key]++
}

$hitRows = @($hitMap.GetEnumerator() | ForEach-Object {
  $parts = $_.Key.Split('|', 3)
  [pscustomobject]@{
    platform = $parts[0]
    sku = $parts[1]
    theme = $parts[2]
    count = [int]$_.Value
  }
})

$itemRows = @($summary | ForEach-Object {
  $available = if ($null -ne $_.dataAvailable) { [bool]$_.dataAvailable } else { $null -ne $_.totalReviews }
  $lowStar = if ($available) { [int]$_.rating1 + [int]$_.rating2 + [int]$_.rating3 } else { $null }
  $total = if ($available) { [int]$_.totalReviews } else { $null }
  $platform = [string]$_.platform
  $sku = [string]$_.sku
  $skuHits = @($hitRows | Where-Object { $_.platform -eq $platform -and $_.sku -eq $sku } | Sort-Object @{ Expression = 'count'; Descending = $true }, @{ Expression = 'theme'; Descending = $false })
  [pscustomobject]@{
    platform = $platform
    sku = $sku
    brand = [string]$_.brand
    category = [string]$_.category
    productLine = ProductLine ([string]$_.category)
    productName = [string]$_.productName
    url = [string]$_.url
    totalReviews = $total
    avgRating = if ($available) { [double]$_.avgRating } else { $null }
    rating1 = if ($available) { [int]$_.rating1 } else { $null }
    rating2 = if ($available) { [int]$_.rating2 } else { $null }
    rating3 = if ($available) { [int]$_.rating3 } else { $null }
    lowStarReviews = $lowStar
    lowStarRate = if ($available -and $total -gt 0) { $lowStar / $total } elseif ($available) { 0 } else { $null }
    strongNegativeReviews = if ($available) { [int]$_.negativeReviews } else { $null }
    readableLowStarReviews = [int](($skuHits | Measure-Object -Property count -Sum).Sum)
    themeHits = @($skuHits | Select-Object -First 4)
    urgency = [string]$_.urgency
    actionItems = @($_.actionItems)
    reviewPlan = [string]$_.reviewPlan
    coreNew = [bool]$_.coreNew
    qaPassed = if ($null -ne $_.qaPassed) { [bool]$_.qaPassed } else { ($_.ratingCheck -eq 'OK' -and $_.endpointCheck -eq 'OK' -and $_.textCheck -eq 'OK') }
    sourceSystem = [string]$_.sourceSystem
    dataAvailable = $available
    availabilityStatus = [string]$_.availabilityStatus
  }
})

$meta = [pscustomobject]@{
  reportDate = $ReportDate
  period = $Period
  generatedAt = Get-Date -Format 'yyyy-MM-dd HH:mm'
  platforms = @($summary | Select-Object -ExpandProperty platform -Unique)
  reportTitle = $ReportTitle
  sourceNote = $SourceNote
}

$itemsJson = ConvertTo-Json -InputObject @($itemRows) -Depth 8 -Compress
$hitsJson = ConvertTo-Json -InputObject @($hitRows) -Depth 5 -Compress
$metaJson = ConvertTo-Json -InputObject $meta -Depth 4 -Compress
$comparisonJson = ConvertTo-Json -InputObject $comparison -Depth 8 -Compress

$template = @'
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>__REPORT_TITLE__</title>
  <style>
    :root{--ink:#17212b;--muted:#66737f;--line:#dbe3e8;--panel:#fff;--bg:#f3f6f5;--dark:#25313a;--orange:#d8663f;--orange-soft:#fff1eb;--teal:#28715f;--teal-soft:#edf6f2;--blue:#315f8c;--blue-soft:#edf3f9;--gold:#a66a12;--gold-soft:#fff6df;--red:#a83f2c}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--ink);font-family:Arial,"Microsoft YaHei",sans-serif;letter-spacing:0}button,select{font:inherit}
    header{background:#fff;border-bottom:1px solid var(--line);padding:26px clamp(20px,3vw,48px) 20px}.head{max-width:1560px;margin:auto}.titlebar{display:flex;justify-content:space-between;gap:28px;align-items:flex-end}.eyebrow{font-size:12px;font-weight:800;color:var(--orange);margin-bottom:8px}.archive{color:var(--blue);font-size:13px;text-decoration:none}.archive:hover{text-decoration:underline}h1{font-size:28px;margin:0 0 8px;overflow-wrap:anywhere}.sub{color:var(--muted);font-size:13px;line-height:1.65;overflow-wrap:anywhere}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-top:18px}.tab{border:1px solid #cbd6dd;background:#fff;border-radius:6px;padding:9px 15px;font-weight:800;cursor:pointer}.tab:hover{border-color:#83919b}.tab.active{background:var(--dark);border-color:var(--dark);color:#fff}.tab.add{border-style:dashed;color:#74818b;cursor:default}
    main{max-width:1640px;margin:auto;padding:22px clamp(20px,3vw,48px) 52px;min-width:0}.card{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px;margin-bottom:18px}.kpis{display:grid;grid-template-columns:1.2fr 1fr 1fr 1.1fr .85fr;gap:12px;margin-bottom:18px}.kpi-card{min-height:132px;margin:0}.kpi-card.hero{border-top:4px solid var(--orange);background:#fffaf8}.label{color:var(--muted);font-size:12px;font-weight:800}.kpi{font-size:30px;font-weight:900;margin:9px 0 4px;line-height:1.12;overflow-wrap:anywhere}.kpi.text{font-size:22px}.low{color:var(--red);font-weight:900}.hint{color:var(--muted);font-size:12px;line-height:1.55}.logic{display:grid;grid-template-columns:140px 1fr;gap:18px;align-items:center;border-left:4px solid var(--blue)}.logic strong{font-size:18px}.logic p{margin:0;color:#40505a;line-height:1.65;font-size:14px}
    h2{font-size:20px;margin:0}.section-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:14px}.section-head .hint{margin-top:4px}.two-col{display:grid;grid-template-columns:minmax(420px,.88fr) minmax(540px,1.12fr);gap:18px}.two-col>.card{margin-bottom:18px}.bar-row{display:grid;grid-template-columns:minmax(130px,190px) 1fr 112px;gap:12px;align-items:center;margin:11px 0}.bar-label{font-size:13px}.track{height:14px;background:#edf1f3;border-radius:3px;overflow:hidden}.fill{height:100%;background:var(--orange)}.bar-value{text-align:right;font-size:12px;color:var(--muted)}.bar-value b{color:var(--ink);font-size:14px;margin-right:5px}
    .sort-modes{display:flex;gap:4px;background:#f1f4f5;padding:3px;border-radius:6px}.mode{border:0;background:transparent;border-radius:4px;padding:6px 9px;font-size:12px;color:var(--muted);cursor:pointer}.mode.active{background:#fff;color:var(--ink);font-weight:800;box-shadow:0 1px 3px rgba(22,33,43,.12)}.sku-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.sku-card{border:1px solid #e0e6ea;border-radius:6px;padding:12px;background:#fbfcfc}.sku-top,.sku-metrics{display:flex;justify-content:space-between;gap:10px;align-items:center}.sku-name{font-weight:900}.platform{font-size:11px;color:var(--muted);margin-right:6px}.rank{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--orange-soft);color:var(--red);font-weight:900;margin-right:6px}.sample{font-size:10px;color:var(--gold);background:var(--gold-soft);padding:3px 5px;border-radius:4px}.sku-metrics{font-size:12px;color:var(--muted);margin:9px 0}.sku-metrics b{font-size:15px;color:var(--ink)}.chips{display:flex;gap:5px;flex-wrap:wrap}.chip{font-size:11px;background:var(--blue-soft);color:#294f72;border-radius:4px;padding:4px 6px}.chip b{margin-left:3px}.empty{color:var(--muted);padding:18px 0;text-align:center}
    .tablewrap{overflow:auto;border:1px solid var(--line);border-radius:6px;max-height:620px}table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}th,td{border-bottom:1px solid #e1e8ed;padding:10px 8px;text-align:left;vertical-align:top}th{background:#f8fafb;color:#33424c;position:sticky;top:0;z-index:1;white-space:nowrap}tbody tr:hover{background:#fbfcfd}th.sort{cursor:pointer}th.sort:after{content:" ↕";color:#82909b;font-weight:400}.line-tag{display:inline-block;background:var(--teal-soft);color:#216653;border-radius:4px;padding:4px 7px;font-weight:800}.theme-list{display:flex;gap:5px;flex-wrap:wrap}.theme-list span{background:#f1f4f5;border-radius:4px;padding:3px 5px;white-space:nowrap}.pill{display:inline-block;border-radius:4px;padding:4px 7px;background:#edf5f2;color:#216653;font-weight:800;white-space:nowrap}.p0{background:var(--orange-soft);color:var(--red)}.p1{background:var(--gold-soft);color:#79520d}.p2{background:var(--blue-soft);color:var(--blue)}
    .priority-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.priority-table td:first-child{font-weight:800}.decision{color:#40505a;line-height:1.5}.actions{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.action{border-top:3px solid var(--teal);background:#f9fbfa;border-radius:6px;padding:12px;border-left:1px solid #e2e9e6;border-right:1px solid #e2e9e6;border-bottom:1px solid #e2e9e6}.action b{display:block;margin-bottom:6px;font-size:13px}.source{font-size:12px;color:var(--muted);line-height:1.7}.source p{margin:8px 0 0}.section-anchor{scroll-margin-top:12px}a.sku-link{color:var(--blue);font-weight:800;text-decoration:none}a.sku-link:hover{text-decoration:underline}.compare-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:14px}.compare-metric{border-left:3px solid var(--blue);background:#f8fafb;padding:11px 12px;border-radius:4px}.compare-metric b{display:block;font-size:20px;margin:4px 0}.delta-up{color:var(--red)}.delta-down{color:var(--teal)}.unavailable{display:inline-block;background:#f1f3f4;color:#5f6b73;border:1px solid #d8dfe3;border-radius:4px;padding:3px 6px;font-weight:800;font-size:11px}
    @media(max-width:1180px){.kpis{grid-template-columns:repeat(3,1fr)}.two-col,.priority-grid{grid-template-columns:1fr}.actions,.compare-grid{grid-template-columns:repeat(3,1fr)}}
    @media(max-width:760px){header,main{padding-left:16px;padding-right:16px}.titlebar{display:block}.titlebar>.sub{margin-top:10px}.kpis{grid-template-columns:1fr}.kpi-card{min-height:108px}.logic{grid-template-columns:1fr}.sku-grid,.actions{grid-template-columns:1fr}.compare-grid{grid-template-columns:1fr 1fr}.bar-row{grid-template-columns:100px minmax(0,1fr) 68px;gap:8px}.section-head{display:block}.sort-modes{margin-top:10px;width:max-content;max-width:100%}.tab.add{display:none}h1{font-size:25px}.kpi{font-size:27px}}
  </style>
</head>
<body>
<header><div class="head">
  <div class="titlebar"><div><div class="eyebrow" id="periodLabel"></div><h1>__REPORT_TITLE__</h1><div class="sub">以 SKU 为分析主轴：先看低分规模，再看问题命中和产品线共性，最后形成可执行 To Do。</div></div><div class="sub"><a class="archive" href="../">返回归档首页</a><br>数据源：__SOURCE_NOTE__<br>评分包含 ratings-only；原因分析仅覆盖可读文本</div></div>
  <div class="tabs" id="platformTabs"></div>
</div></header>
<main>
  <section class="kpis" id="kpiStrip"></section>
  <section class="card logic"><strong>本页风险判断逻辑</strong><p><b>量</b>看问题命中次数，<b>率</b>看 1–3 星占页面 Review 的比例，<b>广度</b>看问题影响多少 SKU / 产品线。高严重度产品问题优先修根因，导评与测评只用于验证修复后的真实体验。</p></section>

  <section class="card section-anchor"><div class="section-head"><div><h2>较上期变化</h2><div class="hint" id="comparisonHint"></div></div></div><div class="compare-grid" id="comparisonKpis"></div><div class="tablewrap"><table><thead><tr><th>平台</th><th>可比 SKU</th><th>页面 Review</th><th>Review 变化</th><th>1–3 星</th><th>低分变化</th><th>低分率变化</th><th>新增可读低星</th><th>当前不可用</th></tr></thead><tbody id="comparisonBody"></tbody></table></div></section>

  <section class="two-col section-anchor">
    <div class="card"><div class="section-head"><div><h2>共性差评原因命中</h2><div class="hint">按可读 1–3 星评论的主标签统计；当前每条评论只计 1 个核心问题。</div></div></div><div id="themeBars"></div></div>
    <div class="card"><div class="section-head"><div><h2>SKU 核心问题命中</h2><div class="hint">同时显示低分规模、低分率和单 SKU 的高频问题次数。</div></div><div class="sort-modes"><button class="mode active" data-sku-sort="volume">按低分数</button><button class="mode" data-sku-sort="rate">按低分率</button><button class="mode" data-sku-sort="hits">按问题命中</button></div></div><div class="sku-grid" id="skuCards"></div></div>
  </section>

  <section class="card section-anchor"><div class="section-head"><div><h2>按产品线分析</h2><div class="hint">把 SKU 聚合成产品线，定位跨型号的结构性问题；不引入销售与退款数据。</div></div></div><div class="tablewrap"><table><thead><tr><th>产品线</th><th>SKU 数</th><th>页面 Review</th><th>1–3 星低分</th><th>低分率</th><th>可读文本命中</th><th>主要问题</th></tr></thead><tbody id="productLineBody"></tbody></table></div></section>

  <section class="card section-anchor"><div class="section-head"><div><h2>问题优先级分析</h2><div class="hint">优先级综合问题严重度、命中次数和受影响 SKU 广度；不以单纯差评率替代判断。</div></div></div><div class="tablewrap"><table class="priority-table"><thead><tr><th>问题</th><th>优先级</th><th>命中次数</th><th>影响 SKU</th><th>覆盖平台</th><th>处理判断</th></tr></thead><tbody id="priorityBody"></tbody></table></div></section>

  <section class="card"><div class="section-head"><div><h2>通用处理方法</h2><div class="hint">先给所有平台共用的闭环方法，再进入具体 SKU。</div></div></div><div class="actions">
    <div class="action"><b>1. 产品根因闭环</b><span class="hint">启动/动力、耐久、电池和割草效果进入退货件拆解、复测与版本验证。</span></div>
    <div class="action"><b>2. 页面预期重写</b><span class="hint">明确适用场景、续航、启动步骤、安装门槛、限制条件和售后入口。</span></div>
    <div class="action"><b>3. 低星 48 小时闭环</b><span class="hint">P0/P1 评论逐条分配 owner，记录响应、补件/换新/教程和解决状态。</span></div>
    <div class="action"><b>4. 真实测评验证</b><span class="hint">P0 老品 20–30 条，P1 10–15 条；核心新品 10–15 条且至少 3 条图/视频。</span></div>
    <div class="action"><b>5. 新品 30 天护航</b><span class="hint">每周跟进低星、问答和页面反馈；先建样本，再判断比例是否稳定。</span></div>
  </div></section>

  <section class="card section-anchor"><div class="section-head"><div><h2>SKU To Do 明细</h2><div class="hint">处理方案与导评/测评分开，避免用补评论替代产品修复。</div></div></div><div class="tablewrap"><table><thead><tr><th>优先级</th><th>平台 / SKU</th><th>1–3 星</th><th>核心问题命中</th><th>处理方案</th><th>导评 / 测评</th></tr></thead><tbody id="todoBody"></tbody></table></div></section>

  <section class="card section-anchor"><div class="section-head"><div><h2>Listing 风险排名</h2><div class="hint">点击表头排序；保留页面 Review、星级分布和问题命中，便于复核。</div></div></div><div class="tablewrap"><table id="riskTable"><thead><tr><th class="sort" data-key="platform" data-type="text">平台</th><th class="sort" data-key="sku" data-type="text">SKU</th><th class="sort" data-key="totalReviews" data-type="num">页面 Review</th><th class="sort" data-key="avgRating" data-type="num">评分</th><th class="sort" data-key="rating1" data-type="num">1星</th><th class="sort" data-key="rating2" data-type="num">2星</th><th class="sort" data-key="rating3" data-type="num">3星</th><th class="sort" data-key="lowStarRate" data-type="num">1–3星率</th><th class="sort" data-key="readableLowStarReviews" data-type="num">文本命中</th><th>Top 问题</th></tr></thead><tbody id="riskBody"></tbody></table></div></section>

  <section class="card source"><h2>数据口径与 QA</h2><p id="qaNote"></p></section>
</main>
<script>
const ITEMS=__ITEMS_JSON__;
const HITS=__HITS_JSON__;
const META=__META_JSON__;
const COMPARISON=__COMPARISON_JSON__;
const nf=new Intl.NumberFormat('zh-CN');
let activePlatform='全部',skuSort='volume',tableSort={key:'lowStarRate',dir:'desc'};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>`${(Number(v||0)*100).toFixed(1)}%`;
const sum=(arr,key)=>arr.reduce((n,x)=>n+Number(x[key]||0),0);
const filteredItems=()=>activePlatform==='全部'?ITEMS:ITEMS.filter(x=>x.platform===activePlatform);
const availableItems=()=>filteredItems().filter(x=>x.dataAvailable);
const filteredHits=()=>{const keys=new Set(availableItems().map(x=>`${x.platform}|${x.sku}`));return HITS.filter(x=>keys.has(`${x.platform}|${x.sku}`))};
const fmt=v=>v===null||v===undefined?'不可用':nf.format(v);
const signed=v=>v===null||v===undefined?'—':`${v>0?'+':''}${nf.format(v)}`;
const pp=v=>v===null||v===undefined?'—':`${v>0?'+':''}${(v*100).toFixed(1)}pp`;
const deltaClass=v=>Number(v)>0?'delta-up':Number(v)<0?'delta-down':'';
function aggregateThemes(rows){const map=new Map();rows.forEach(x=>{if(!map.has(x.theme))map.set(x.theme,{theme:x.theme,count:0,skus:new Set(),platforms:new Set()});const r=map.get(x.theme);r.count+=x.count;r.skus.add(`${x.platform}|${x.sku}`);r.platforms.add(x.platform)});return [...map.values()].sort((a,b)=>b.count-a.count||a.theme.localeCompare(b.theme));}
function topThemeHtml(rows,limit=3){return rows.slice(0,limit).map(x=>`<span>${esc(x.theme)} <b>${nf.format(x.count)}</b></span>`).join('')||'<span>暂无可归因文本</span>';}
function renderTabs(){const tabs=['全部',...META.platforms];document.getElementById('platformTabs').innerHTML=tabs.map(p=>`<button class="tab ${p===activePlatform?'active':''}" data-platform="${esc(p)}">${esc(p)}</button>`).join('')+'<button class="tab add" title="后续平台会自动加入筛选">+ 新增平台</button>';document.querySelectorAll('[data-platform]').forEach(b=>b.onclick=()=>{activePlatform=b.dataset.platform;renderAll()});}
function renderKpis(){const items=filteredItems(),available=availableItems(),hits=filteredHits(),total=sum(available,'totalReviews'),low=sum(available,'lowStarReviews'),readable=sum(hits,'count'),themes=aggregateThemes(hits),qa=available.filter(x=>x.qaPassed).length,unavailable=items.length-available.length,top=themes[0];document.getElementById('kpiStrip').innerHTML=`
  <div class="card kpi-card hero"><div class="label">1–3 星低分反馈</div><div class="kpi low">${nf.format(low)}</div><div class="hint">占页面 Review ${pct(total?low/total:0)}，先看问题规模再看比例。</div></div>
  <div class="card kpi-card"><div class="label">页面 Review</div><div class="kpi">${nf.format(total)}</div><div class="hint">平台公开评分统计，包含 ratings-only。</div></div>
  <div class="card kpi-card"><div class="label">可分析低分文本</div><div class="kpi">${nf.format(readable)}</div><div class="hint">覆盖 1–3 星 ${pct(low?readable/low:0)}；仅这些评论进入原因命中。</div></div>
  <div class="card kpi-card"><div class="label">最大共性问题</div><div class="kpi text">${top?esc(top.theme):'暂无'}</div><div class="hint">${top?`${nf.format(top.count)} 次，影响 ${top.skus.size} 个 SKU`:'当前筛选无可读低分文本'}</div></div>
  <div class="card kpi-card"><div class="label">交叉验证</div><div class="kpi">${qa}/${available.length}</div><div class="hint">有效页面内部一致；当前不可用 ${unavailable} 个。</div></div>`;}
function renderComparison(){const rows=(COMPARISON.platforms||[]).filter(x=>activePlatform==='全部'||x.platform===activePlatform),t=activePlatform==='全部'?COMPARISON.totals:rows[0];document.getElementById('comparisonHint').textContent=COMPARISON.priorReportDate?`与 ${COMPARISON.priorReportDate} 比较；仅纳入两期均可用的同一 SKU。`:'暂无可比较的历史报告';document.getElementById('comparisonKpis').innerHTML=t?`<div class="compare-metric"><span class="label">可比 SKU</span><b>${fmt(t.comparableListings)}</b><span class="hint">同口径范围</span></div><div class="compare-metric"><span class="label">Review 变化</span><b class="${deltaClass(t.totalReviewDelta)}">${signed(t.totalReviewDelta)}</b><span class="hint">${fmt(t.priorTotalReviews)} → ${fmt(t.currentTotalReviews)}</span></div><div class="compare-metric"><span class="label">1–3 星变化</span><b class="${deltaClass(t.lowStarDelta)}">${signed(t.lowStarDelta)}</b><span class="hint">${fmt(t.priorLowStarReviews)} → ${fmt(t.currentLowStarReviews)}</span></div><div class="compare-metric"><span class="label">低分率变化</span><b class="${deltaClass(t.lowStarRateDelta)}">${pp(t.lowStarRateDelta)}</b><span class="hint">同口径比例变化</span></div><div class="compare-metric"><span class="label">新增可读低星</span><b>${fmt(t.newReadableLowStarReviews)}</b><span class="hint">报告日期后新增文本</span></div>`:'<div class="empty">暂无跨期数据</div>';document.getElementById('comparisonBody').innerHTML=rows.map(x=>`<tr><td><b>${esc(x.platform)}</b></td><td>${x.comparableListings}</td><td>${fmt(x.priorTotalReviews)} → ${fmt(x.currentTotalReviews)}</td><td class="${deltaClass(x.totalReviewDelta)}">${signed(x.totalReviewDelta)}</td><td>${fmt(x.priorLowStarReviews)} → ${fmt(x.currentLowStarReviews)}</td><td class="${deltaClass(x.lowStarDelta)}">${signed(x.lowStarDelta)}</td><td class="${deltaClass(x.lowStarRateDelta)}">${pp(x.lowStarRateDelta)}</td><td>${fmt(x.newReadableLowStarReviews)}</td><td>${x.currentUnavailable||0}</td></tr>`).join('')||'<tr><td colspan="9">暂无跨期数据</td></tr>';}
function renderThemes(){const rows=aggregateThemes(filteredHits()).slice(0,10),max=Math.max(1,...rows.map(x=>x.count));document.getElementById('themeBars').innerHTML=rows.length?rows.map(x=>`<div class="bar-row"><div class="bar-label">${esc(x.theme)}</div><div class="track"><div class="fill" style="width:${(x.count/max*100).toFixed(1)}%"></div></div><div class="bar-value"><b>${nf.format(x.count)}</b>${x.skus.size} SKU</div></div>`).join(''):'<div class="empty">当前筛选无可读低分文本</div>';}
function skuHitRows(item){return filteredHits().filter(x=>x.platform===item.platform&&x.sku===item.sku).sort((a,b)=>b.count-a.count);}
function renderSkuCards(){let rows=availableItems().filter(x=>x.lowStarReviews>0);rows.sort((a,b)=>skuSort==='rate'?b.lowStarRate-a.lowStarRate||b.lowStarReviews-a.lowStarReviews:skuSort==='hits'?b.readableLowStarReviews-a.readableLowStarReviews||b.lowStarReviews-a.lowStarReviews:b.lowStarReviews-a.lowStarReviews||b.lowStarRate-a.lowStarRate);rows=rows.slice(0,8);document.getElementById('skuCards').innerHTML=rows.length?rows.map((x,i)=>{const themes=skuHitRows(x);return `<div class="sku-card"><div class="sku-top"><div><span class="rank">${i+1}</span><span class="platform">${esc(x.platform)}</span><span class="sku-name">${esc(x.sku)}</span></div>${x.totalReviews<10?'<span class="sample">小样本</span>':''}</div><div class="sku-metrics"><span>1–3 星 <b>${nf.format(x.lowStarReviews)}</b> / ${nf.format(x.totalReviews)}</span><span>低分率 <b>${pct(x.lowStarRate)}</b></span></div><div class="chips">${themes.slice(0,4).map(t=>`<span class="chip">${esc(t.theme)}<b>${t.count}</b></span>`).join('')||'<span class="chip">暂无文本命中</span>'}</div></div>`}).join(''):'<div class="empty">当前筛选无低分 SKU</div>';document.querySelectorAll('[data-sku-sort]').forEach(b=>b.classList.toggle('active',b.dataset.skuSort===skuSort));}
function renderProductLines(){const groups=new Map();filteredItems().forEach(x=>{if(!groups.has(x.productLine))groups.set(x.productLine,[]);groups.get(x.productLine).push(x)});const rows=[...groups.entries()].map(([line,items])=>{const valid=items.filter(x=>x.dataAvailable),keys=new Set(valid.map(x=>`${x.platform}|${x.sku}`)),hits=filteredHits().filter(h=>keys.has(`${h.platform}|${h.sku}`)),total=sum(valid,'totalReviews'),low=sum(valid,'lowStarReviews');return{line,items,valid,total,low,rate:total?low/total:0,hits:sum(hits,'count'),themes:aggregateThemes(hits)}}).sort((a,b)=>b.low-a.low||b.total-a.total);document.getElementById('productLineBody').innerHTML=rows.map(r=>`<tr><td><span class="line-tag">${esc(r.line)}</span></td><td>${r.valid.length}/${r.items.length}</td><td>${nf.format(r.total)}</td><td class="low">${nf.format(r.low)}</td><td class="low">${pct(r.rate)}</td><td>${nf.format(r.hits)}</td><td><div class="theme-list">${topThemeHtml(r.themes)}</div></td></tr>`).join('');}
function priorityFor(x){const severe=['启动/动力故障','质量/耐久'];if(severe.includes(x.theme)&&x.count>=5)return'P0';if(x.count>=10||x.skus.size>=3)return'P1';return'P2';}
function decisionFor(x,p){if(p==='P0')return'高严重度产品问题：进入退货件拆解、工程复测和版本关闭。';if(p==='P1')return x.skus.size>=3?'跨 SKU 共性问题：统一页面预期、SOP 与专项验证。':'命中量较高：指定 owner，按 SKU 聚焦修复并跟踪新评论。';return'当前样本有限：保留监控，补充样本后再升级优先级。';}
function renderPriority(){const rows=aggregateThemes(filteredHits()).map(x=>({...x,priority:priorityFor(x)})).sort((a,b)=>a.priority.localeCompare(b.priority)||b.count-a.count);document.getElementById('priorityBody').innerHTML=rows.map(x=>`<tr><td>${esc(x.theme)}</td><td><span class="pill ${x.priority.toLowerCase()}">${x.priority}</span></td><td>${nf.format(x.count)}</td><td>${x.skus.size}</td><td>${x.platforms.size}</td><td class="decision">${decisionFor(x,x.priority)}</td></tr>`).join('');}
function urgencyClass(v){return /^P0/.test(v)?'p0':/^P1/.test(v)?'p1':'p2'}
function actionHtml(actions){return (actions||[]).slice(0,3).map(x=>esc(x)).join('<br>')||'逐条复核低星原文并分配 owner。'}
function renderTodo(){const rows=filteredItems().filter(x=>!x.dataAvailable||/^P0|^P1/.test(x.urgency)||/建样本/.test(x.urgency)).sort((a,b)=>urgencyClass(a.urgency).localeCompare(urgencyClass(b.urgency))||Number(b.lowStarReviews||0)-Number(a.lowStarReviews||0));document.getElementById('todoBody').innerHTML=rows.map(x=>`<tr><td><span class="pill ${urgencyClass(x.urgency)}">${esc(x.urgency)}</span></td><td><b>${esc(x.platform)}</b><br>${esc(x.sku)}${x.coreNew?'<br><span class="sample">核心新品</span>':''}</td><td class="low">${x.dataAvailable?`${nf.format(x.lowStarReviews)} / ${nf.format(x.totalReviews)}<br><span class="hint">${pct(x.lowStarRate)}</span>`:'<span class="unavailable">当前不可用</span>'}</td><td><div class="theme-list">${x.dataAvailable?topThemeHtml(skuHitRows(x),4):'<span>Listing 页面失效</span>'}</div></td><td>${actionHtml(x.actionItems)}</td><td>${esc(x.reviewPlan)}</td></tr>`).join('');}
function renderRisk(){const rows=[...filteredItems()].sort((a,b)=>{if(a.dataAvailable!==b.dataAvailable)return a.dataAvailable?-1:1;let av=a[tableSort.key],bv=b[tableSort.key];if(tableSort.key==='platform'||tableSort.key==='sku'){av=String(av);bv=String(bv);return tableSort.dir==='asc'?av.localeCompare(bv):bv.localeCompare(av)}return tableSort.dir==='asc'?Number(av)-Number(bv):Number(bv)-Number(av)});document.getElementById('riskBody').innerHTML=rows.map(x=>`<tr><td>${esc(x.platform)}</td><td><a class="sku-link" href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.sku)}</a></td>${x.dataAvailable?`<td>${nf.format(x.totalReviews)}</td><td>${x.avgRating.toFixed(2)}</td><td>${x.rating1}</td><td>${x.rating2}</td><td>${x.rating3}</td><td class="low">${pct(x.lowStarRate)}</td><td>${x.readableLowStarReviews}</td><td><div class="theme-list">${topThemeHtml(skuHitRows(x),3)}</div></td>`:'<td colspan="8"><span class="unavailable">当前页面不可用</span> <span class="hint">Listing 失效，未纳入总量与风险排序</span></td>'}</tr>`).join('');}
function renderQa(){const items=filteredItems(),available=availableItems(),low=sum(available,'lowStarReviews'),hits=sum(filteredHits(),'count'),passed=available.filter(x=>x.qaPassed).length,unavailable=items.length-available.length;document.getElementById('qaNote').innerHTML=`1–3 星低分反馈 = 1 星 + 2 星 + 3 星；页面 Review 与平均评分来自平台公开统计，包含 ratings-only。THD/Lowes 使用 Bazaarvoice 统计与评论端点交叉验证；Walmart 以商品页星级分布为主口径、公开 Bazaarvoice 为文本辅助源。原因命中仅使用标题或正文可读的 1–3 星评论，当前采用“每条评论 1 个主标签”的保守口径：${nf.format(hits)} 条可分析文本 / ${nf.format(low)} 条低分反馈。当前筛选 ${passed}/${available.length} 个有效 SKU 通过内部一致性校验，${unavailable} 个当前不可用 SKU 未计入总量。报告日期：${esc(META.reportDate)}；页面版本更新时间：${esc(META.generatedAt)}。`;}
function renderAll(){renderTabs();renderKpis();renderComparison();renderThemes();renderSkuCards();renderProductLines();renderPriority();renderTodo();renderRisk();renderQa();}
document.getElementById('periodLabel').textContent=`${META.reportDate} · ${META.period}`;
document.querySelectorAll('[data-sku-sort]').forEach(b=>b.onclick=()=>{skuSort=b.dataset.skuSort;renderSkuCards()});
document.querySelectorAll('#riskTable th.sort').forEach(th=>th.onclick=()=>{const key=th.dataset.key;tableSort={key,dir:tableSort.key===key&&tableSort.dir==='desc'?'asc':'desc'};renderRisk()});
renderAll();
</script>
</body>
</html>
'@

$html = $template.Replace('__ITEMS_JSON__', $itemsJson).Replace('__HITS_JSON__', $hitsJson).Replace('__META_JSON__', $metaJson).Replace('__COMPARISON_JSON__', $comparisonJson).Replace('__REPORT_TITLE__', [System.Net.WebUtility]::HtmlEncode($ReportTitle)).Replace('__SOURCE_NOTE__', [System.Net.WebUtility]::HtmlEncode($SourceNote))
$resolvedReportPath = if ([System.IO.Path]::IsPathRooted($ReportPath)) { $ReportPath } else { Join-Path (Get-Location) $ReportPath }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedReportPath) | Out-Null
[System.IO.File]::WriteAllText($resolvedReportPath, $html, [System.Text.UTF8Encoding]::new($true))
Write-Host "Wrote full biweekly report: $resolvedReportPath ($($html.Length) chars)"
