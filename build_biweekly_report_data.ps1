$ErrorActionPreference = 'Stop'

$RunDir = Join-Path (Get-Location) 'runs\2026-07-23-biweekly-review-analysis'
if ($args.Count -gt 0) {
  for ($i = 0; $i -lt $args.Count; $i += 2) {
    if ([string]$args[$i] -eq '-RunDir') { $RunDir = [string]$args[$i + 1] }
  }
}

function Get-Theme([string]$Text, [string]$Category) {
  $t = ($Text + ' ' + $Category).ToLowerInvariant()
  if ($t -match 'customer service|support|email|tracking|inventory|shipping|delivery|delivered|never came|not received|scam|reply|warranty|parts unavailable') { return '客服/履约' }
  if ($t -match '\bapp\b|gps|rtk|boundary|map|connect|bluetooth|wifi|wi-fi|signal|navigation|initialize|initializing') { return 'APP/导航/连接' }
  if ($t -match 'battery|batteries|charge|charger|charging|runtime|volt|\bah\b|power pack') { return '电池/充电' }
  if ($t -match 'start|started|pull|string kept|engine|motor|smok|fire|won''t run|would not run|stopped|stall|carb|fuel|gas|oil|no power|low power|not much power') { return '启动/动力故障' }
  if ($t -match 'defective|broke|broken|return|returned|quit|failed|dead|replace|warranty|quality|cheaply made|missing piece|missing screw') { return '质量/耐久' }
  if ($t -match 'heavy|weight|balance|vibration|wrist|handle|ergonomic|strap') { return '重量/人体工学' }
  if ($t -match 'cut|mow|trimming|weed|grass|blade|line|guard|string|brush|deck|height|advance|edger') { return '割草/修剪效果' }
  if ($t -match 'assemble|assembly|setup|install|manual|instruction') { return '安装/设置' }
  if ($t -match 'price|value|expectation|expected|money|cost') { return '价格/预期' }
  return '其他'
}

function Get-Urgency([int]$Total, [int]$Low, [double]$Rate, [bool]$CoreNew, [string[]]$Themes) {
  if ($Total -eq 0) { return 'P2 建样本' }
  if ($Total -lt 10) {
    if ($CoreNew -and $Low -ge 2) { return 'P0 新品护航' }
    if ($Low -gt 0) { return 'P1 样本不足' }
    return 'P2 建样本'
  }
  $severe = @($Themes | Where-Object { $_ -in @('启动/动力故障', '质量/耐久', '电池/充电') }).Count -gt 0
  if (($CoreNew -and $Low -gt 0 -and $Rate -ge 0.12) -or $Low -ge 30 -or ($Rate -ge 0.25 -and $Low -ge 5) -or ($severe -and $Low -ge 10)) { return 'P0 立即处理' }
  if ($Low -ge 5 -or $Rate -ge 0.12) { return 'P1 本周处理' }
  return 'P2 持续观察'
}

function Get-ReviewPlan([int]$Total, [int]$Low, [double]$Rate, [bool]$CoreNew) {
  if ($Total -eq 0) { return '先补 8-12 条真实测评，覆盖开箱、安装、连续使用和售后触点；有样本后再判断低分率。' }
  if ($Total -lt 10 -and -not $CoreNew) { return '当前样本不足：补 8-12 条真实测评，覆盖核心场景；达到稳定样本后再判断低分率。' }
  if ($CoreNew -and $Total -lt 10) { return '核心新品样本不足：优先补 10-15 条真实测评，至少 3 条带图/视频；同步跟进每条低星用户。' }
  if ($Low -ge 50 -or $Rate -ge 0.25) { return '完成根因修复后补 20-30 条真实测评验证；不得用导评替代产品整改。' }
  if ($Rate -ge 0.12) { return '完成重点修复后补 10-15 条真实测评，覆盖高频场景，并保留每周复盘。' }
  return '维持自然评价节奏，每月 5-8 条真实测评，重点监控新增低星。'
}

function Get-Actions([string[]]$Themes, [bool]$CoreNew) {
  $items = [System.Collections.Generic.List[string]]::new()
  if ($Themes -contains '启动/动力故障') { $items.Add('产品：复盘动力系统、开关与启动链路；增加负载和连续运行抽检。') }
  if ($Themes -contains '质量/耐久') { $items.Add('产品：建立退货件拆解清单，优先排查连接件、结构强度和早期失效。') }
  if ($Themes -contains '客服/履约') { $items.Add('服务：48 小时内回复低星评论；补齐补件、换新、保修和物流追踪 SOP。') }
  if ($Themes -contains '割草/修剪效果') { $items.Add('产品/内容：验证刀片、线轴与实际割草效果；页面明确草况、面积和使用限制。') }
  if ($Themes -contains '电池/充电') { $items.Add('产品：核查电池容量、续航和充电器故障率；页面明确实际工况续航。') }
  if ($Themes -contains 'APP/导航/连接') { $items.Add('软件：排查定位、地图边界与配网；补充 App 设置短视频和异常处理入口。') }
  if ($Themes -contains '重量/人体工学') { $items.Add('产品：评估重量、手柄平衡与震动；页面明确重量和适用人群。') }
  if ($Themes -contains '安装/设置') { $items.Add('内容：重写安装步骤和故障排查，补充关键节点图片与短视频。') }
  if ($items.Count -eq 0) { $items.Add('运营：逐条复核低星原文，确认个案、误用、物流或页面预期偏差。') }
  if ($CoreNew) { $items.Add('新品：建立每 7 天一次的低星闭环表，Owner 落到产品、客服和内容。') }
  return @($items)
}

$bvSummary = @(Get-Content -LiteralPath (Join-Path $RunDir 'review_summary_bv.json') -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$bvReviews = @(Get-Content -LiteralPath (Join-Path $RunDir 'low_star_reviews_bv.json') -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })
$walmart = @(Get-Content -LiteralPath (Join-Path $RunDir 'walmart_raw.json') -Encoding UTF8 -Raw | ConvertFrom-Json | ForEach-Object { $_ })

$reviewRows = [System.Collections.Generic.List[object]]::new()
foreach ($review in $bvReviews) { $reviewRows.Add($review) }
foreach ($item in $walmart) {
  foreach ($review in @($item.reviews)) {
    $reviewRows.Add([pscustomobject]@{
      platform = 'Walmart'; sku = $item.sku; brand = $item.brand; category = $item.category
      productId = $item.itemId; productName = $item.productName; url = $item.url
      rating = [int]$review.rating
      theme = Get-Theme (($review.title + ' ' + $review.text)) $item.category
      title = $review.title; text = $review.text; date = $review.date
      syndicated = -not [string]::IsNullOrWhiteSpace([string]$review.syndicationSource)
      sourceClient = if ($review.syndicationSource) { $review.syndicationSource } else { 'walmart' }
      verified = [bool]$review.verified
    })
  }
}

$summaries = [System.Collections.Generic.List[object]]::new()
foreach ($source in $bvSummary) {
  $low = [int]$source.rating1 + [int]$source.rating2 + [int]$source.rating3
  $rate = if ([int]$source.totalReviews -gt 0) { $low / [double]$source.totalReviews } else { 0 }
  $skuThemes = @($reviewRows | Where-Object { $_.platform -eq $source.platform -and $_.sku -eq $source.sku } | Group-Object theme | Sort-Object Count -Descending)
  $themeNames = @($skuThemes | Select-Object -First 3 -ExpandProperty Name)
  $source.urgency = Get-Urgency ([int]$source.totalReviews) $low $rate ([bool]$source.coreNew) $themeNames
  $source.reviewPlan = Get-ReviewPlan ([int]$source.totalReviews) $low $rate ([bool]$source.coreNew)
  $source.actionItems = @(Get-Actions $themeNames ([bool]$source.coreNew))
  $source | Add-Member -NotePropertyName sourceSystem -NotePropertyValue 'Bazaarvoice' -Force
  $source | Add-Member -NotePropertyName qaPassed -NotePropertyValue $true -Force
  $source | Add-Member -NotePropertyName dataAvailable -NotePropertyValue $true -Force
  $source | Add-Member -NotePropertyName availabilityStatus -NotePropertyValue 'AVAILABLE' -Force
  $summaries.Add($source)
}

foreach ($item in $walmart) {
  $stats = $item.stats
  $available = if ($null -ne $item.dataAvailable) { [bool]$item.dataAvailable } else { $true }
  $coreNew = ([string]$item.brand -eq 'SUNSEEKER') -or ([string]$item.category -match 'Robot')
  $skuRows = @($reviewRows | Where-Object { $_.platform -eq 'Walmart' -and $_.sku -eq $item.sku })
  $skuThemes = @($skuRows | Group-Object theme | Sort-Object Count -Descending)
  $themeNames = @($skuThemes | Select-Object -First 3 -ExpandProperty Name)
  $themeText = ($skuThemes | Select-Object -First 3 | ForEach-Object { "$($_.Name) $($_.Count)" }) -join ' / '
  $warnings = @($item.errors | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
  if (-not $available) {
    $summaries.Add([pscustomobject]@{
      platform = 'Walmart'; sku = $item.sku; brand = $item.brand; category = $item.category
      productId = $item.itemId; productName = $item.productName; url = $item.url
      totalReviews = $null; avgRating = $null
      rating1 = $null; rating2 = $null; rating3 = $null; rating4 = $null; rating5 = $null
      negativeReviews = $null; neutralReviews = $null; negativeRate = $null
      textNegativeReviews = $null; textNeutralReviews = $null; ratingsOnlyReviews = $null
      ratingDistributionSum = $null; endpointAllReviews = $null; endpointTextReviews = $null; expectedTextReviews = $null
      textCoverage = $null; negativeTextCoverage = $null
      ratingCheck = 'UNAVAILABLE'; endpointCheck = 'UNAVAILABLE'; textCheck = 'UNAVAILABLE'
      qaStatus = '当前页面不可用'; qaPassed = $false; qaWarnings = $warnings
      topThemes = $themeText; urgency = 'P0 Listing 失效'
      reviewPlan = '当前页面不可用，不制定导评数量；先确认下架、URL 迁移或替代 Listing。'
      actionItems = @('渠道：确认 Listing 是否下架、迁移或替换；更新监控 URL 后重新建立评分基线。')
      firstReview = $null; lastReview = $null; coreNew = $coreNew
      sourceSystem = 'Walmart storefront + Bazaarvoice auxiliary text'
      dataAvailable = $false; availabilityStatus = [string]$item.availabilityStatus
      comparison = $item.comparison
    })
    continue
  }
  $r1 = [int]$stats.ratings.one; $r2 = [int]$stats.ratings.two; $r3 = [int]$stats.ratings.three
  $r4 = [int]$stats.ratings.four; $r5 = [int]$stats.ratings.five
  $total = [int]$stats.totalReviewCount; $textTotal = [int]$stats.reviewsWithTextCount
  $low = $r1 + $r2 + $r3; $rate = if ($total -gt 0) { $low / [double]$total } else { 0 }
  $summaries.Add([pscustomobject]@{
    platform = 'Walmart'; sku = $item.sku; brand = $item.brand; category = $item.category
    productId = $item.itemId; productName = $item.productName; url = $item.url
    totalReviews = $total; avgRating = [math]::Round([double]$stats.averageOverallRating, 4)
    rating1 = $r1; rating2 = $r2; rating3 = $r3; rating4 = $r4; rating5 = $r5
    negativeReviews = $r1 + $r2; neutralReviews = $r3
    negativeRate = if ($total -gt 0) { [math]::Round(($r1 + $r2) / [double]$total, 4) } else { 0 }
    textNegativeReviews = [int]$stats.textRatings.one + [int]$stats.textRatings.two
    textNeutralReviews = [int]$stats.textRatings.three
    ratingsOnlyReviews = $total - $textTotal
    ratingDistributionSum = [int]$item.qa.starSum
    endpointAllReviews = $total; endpointTextReviews = $textTotal; expectedTextReviews = $textTotal
    textCoverage = if ($textTotal -gt 0) { [math]::Round($skuRows.Count / [double]$textTotal, 4) } else { 1 }
    negativeTextCoverage = if (($r1 + $r2) -gt 0) { [math]::Round(([int]$stats.textRatings.one + [int]$stats.textRatings.two) / [double]($r1 + $r2), 4) } else { 1 }
    ratingCheck = if ($item.qa.starSumMatchesTotal) { 'OK' } else { 'MISMATCH' }
    endpointCheck = if ($item.qa.textStarSumMatchesTotal) { 'OK' } else { 'MISMATCH' }
    textCheck = if ($item.qa.lowStarTextTotalMatches) { 'OK' } else { 'MISMATCH' }
    qaStatus = if ($item.qa.passed) { '可用于评分判断' } else { '需人工复核' }
    qaPassed = [bool]$item.qa.passed; qaWarnings = $warnings
    topThemes = $themeText
    urgency = Get-Urgency $total $low $rate $coreNew $themeNames
    reviewPlan = Get-ReviewPlan $total $low $rate $coreNew
    actionItems = @(Get-Actions $themeNames $coreNew)
    firstReview = $null; lastReview = $null; coreNew = $coreNew
    sourceSystem = 'Walmart storefront + Bazaarvoice auxiliary text'
    dataAvailable = $true; availabilityStatus = [string]$item.availabilityStatus
    comparison = $item.comparison
  })
}

$summaryPath = Join-Path $RunDir 'review_summary.json'
$reviewPath = Join-Path $RunDir 'low_star_reviews.json'
$qaPath = Join-Path $RunDir 'qa_report.json'
[System.IO.File]::WriteAllText($summaryPath, (ConvertTo-Json -InputObject @($summaries) -Depth 10), [System.Text.UTF8Encoding]::new($true))
[System.IO.File]::WriteAllText($reviewPath, (ConvertTo-Json -InputObject @($reviewRows) -Depth 8), [System.Text.UTF8Encoding]::new($true))

$qaRows = @($summaries | ForEach-Object {
  $summaryRow = $_
  [pscustomobject]@{
    platform = $summaryRow.platform; sku = $summaryRow.sku; source = $summaryRow.sourceSystem; passed = [bool]$summaryRow.qaPassed
    totalReviews = [int]$summaryRow.totalReviews; ratingSum = [int]$summaryRow.ratingDistributionSum
    textReviews = [int]$summaryRow.endpointTextReviews
    readableLowStarReviews = @($reviewRows | Where-Object { $_.platform -eq $summaryRow.platform -and $_.sku -eq $summaryRow.sku -and (-not [string]::IsNullOrWhiteSpace([string]$_.title) -or -not [string]::IsNullOrWhiteSpace([string]$_.text)) }).Count
    warnings = @($summaryRow.qaWarnings | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
  }
})
[System.IO.File]::WriteAllText($qaPath, (ConvertTo-Json -InputObject $qaRows -Depth 7), [System.Text.UTF8Encoding]::new($true))

$totalReviews = ($summaries | Measure-Object totalReviews -Sum).Sum
$lowStars = ($summaries | ForEach-Object { [int]$_.rating1 + [int]$_.rating2 + [int]$_.rating3 } | Measure-Object -Sum).Sum
$readableRows = @($reviewRows | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.title) -or -not [string]::IsNullOrWhiteSpace([string]$_.text) }).Count
Write-Host "Merged $($summaries.Count) listings, $($reviewRows.Count) low-star review records ($readableRows readable), $totalReviews total ratings, $lowStars low-star ratings."
