## Makefile - common commands for development

.PHONY: up build backend run lint format clean

up:
	cd infra && docker-compose up --build

build:
	docker build -t iwm-backend backend

backend:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend/app

lint:
	# add linting commands if you use flake/ruff
	echo "No linter configured"

clean:
	rm -rf .venv
