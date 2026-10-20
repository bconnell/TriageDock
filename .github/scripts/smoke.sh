#!/usr/bin/env bash
set -euo pipefail

echo "Building and starting isolated TriageDock Compose services"
docker compose up --build -d

echo "Waiting for HTTP readiness"
ready=0
for attempt in $(seq 1 50); do
  if curl --max-time 2 --fail --silent http://127.0.0.1:8000/health/ > /dev/null; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" != "1" ]; then
  echo "Web application did not become ready" >&2
  exit 1
fi

echo "Checking rendered dashboard and bundled asset"
curl --fail --silent --show-error http://127.0.0.1:8000/ > /tmp/triagedock-dashboard.html
grep -q "TriageDock | Incident response console" /tmp/triagedock-dashboard.html
asset=$(grep -oE '/static/ui/assets/[^"]+\.js' /tmp/triagedock-dashboard.html | head -n 1)
test -n "$asset"
curl --fail --silent --show-error "http://127.0.0.1:8000$asset" -o /dev/null

echo "Confirming session barrier and protected alert intake"
session_code=$(curl --silent --output /dev/null --write-out "%{http_code}" http://127.0.0.1:8000/api/v1/incidents/)
test "$session_code" = "403"
reject_code=$(curl --silent --output /dev/null --write-out "%{http_code}" \
  -X POST http://127.0.0.1:8000/api/v1/alerts/ \
  -H "Content-Type: application/json" \
  --data '{"source":"ci","external_key":"idempotent","title":"CI alert","severity":"high"}')
test "$reject_code" = "401"

echo "Verifying HTTP 201 -> 200 deduplication through real PostgreSQL"
for expected in 201 200; do
  code=$(curl --silent --show-error --output /tmp/triagedock-alert.json --write-out "%{http_code}" \
    -X POST http://127.0.0.1:8000/api/v1/alerts/ \
    -H "Content-Type: application/json" \
    -H "X-TriageDock-Key: $INGEST_API_KEY" \
    --data '{"source":"ci","external_key":"idempotent","title":"CI alert","severity":"high"}')
  if [ "$code" != "$expected" ]; then
    echo "Expected HTTP $expected but received $code" >&2
    exit 1
  fi
done
docker compose exec -T web python manage.py shell -c \
  "from incidents.models import Incident, IncidentEvent; assert Incident.objects.count() == 1; assert Incident.objects.get().occurrences == 2; assert IncidentEvent.objects.count() == 2"
echo "Live Compose smoke checks passed"
