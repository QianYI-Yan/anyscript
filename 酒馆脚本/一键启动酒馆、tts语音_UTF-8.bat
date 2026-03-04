:: Open with GBK encoding
:: 我终端不知道为啥锁GBK了
:: required 
:: - https://aka.ms/terminal
:: win11的新版终端，多标签页真的好用
:: - https://github.com/SillyTavern/SillyTavern
:: 酒馆
:: - https://github.com/guoql666/GPT-SoVITS_sillytavern_adapter
:: 插件支持
:: - https://github.com/RVC-Boss/GPT-SoVITS
:: TTS后端
:: - https://www.bilibili.com/video/BV1G1m1BKEEM
:: 教学视频

@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: --- 第一步：路径配置 (亲亲如果换了文件夹改这里就好) ---
:: ==========================================
set "P_ADAPTER=D:\SillyTavern\GPT-SoVITS_sillytavern_adapter"
:: 改插件的文件夹
set "P_API=D:\RVC\GPT-SoVITS-v2pro-20250604"
:: 改TTS的文件夹
set "P_TAVERN=D:\SillyTavern\SillyTavern"
:: 改酒馆的文件夹

:: ==========================================
:: --- 第二步：在临时目录生成 PS1 脚本 ---
:: ==========================================
set "TEMP_DIR=%TEMP%\SillyTavern_Starter"
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

echo Write-Host '--- 启动：语音插件 ---' -ForegroundColor Magenta; cd -LiteralPath '%P_ADAPTER%'; python .\adapter.py; pause > "%TEMP_DIR%\t1.ps1"
echo Write-Host '--- 启动：API V2 ---' -ForegroundColor Cyan; cd -LiteralPath '%P_API%'; .\runtime\python.exe .\api_v2.py; pause > "%TEMP_DIR%\t2.ps1"

:: ? 这里加入了亲亲要的 15 秒倒计时魔法
(
echo Write-Host '--- 准备进入酒馆，开启 15 秒倒计时 ---' -ForegroundColor White
echo for ^($i=15; $i -gt 0; $i--^) {
echo     Write-Host "`r正在等待环境就绪：$i 秒... " -NoNewline -ForegroundColor White
echo     Start-Sleep -Seconds 1
echo }
echo Write-Host "`r倒计时结束，正在召唤酒馆！        " -ForegroundColor Green
echo cd -LiteralPath '%P_TAVERN%'
echo .\Start.bat
echo pause
) > "%TEMP_DIR%\t3.ps1"

:: ==========================================
:: --- 第三步：一键召唤 Windows Terminal ---
:: ==========================================
wt --window -1 ^
  --title "语音插件" --tabColor "#007ACC" powershell -NoExit -ExecutionPolicy Bypass -File "%TEMP_DIR%\t1.ps1" ; ^
  new-tab --title "语音API_V2" --tabColor "#00FF00" powershell -NoExit -ExecutionPolicy Bypass -File "%TEMP_DIR%\t2.ps1" ; ^
  new-tab --title "酒馆" --tabColor "#E74C3C" powershell -NoExit -ExecutionPolicy Bypass -File "%TEMP_DIR%\t3.ps1"

:: 给 WT 一点点启动时间然后退出母体
timeout /t 2 >nul
exit

:: 写脚本的：
:: Gemini --- https://gemini.google.com/