.PHONY: install lint build run compose-up compose-down compose-ps logs test-compose readiness

install:
	npm ci

lint:
	npm run lint:openapi

build:
	docker build -t fit4110/iot-ingestion:lab05 .

run:
	docker run --rm --name fit4110-api-lab05 -p 8000:8000 --env-file .env.example fit4110/iot-ingestion:lab05

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

compose-ps:
	docker compose ps

logs:
	docker compose logs -f

readiness:
	curl http://localhost:8000/health
	curl http://localhost:8000/readiness
	curl http://localhost:9000/health
	docker compose exec -T db pg_isready -U lab05 -d iotdb

test-compose:
	npm run test:compose
