#!/usr/bin/env bash
set -euo pipefail

# Benign HTTP/HTTPS requests to test Web Filter categorization and policy enforcement.
# Only lightweight HEAD requests; no downloads.

CURL_OPTS=(-m 8 -sS -I -L)
UA="Lab-Traffic-Sim-Web/1.0"

SITES=(
  "http://www.fortinet.com"
  "http://www.cnn.com"
  "http://www.onlyfans.com"
  "http://www.facebook.com"
  "http://www.youtube.com"  
  "https://www.hak5.org"
  "https://www.fortinet.com"
  "https://www.cnn.com"
  "https://www.bbc.com"
  "https://www.facebook.com"
  "https://www.instagram.com"
  "https://www.onlyfans.com"
  "https://www.pornhub.com"
)

for url in "${SITES[@]}"; do
  echo "=== WEB test -> $url ==="
  curl "${CURL_OPTS[@]}" -A "$UA" "$url" >/dev/null && echo "[OK] $url" || echo "[FAIL] $url"
done
