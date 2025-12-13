#!/usr/bin/env bash
set -euo pipefail

IP="${1:-}"
REQ="${2:-50}"
CONC="${3:-10}"
TO="${4:-2}"

if [ -z "$IP" ]; then
  echo "Usage: $0 <IP> [requests] [concurrency] [timeout]"
  exit 1
fi

active=0
for ((i=1; i<=REQ; i++)); do
  curl -m "$TO" -s "http://$IP/" >/dev/null &
  active=$((active+1))
  if [ "$active" -ge "$CONC" ]; then
    wait
    active=0
  fi
done
wait
echo "LOAD_DONE"
