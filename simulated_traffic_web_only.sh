#!/usr/bin/env bash
#
# simulated_traffic_web_only.sh — simulate safe app/web traffic (no downloads)
# Tested on Ubuntu 24.04

set -euo pipefail

install_pkg() {
  local pkg=$1
  if ! dpkg -s "$pkg" &>/dev/null; then
    echo "→ Installing $pkg..."
    sudo apt-get update -qq
    sudo apt-get install -y "$pkg"
  fi
}

# Minimal deps for web/app style traffic
for p in curl coreutils openssl netcat-openbsd; do
  install_pkg "$p"
done

simulate_web_traffic() {
  echo
  echo "=== Web / App traffic ==="

  # Keep this list clean and safe (no adult sites). Add your own as needed.
  SITES=(
    example.com
    wikipedia.org
    github.com
    ubuntu.com
    cloudflare.com
    aws.amazon.com
  )

  echo
  echo "--- HTTP (port 80) HEAD requests"
  for host in "${SITES[@]}"; do
    url="http://$host"
    echo "- Testing $url"
    if timeout 8 curl -m 8 -s -S -I "$url" &>/dev/null; then
      echo "  ✔ OK"
    else
      echo "  ✖ FAILED"
    fi
  done

  echo
  echo "--- HTTPS (port 443) HEAD requests"
  for host in "${SITES[@]}"; do
    url="https://$host"
    echo "- Testing $url"
    if timeout 8 curl -m 8 -s -S -I "$url" &>/dev/null; then
      echo "  ✔ OK"
    else
      echo "  ✖ FAILED"
    fi
  done
}

simulate_im_traffic() {
  echo
  echo "=== Messaging-like TLS handshake traffic ==="

  # Lightweight: just a TLS handshake to a known host:443
  # (If you want to change it, use a domain you own/control.)
  TARGET_HOST="example.com"

  echo "- TLS handshake to $TARGET_HOST:443"
  if timeout 8 openssl s_client -connect "$TARGET_HOST":443 </dev/null &>/dev/null; then
    echo "  ✔ OK"
  else
    echo "  ✖ FAILED"
  fi

  # Optional: raw TCP connect to a public XMPP server (no auth, no messages)
  XMPP_HOST="jabber.at"
  echo
  echo "- TCP connect (XMPP style) to $XMPP_HOST:5222"
  if timeout 8 nc -vz "$XMPP_HOST" 5222 &>/dev/null; then
    echo "  ✔ OK"
  else
    echo "  ✖ FAILED"
  fi
}

main() {
  echo ">>> Starting safe traffic simulation $(date)"
  simulate_web_traffic
  simulate_im_traffic
  echo
  echo ">>> Done $(date)"
}

main "$@"
