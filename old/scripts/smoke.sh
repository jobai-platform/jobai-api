set -euo pipefail

URL="${BACKEND_HEALTH_URL:-https://domain.tld/api/health}"
echo "Smoke test: GET $URL"
code=$(curl -sk -o /dev/null -w "%{http_code}" "$URL")
if [ "$code" -ne 200 ]; then
  echo "Smoke FAILED (status=$code)"
  exit 1
fi
echo "Smoke OK"
