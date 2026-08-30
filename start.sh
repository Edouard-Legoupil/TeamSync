#!/usr/bin/env bash
#
# start.sh — launch TeamSync locally in development mode.
#
# Starts:
#   1. FastAPI backend  -> http://localhost:8000  (uvicorn, auto-reload)
#   2. React frontend   -> http://localhost:5173  (Vite, proxies /api -> :8000)
#
# Usage:
#   ./start.sh                    # install deps if needed, then start both
#   ./start.sh --seed             # also seed demo users/teams first
#   ./start.sh --skip-install     # skip pip/npm install steps
#   ./start.sh --help             # show this help
#
# Environment overrides (these win over backend/.env, per pydantic-settings):
#   DATABASE_URL, FRONTEND_URL, AZURE_AD_REDIRECT_URI, CORS_ORIGINS,
#   ALLOW_DEV_LOGIN, OPENAI_API_KEY, AZURE_AD_* , JWT_SECRET_KEY
#
# Ctrl+C stops both servers.

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

SEED=0
SKIP_INSTALL=0

usage() {
  sed -n '2,16p' "$0"
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --seed) SEED=1 ;;
    --skip-install) SKIP_INSTALL=1 ;;
    -h | --help) usage ;;
    *) echo "Unknown option: $arg (use --help)" >&2; exit 2 ;;
  esac
done

# --- helpers ----------------------------------------------------------------

log()  { printf '\033[1;34m[teamsync]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[teamsync]\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m[teamsync]\033[0m %s\n' "$*" >&2; exit 1; }

# Returns 0 if a process is already listening on 127.0.0.1:$1.
port_in_use() {
  (exec 3<>/dev/tcp/127.0.0.1/$1) 2>/dev/null
}

command -v python3 >/dev/null 2>&1 || fail "python3 is required but not found."
command -v node    >/dev/null 2>&1 || fail "node is required but not found."
command -v npm     >/dev/null 2>&1 || fail "npm is required but not found."

# --- dev defaults (overridable; these override backend/.env) ----------------

# The Vite dev server serves the SPA and proxies /api to :8000, so SSO
# callbacks and post-login redirects target the Vite origin.
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
export AZURE_AD_REDIRECT_URI="${AZURE_AD_REDIRECT_URI:-http://localhost:5173/api/auth/callback}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173}"
export ALLOW_DEV_LOGIN="${ALLOW_DEV_LOGIN:-true}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./teamsync.db}"

# --- backend ----------------------------------------------------------------

log "Preparing backend ($BACKEND_DIR)"

if [ ! -d "$BACKEND_DIR/venv" ]; then
  log "Creating Python virtualenv..."
  python3 -m venv "$BACKEND_DIR/venv"
fi

# shellcheck disable=SC1091
source "$BACKEND_DIR/venv/bin/activate"

if [ ! -f "$BACKEND_DIR/.env" ]; then
  warn "No backend/.env found — created from .env.example (edit to configure Azure AD / OpenAI)."
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ "$SKIP_INSTALL" -eq 0 ] && ! python -c "import fastapi, sqlalchemy, jose" >/dev/null 2>&1; then
  log "Installing backend dependencies (pip install -r requirements.txt)..."
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r "$BACKEND_DIR/requirements.txt"
fi

python -c "import uvicorn" >/dev/null 2>&1 || fail "uvicorn not installed (re-run without --skip-install)."

if [ "$SEED" -eq 1 ]; then
  log "Seeding demo data..."
  (cd "$BACKEND_DIR" && python -m seed)
fi

# --- frontend ---------------------------------------------------------------

log "Preparing frontend ($FRONTEND_DIR)"

if [ "$SKIP_INSTALL" -eq 0 ] && [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  log "Installing frontend dependencies (npm install)..."
  (cd "$FRONTEND_DIR" && npm install)
fi

[ -x "$FRONTEND_DIR/node_modules/.bin/vite" ] \
  || fail "Vite not found in frontend/node_modules (re-run without --skip-install)."

# --- run both servers with graceful shutdown --------------------------------

if port_in_use 8000; then
  warn "Port 8000 is already in use — is another backend running?"
  warn "Find it with:  lsof -i :8000   (or:  ss -ltnp | grep 8000)"
  fail "Stop the existing process, then re-run start.sh."
fi

if port_in_use 5173; then
  warn "Port 5173 is already in use — is another frontend running?"
  fail "Stop the existing process, then re-run start.sh."
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  log "Shutting down dev servers..."
  for pid in "$BACKEND_PID" "$FRONTEND_PID"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT TERM

log "Starting backend: http://localhost:8000"
(cd "$BACKEND_DIR" && exec python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

log "Starting frontend: http://localhost:5173"
(cd "$FRONTEND_DIR" && exec "$FRONTEND_DIR/node_modules/.bin/vite") &
FRONTEND_PID=$!

echo ""
log "TeamSync is starting up."
log "  App:        http://localhost:5173"
log "  API health: http://localhost:8000/api/health"
log "  Database:   ${DATABASE_URL}"
if [ "${ALLOW_DEV_LOGIN:-true}" = "true" ]; then
  log "  Dev login:  http://localhost:5173/api/auth/dev-login?email=supervisor@example.org"
fi
echo ""
warn "Press Ctrl+C to stop both servers."

# Block until one server exits, then tear the other down (EXIT trap does this).
wait -n 2>/dev/null || true
log "A dev server exited. Stopping the other."
