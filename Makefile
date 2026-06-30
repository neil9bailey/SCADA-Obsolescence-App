.PHONY: run test migrate docker-up docker-down clean-demo

run:
	uvicorn app.main:app --reload

test:
	pytest -q tests

migrate:
	alembic upgrade head

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean-demo:
	rm -f data/scada_obsolescence.db
