#!/usr/bin/env bash
set -euo pipefail

IP="${1:-}"
PATH_BEACON="${2:-/beacon}"
UA="${3:-Lab-Traffic-Sim}"
TO="${4:-5}"

if [ -z "$IP" ]; then
  echo "Usage: $0 <IP> [path] [user-agent] [timeout]"
  exit 1
fi

curl -m "$TO" -sS "http://$IP$PATH_BEACON" -A "$UA" >/dev/null && echo "BEACON_OK" || echo "BEACON_FAILED"
