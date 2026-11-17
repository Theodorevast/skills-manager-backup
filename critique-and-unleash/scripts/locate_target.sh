#!/bin/zsh
# Usage: zsh locate_target.sh <port_or_url>
# Resolves a running local port/URL to its exact PID, command, working directory, and HTML entry files.
set -e
INPUT="${1:-}"
if [ -z "$INPUT" ]; then
  echo "Usage: $0 <port_or_url>"
  exit 1
fi

PORT=$(echo "$INPUT" | sed -E 's#^[a-zA-Z]+://[^:/]+:([0-9]+).*#\1#; s#^[^0-9]*([0-9]+).*#\1#')
if [ -z "$PORT" ]; then
  echo "Could not extract port from: $INPUT"
  exit 1
fi

echo "=== Port :$PORT Listener ==="
PIDS=$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)
if [ -z "$PIDS" ]; then
  echo "No process listening on port $PORT"
  exit 0
fi

for PID in $PIDS; do
  echo "PID: $PID"
  ps -p "$PID" -o pid,ppid,command
  CWD=$(lsof -a -p "$PID" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  echo "CWD: $CWD"
  if [ -n "$CWD" ] && [ -d "$CWD" ]; then
    echo "=== HTML Entries in $CWD ==="
    find "$CWD" -maxdepth 2 -name "*.html" -not -path "*/node_modules/*" -not -path "*/dist/*"
    echo "=== Docs / Prompts / Specs in $CWD ==="
    find "$CWD" -maxdepth 3 \( -path "*/docs/*" -o -path "*/prompts/*" -o -name "*spec*.md" -o -name "*design*.md" \) -not -path "*/node_modules/*" 2>/dev/null | head -n 25
  fi
done
