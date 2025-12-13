#!/usr/bin/env bash
set -euo pipefail

# Benign HTTPS requests to simulate "app-like" traffic:
# - Video/streaming
# - Cloud/SaaS
# - Instant messaging/collaboration
# Only lightweight HEAD requests; no downloads.

CURL_OPTS=(-m 8 -sS -I -L)
UA="Lab-Traffic-Sim-App/1.0"

VIDEO_URLS=(
  "https://www.youtube.com"
  "https://m.youtube.com"
  "https://www.twitch.tv"
  "https://vimeo.com"
)

CLOUD_URLS=(
  "https://aws.amazon.com"
  "https://login.microsoftonline.com"
  "https://drive.google.com"
  "https://dropbox.com"
)

IM_URLS=(
  "https://web.whatsapp.com"
  "https://discord.com"
  "https://slack.com"
  "https://telegram.org"
)

hit() {
  local url="$1"
  echo "=== APP traffic -> $url ==="
  curl "${CURL_OPTS[@]}" -A "$UA" "$url" >/dev/null && echo "[OK] $url" || echo "[FAIL] $url"
}

echo "== Video =="
for u in "${VIDEO_URLS[@]}"; do hit "$u"; done

echo "== Cloud =="
for u in "${CLOUD_URLS[@]}"; do hit "$u"; done

echo "== Instant Messaging / Collaboration =="
for u in "${IM_URLS[@]}"; do hit "$u"; done
