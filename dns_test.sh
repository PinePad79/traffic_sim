#!/usr/bin/env bash
set -euo pipefail

# dns_test.sh
# Defensive DNS filtering lab test (UDP/53).
#
# It performs A-record DNS queries for a fixed domain list and evaluates the response:
# - If the answer contains 208.91.112.55 -> "Blocked by Fortiguard DNS Filtering"
# - Otherwise -> "OK" (not blocked)
#
# Usage: ./dns_test.sh <DNS_SERVER_IP>
#
# Requirements: dig (dnsutils)

DNS_SERVER="${1:-}"
BLOCK_IP="208.91.112.55"

if [[ -z "$DNS_SERVER" ]]; then
  echo "Usage: $0 <DNS_SERVER_IP>"
  exit 1
fi

if ! command -v dig >/dev/null 2>&1; then
  echo "ERROR: 'dig' not found. Install with: sudo apt install -y dnsutils"
  exit 1
fi

RUN_ID="$(date +%Y%m%d-%H%M%S)"
echo "============================================================"
echo "DNS FILTERING TEST (UDP/53)"
echo "Run ID     : ${RUN_ID}"
echo "DNS Server : ${DNS_SERVER}"
echo "Block IP   : ${BLOCK_IP} (expected FortiGuard block page IP)"
echo "============================================================"

DOMAINS=(
  "hak5.org"
  "fortinet.com"
  "cnn.com"
  "bbc.com"
  "facebook.com"
  "instagram.com"
)

total=0
blocked=0
ok=0
fail=0

query_domain() {
  local d="$1"
  dig @"$DNS_SERVER" "$d" A +time=2 +tries=1 +short 2>/dev/null || true
}

for d in "${DOMAINS[@]}"; do
  total=$((total+1))
  echo "---- Query A: ${d}"
  ans="$(query_domain "$d")"
  if [[ -z "$ans" ]]; then
    echo "Result: FAIL (no answer)"
    fail=$((fail+1))
    continue
  fi

  # If any returned IP equals BLOCK_IP, treat as blocked
  if echo "$ans" | grep -q "^${BLOCK_IP}$"; then
    echo "Answer: ${ans}"
    echo "Result: Blocked by Fortiguard DNS Filtering"
    blocked=$((blocked+1))
  else
    echo "Answer: ${ans}"
    echo "Result: OK"
    ok=$((ok+1))
  fi
done

echo "------------------ SUMMARY ------------------"
echo "Total domains : ${total}"
echo "OK            : ${ok}"
echo "Blocked       : ${blocked}"
echo "FAIL          : ${fail}"
echo "Evidence Tag  : DNSRun:${RUN_ID} DNS:${DNS_SERVER}"
echo "---------------------------------------------"

if (( ok + blocked > 0 )); then
  exit 0
fi
exit 2
