@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Сборка PCCleaner_x64.exe для Windows x64 (64-бит)
echo ============================================
echo.

rem --- ищем файл программы рядом со скриптом ---
set SCRIPT=cleaner.py
if exist "%SCRIPT%" goto havefile
echo Файл cleaner.py не найден в папке:
echo   %~dp0
echo.
echo Скопируйте файл программы в эту папку и назовите его cleaner.py,
echo либо введите имя файла программы, например main.py
set /p SCRIPT=Имя файла:
if exist "%SCRIPT%" goto havefile
echo.
echo [ОШИБКА] Файл "%SCRIPT%" не найден в папке %~dp0
pause
exit /b 1

:havefile
echo Собираю из файла: %SCRIPT%
echo.

set BITS=
for /f %%i in ('py -3-64 -c "import struct;print(struct.calcsize('P')*8)" 2^>nul') do set BITS=%%i
if not "%BITS%"=="64" goto no64

if not exist .venv64\Scripts\activate.bat py -3-64 -m venv .venv64
if not exist .venv64\Scripts\activate.bat goto fail
call .venv64\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install pyinstaller pillow
if errorlevel 1 goto fail

rem Чтобы .exe ВСЕГДА запрашивал права администратора, добавьте параметр --uac-admin
rem Значок программы: app.ico рядом со скриптом (создаётся автоматически, если его нет)
if not exist app.ico python -c "import sys; sys.argv=['x']; import cleaner; im=cleaner.app_icon_image(256); im.save('app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
rem Временные файлы сборки — в %%TEMP%%: внутри OneDrive PyInstaller не может удалить папку build
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PCCleaner_x64 --icon app.ico --workpath "%TEMP%\pcc_build" "%SCRIPT%"
if errorlevel 1 goto fail

echo.
echo Готово! Файл: %~dp0dist\PCCleaner_x64.exe
pause
exit /b 0

:no64
echo [ОШИБКА] Не найден 64-битный Python. Установите его командой:   py install 3-64
pause
exit /b 1

:fail
echo.
echo [ОШИБКА] Сборка не удалась. Прочитайте сообщения выше.
pause
exit /b 1
