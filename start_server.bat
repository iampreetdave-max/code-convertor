@echo off
echo ==================================
echo   Code Converter - Starting...
echo ==================================
echo.

:: Load environment variables (e.g. GROQ_API_KEY) from a local .env file if present.
:: Copy .env.example to .env and add your key there. .env is gitignored.
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%~dp0.env") do (
        set "%%a=%%b"
    )
)

:: Change to backend directory
cd /d "%~dp0backend"

if defined GROQ_API_KEY (
    echo Groq API key: Set
) else (
    echo Groq API key: NOT set ^(create a .env file with GROQ_API_KEY=... - see .env.example^)
)
echo.
echo ==================================
echo   Open in browser:
echo   http://localhost:8080
echo ==================================
echo.
echo Press Ctrl+C to stop the server
echo.

:: Start the server on port 8080
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8080

:: If server crashes, show error and pause
echo.
echo ==================================
echo   Server stopped or crashed!
echo ==================================
pause
