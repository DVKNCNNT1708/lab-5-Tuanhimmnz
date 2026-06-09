# Readiness Checklist - Lab 05

- [x] **Database ready:** container `fit4110-db-lab05` chay va `pg_isready -U lab05 -d iotdb` tra ready.
- [x] **AI service ready:** container `fit4110-ai-lab05` tra `200` cho `/health` va `/predict` hoat dong.
- [x] **API ready:** container `fit4110-api-lab05` tra `200` cho `/health`, `/readiness` va tao/lai readings voi token hop le.
- [x] **Environment variables:** runtime config tach qua `.env.example`; repo khong commit `.env` hay secret that.
- [x] **Network and ports:** `team-internal` hoat dong; API goi noi bo `db:5432` va `ai-service:9000`; host map API `8000`, AI `9000`, DB `5432`.
- [x] **Version and image tags:** image local dung tag `fit4110/iot-ingestion:lab05`, `fit4110/ai-service:lab05`, registry tag goi y `ghcr.io/dvkncnnt1708/team-iot:v0.1.0-team-iot`.

Evidence:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
reports/lab05-compose-evidence.md
```
