#!/usr/bin/env bash
#
# curl-ips.sh – Connect to a list of IPs using curl
# Created by https://github.com/PinePad79
#

# List of target IPs
IPS=(
  31.166.141.166
)

# Optional curl options
# -m 10   : timeout after 10 seconds
# -s      : silent (no progress meter)
# -S      : show errors if they occur
CURL_OPTS="-m 10 -s -S"

for ip in "${IPS[@]}"; do
  echo "=== Connecting to $ip ==="
  
  # You can specify HTTP or HTTPS as needed; here we assume HTTP
  curl $CURL_OPTS "http://$ip" \
    && echo -e "\n[$ip] OK\n" \
    || echo -e "\n[$ip] FAILED\n"
done