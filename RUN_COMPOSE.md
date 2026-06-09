# RUN_COMPOSE.md - Huong dan chay Lab 05

Tai lieu nay giup nguoi khac clone repo sach, chay toan bo Docker Compose stack va kiem tra lai bang Newman.

## 1. Clone repo va cai Newman tooling

```bash
git clone https://github.com/DVKNCNNT1708/lab-5-Tuanhimmnz.git
cd lab-5-Tuanhimmnz
npm ci
```

## 2. Chay Docker Compose stack

```bash
docker compose up -d --build
```

Stack gom 3 service:

- `fit4110-db-lab05`: PostgreSQL, healthcheck bang `pg_isready`
- `fit4110-ai-lab05`: mock AI service, port `9000`
- `fit4110-api-lab05`: IoT API, port `8000`, chay bang non-root user

## 3. Kiem tra health va readiness

```bash
curl http://localhost:8000/health
curl http://localhost:8000/readiness
curl http://localhost:9000/health
docker compose exec -T db pg_isready -U lab05 -d iotdb
```

Ket qua mong doi:

```json
{"status":"ok","service":"iot-ingestion","version":"0.5.0"}
```

`/readiness` phai tra `status=ready`, `db.ready=true`, `ai.ready=true`.

## 4. Chay Newman tren Compose

```bash
npm run test:compose
```

Report sinh tai:

```text
reports/newman-lab05-compose.xml
reports/newman-lab05-compose.html
```

## 5. Dung stack

```bash
docker compose down
```

Xoa ca volume DB neu can chay lai tu dau:

```bash
docker compose down -v
```
