# Lab 05 Compose Evidence

Generated locally on 2026-06-09. GitHub and registry push are intentionally pending for user review.

## Compose Build And Run

```text
docker compose up -d --build --wait
Result: success after freeing port 8000 from an older Lab 04 container.
```

## Running Containers

```text
fit4110-api-lab05   fit4110/iot-ingestion:lab05   healthy   0.0.0.0:8000->8000/tcp
fit4110-ai-lab05    fit4110/ai-service:lab05      healthy   0.0.0.0:9000->9000/tcp
fit4110-db-lab05    postgres:15-alpine            healthy   0.0.0.0:5432->5432/tcp
```

## Health And Readiness

```text
GET http://localhost:8000/health
{"status":"ok","service":"iot-ingestion","version":"0.5.0"}

GET http://localhost:8000/readiness
{"status":"ready","service":"iot-ingestion","version":"0.5.0","db":{"ready":true,"detail":"PostgreSQL is reachable"},"ai":{"ready":true,"detail":"AI service is reachable"}}

GET http://localhost:9000/health
{"status":"ok","service":"ai-service","version":"0.5.0"}

docker compose exec -T db pg_isready -U lab05 -d iotdb
/var/run/postgresql:5432 - accepting connections
```

## Non-root Runtime

```text
docker compose exec -T api id
uid=100(appuser) gid=101(appgroup) groups=101(appgroup)

docker compose exec -T ai-service id
uid=100(appuser) gid=101(appgroup) groups=101(appgroup)
```

## Newman Result

```text
npm run test:compose
requests: 13 executed, 0 failed
assertions: 27 executed, 0 failed
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## Image Tags

```text
fit4110/iot-ingestion:lab05 d89b0fc6a346 295MB
fit4110/ai-service:lab05 578ff85b874c 295MB
ghcr.io/dvkncnnt1708/team-iot:v0.1.0-team-iot d89b0fc6a346 295MB
```
