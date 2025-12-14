#!/usr/bin/env bash
set -euo pipefail

# controlled_load.sh
# Purpose: Generate SAFE, controlled HTTP traffic for FortiGate DoS-policy *visibility* and logging labs.
# - Runs for an exact duration (default 10s)
# - Caps concurrency
# - Reports achieved request rate (requests/sec)
# - Labels the run clearly (Run ID + parameters)
#
# This script completes normal HTTP requests (no half-open handshakes).
# It uses lightweight HTTP requests and does not intentionally overload targets.

IP="${1:-}"
DURATION_SEC="${2:-10}"
CONCURRENCY="${3:-20}"
TIMEOUT_SEC="${4:-2}"
URL_PATH="${5:-/}"              # Optional path, e.g. /, /health, /index.html
METHOD="${6:-HEAD}"             # HEAD (default) or GET

if [[ -z "$IP" ]]; then
  echo "Usage: $0 <DEST_IP> [duration_sec=10] [concurrency=20] [timeout_sec=2] [path=/] [method=HEAD|GET]"
  exit 1
fi

if ! [[ "$DURATION_SEC" =~ ^[0-9]+$ ]] || (( DURATION_SEC <= 0 )); then
  echo "ERROR: duration_sec must be a positive integer."
  exit 1
fi

if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || (( CONCURRENCY <= 0 )); then
  echo "ERROR: concurrency must be a positive integer."
  exit 1
fi

if ! [[ "$TIMEOUT_SEC" =~ ^[0-9]+$ ]] || (( TIMEOUT_SEC <= 0 )); then
  echo "ERROR: timeout_sec must be a positive integer."
  exit 1
fi

METHOD_UPPER="$(echo "$METHOD" | tr '[:lower:]' '[:upper:]')"
if [[ "$METHOD_UPPER" != "HEAD" && "$METHOD_UPPER" != "GET" ]]; then
  echo "ERROR: method must be HEAD or GET."
  exit 1
fi

RUN_ID="$(date +%Y%m%d-%H%M%S)"
TARGET_URL="http://${IP}${URL_PATH}"

# curl options:
# -m : max time
# -sS: silent but show errors
# -o /dev/null: discard body
# -I : HEAD
# -L : follow redirects (some labs may redirect)
CURL_COMMON=(-m "$TIMEOUT_SEC" -sS -o /dev/null -L)
UA="Lab-Traffic-Sim-ControlledLoad/1.0 (Run:${RUN_ID})"

if [[ "$METHOD_UPPER" == "HEAD" ]]; then
  CURL_CMD=(curl -I "${CURL_COMMON[@]}" -A "$UA" "$TARGET_URL")
else
  CURL_CMD=(curl "${CURL_COMMON[@]}" -A "$UA" "$TARGET_URL")
fi

echo "============================================================"
echo "CONTROLLED LOAD RUN"
echo "Run ID        : ${RUN_ID}"
echo "Destination   : ${IP}"
echo "URL           : ${TARGET_URL}"
echo "Method        : ${METHOD_UPPER}"
echo "Duration (s)  : ${DURATION_SEC}"
echo "Concurrency   : ${CONCURRENCY}"
echo "Timeout (s)   : ${TIMEOUT_SEC}"
echo "User-Agent    : ${UA}"
echo "============================================================"

start_epoch="$(date +%s)"
end_epoch=$((start_epoch + DURATION_SEC))

# Counters
total_started=0
total_ok=0
total_fail=0

# temp files for per-request results
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# We implement a simple worker pool:
# - Keep up to $CONCURRENCY curl processes running
# - Each writes success/fail marker to a temp file
# - Stop launching new ones once time is up, then wait for in-flight to finish

pids=()

launch_one() {
  local idx="$1"
  local out="${tmpdir}/r_${idx}.txt"
  # Mark OK/FAIL by exit code
  (
    if "${CURL_CMD[@]}" >/dev/null 2>&1; then
      echo "OK" > "$out"
    else
      echo "FAIL" > "$out"
    fi
  ) &
  echo $!  # pid
}

# Main loop: launch until time is up, respecting concurrency
while true; do
  now="$(date +%s)"
  if (( now >= end_epoch )); then
    break
  fi

  # Clean finished PIDs from list
  if ((${#pids[@]} > 0)); then
    still=()
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        still+=("$pid")
      fi
    done
    pids=("${still[@]}")
  fi

  # Launch more if we have capacity
  while (( ${#pids[@]} < CONCURRENCY )); do
    now="$(date +%s)"
    if (( now >= end_epoch )); then
      break
    fi
    total_started=$((total_started + 1))
    pid="$(launch_one "$total_started")"
    pids+=("$pid")
    # tiny sleep to avoid ultra-tight loop; keeps things stable
    sleep 0.01
  done

  # brief pause before next scheduling tick
  sleep 0.05
done

# Wait for remaining in-flight requests
for pid in "${pids[@]}"; do
  wait "$pid" 2>/dev/null || true
done

# Aggregate results
# Count OK/FAIL markers created
if compgen -G "${tmpdir}/r_*.txt" > /dev/null; then
  while IFS= read -r f; do
    if grep -q "^OK$" "$f"; then
      total_ok=$((total_ok + 1))
    else
      total_fail=$((total_fail + 1))
    fi
  done < <(ls -1 "${tmpdir}"/r_*.txt)
fi

finish_epoch="$(date +%s)"
elapsed=$((finish_epoch - start_epoch))
if (( elapsed <= 0 )); then
  elapsed=1
fi

rps=$(python3 - <<EOF
ok=${total_ok}
elapsed=${elapsed}
print(f"{ok/elapsed:.2f}")
EOF
)

echo "------------------ RESULTS ------------------"
echo "Elapsed (s)      : ${elapsed}"
echo "Requests started : ${total_started}"
echo "OK               : ${total_ok}"
echo "FAIL             : ${total_fail}"
echo "Achieved RPS     : ${rps} (OK/second)"
echo "Evidence Tag     : Run:${RUN_ID} UA:${UA}"
echo "---------------------------------------------"

# Exit non-zero only if *all* requests failed (helps students see issues)
if (( total_ok == 0 )); then
  exit 2
fi
exit 0
