@echo off
chcp 65001 >nul
echo 正在创建 Bili2Text 桌面快捷方式...

set "PROJ_DIR=%~dp0"

powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([System.IO.Path]::Combine($env:USERPROFILE,'Desktop','Bili2Text.lnk'));$s.TargetPath='%PROJ_DIR%start.bat';$s.WorkingDirectory='%PROJ_DIR%';$s.IconLocation='%PROJ_DIR%favicon.ico';$s.Description='Bili2Text - Bilibili视频转文字工具';$s.Save()"

if %errorlevel% == 0 (
    echo.
    echo  桌面快捷方式创建成功！双击桌面上的 Bili2Text 图标即可启动。
) else (
    echo.
    echo  创建失败，请尝试以管理员身份运行此脚本。
)

pause
