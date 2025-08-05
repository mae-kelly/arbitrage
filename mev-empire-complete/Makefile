.PHONY: help install setup compile test lint format build deploy start stop logs backup restore clean

help:
	@echo "MEV Empire - Available Commands:"
	@echo "  install      Install dependencies"
	@echo "  setup        Complete environment setup"
	@echo "  compile      Compile smart contracts"
	@echo "  test         Run all tests"
	@echo "  lint         Run code quality checks"
	@echo "  format       Format code"
	@echo "  build        Build Docker images"
	@echo "  deploy       Deploy to production"
	@echo "  start        Start all services"
	@echo "  stop         Stop all services"
	@echo "  logs         View service logs"
	@echo "  backup       Backup data"
	@echo "  restore      Restore from backup"
	@echo "  clean        Clean build artifacts"

install:
	pip install -r requirements.txt
	npm install -g hardhat @openzeppelin/contracts

setup:
	./scripts/setup_infrastructure.py
	make install
	make compile

compile:
	cd contracts && npx hardhat compile
	python scripts/deploy_contracts.py --compile-only

test:
	pytest tests/ -v --cov=src --cov-report=html
	cd contracts && npx hardhat test

lint:
	flake8 src/ scripts/ tests/
	mypy src/
	black --check src/ scripts/ tests/

format:
	black src/ scripts/ tests/
	isort src/ scripts/ tests/

build:
	docker-compose build
	docker-compose pull

deploy:
	python scripts/deploy_empire.py --production
	docker-compose up -d

start:
	docker-compose up -d
	python scripts/start_strategies.py

stop:
	python scripts/emergency_stop.py --graceful
	docker-compose down

logs:
	docker-compose logs -f mev-empire

backup:
	python scripts/backup_system.py --full

restore:
	python scripts/backup_system.py --restore

clean:
	docker-compose down -v
	docker system prune -f
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -name "*.pyc" -delete
