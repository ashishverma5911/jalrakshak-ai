#!/bin/bash
set -e

PROJECT="$HOME/Downloads/JalRakshak A.I."
BACKEND="$PROJECT/backend"
FRONTEND="$PROJECT/frontend"

cd "$PROJECT"

if [ ! -d "$BACKEND" ] || [ ! -f "$BACKEND/app/main.py" ]; then
  echo "ERROR: Backend files were not found at $BACKEND"
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -f "$FRONTEND/package.json" ]; then
  echo "ERROR: Frontend package.json was not found."
  read -p "Press Enter to close..."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is not installed."
  read -p "Press Enter to close..."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: Node.js/npm is not installed."
  read -p "Press Enter to close..."
  exit 1
fi

if [ ! -d "$BACKEND/.venv" ]; then
  python3 -m venv "$BACKEND/.venv"
fi

if [ -f "$BACKEND/requirements.txt" ]; then
  "$BACKEND/.venv/bin/python" -m pip install \
    -r "$BACKEND/requirements.txt"
fi

if [ ! -x "$BACKEND/.venv/bin/uvicorn" ]; then
  "$BACKEND/.venv/bin/python" -m pip install uvicorn
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  cd "$FRONTEND"
  npm install
fi

BACKEND_LOG="$PROJECT/backend-launch.log"
"$BACKEND/.venv/bin/python" -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting JalRakshak AI..."

for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend failed. Check $BACKEND_LOG"
    cat "$BACKEND_LOG"
    exit 1
  fi
  sleep 1
done

if ! curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null; then
  echo "Backend did not become healthy. Check $BACKEND_LOG"
  exit 1
fi

cd "$FRONTEND"
echo "Opening JalRakshak AI at http://localhost:5173"
open http://localhost:5173
npm run dev -- --host 127.0.0.1
