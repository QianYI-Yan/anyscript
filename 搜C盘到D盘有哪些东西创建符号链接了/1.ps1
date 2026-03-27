$targetDisk = "C:\"
$startTime = Get-Date

Write-Host "--- 寂月的 CPU 并行全盘扫描 (优化版) ---" -ForegroundColor Red
Write-Host "[System] 正在压榨所有处理器核心... 全盘扫描启动！🔥" -ForegroundColor Gray

# 1. 获取顶级目录（排除常见系统区）
$excludeDirs = @("Windows","Program Files","Program Files (x86)","ProgramData","PerfLogs","$Recycle.Bin","System Volume Information")
$topDirs = Get-ChildItem -Path $targetDisk -Force -ErrorAction SilentlyContinue |
           Where-Object { $excludeDirs -notcontains $_.Name }

# 2. 并行扫描：流式处理，避免一次性加载
$allFound = $topDirs | ForEach-Object -Parallel {
    $count = 0
    Get-ChildItem -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $count++
        if ($count % 1000 -eq 0) {
            Write-Progress -Activity "正在扫描 $($_.FullName)" -Status "已检查 $count 项" -PercentComplete 0
        }

        # 核心逻辑：检测符号链接指向 D 盘
        if ($_.LinkType -ne $null -and $_.Target -like "D:*") {
            [PSCustomObject]@{
                "名称"     = $_.Name
                "类型"     = $_.LinkType
                "指向 D 盘" = $_.Target
                "C 盘位置" = $_.FullName
            }
        }
    }
} -ThrottleLimit 16   # 建议 8–16 线程，避免 I/O 拥堵

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-Host "`n----------------------------------------" -ForegroundColor Cyan
Write-Host "扫描完成！耗时: $($duration.ToString("F2")) 秒" -ForegroundColor White

# 3. 整理序号并输出结果
if ($allFound) {
    $i = 0
    $finalList = @($allFound) | ForEach-Object {
        $i++
        $_ | Add-Member -NotePropertyName "序号" -NotePropertyValue $i -PassThru
    }

    Write-Host "正在弹出结果清单窗口，寂月请查收！(✿◡‿◡)" -ForegroundColor Cyan
    $finalList | Select-Object 序号, 名称, 类型, "指向 D 盘", "C 盘位置" | Out-GridView -Title "寂月的全盘并行扫描清单 (共 $i 项)"

    # 同时保存到 CSV，避免窗口关闭后丢失
    $finalList | Export-Csv -Path "C:\ScanResult.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "结果已保存到 C:\ScanResult.csv" -ForegroundColor Green
} else {
    Write-Host "报告寂月！全盘扫描完毕，未发现符合条件的链接。 (｡•́︿•̀｡)" -ForegroundColor Yellow
}


#这个别用