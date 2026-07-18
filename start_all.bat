@echo off

echo Starting Backend (Flask App with Groq API)...
start cmd /k "cd backend && python app.py"

timeout /t 2

echo Starting Frontend (React Dev Server)...
start cmd /k "cd frontend && npm run dev"

echo All services started.
echo Note: Make sure you have set your GROQ_API_KEY in the .env file
pause
