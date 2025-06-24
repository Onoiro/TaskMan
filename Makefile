MANAGE := poetry run python manage.py

# install dependenciess, collect static, run migrations, create superuser
build:
	./build.sh

# run local server
dev:
	$(MANAGE) runserver 8001

# run production server
PORT ?= 8001
start:
	poetry run gunicorn -w 4 -b localhost:$(PORT) task_manager.wsgi:application

# when you want to check code style with flake8
lint:
	poetry run flake8

# run tests
test:
	$(MANAGE) test

# create & show test-coverage for project in github
cov:
	poetry run coverage run --source='task_manager' manage.py test && poetry run coverage xml

# show all files with they test-coverage in %
test-cov:
	poetry run coverage run --source='task_manager' manage.py test && poetry run coverage report

# run local migrations
migrations:
	$(MANAGE) makemigrations

# run local migrate
migrate:
	$(MANAGE) migrate

# when you want to operate with local DB
shell:
	$(MANAGE) shell

# add all strings to translate to task_manager/locale/ru/LC_MESSAGES/django.po
messages:
	cd task_manager && django-admin makemessages -a

# make all added translates is compiled
compile:
	cd task_manager && django-admin compilemessages

# ========================================
# Docker commands
# ========================================

POSTGRES_USER := $(shell docker compose exec db printenv POSTGRES_USER)
POSTGRES_DB := $(shell docker compose exec db printenv POSTGRES_DB)

# start all services in background
up:
	docker compose up -d

# stop all services
down:
	docker compose down

# stop and remove containers, networks, volumes
down-clean:
	docker compose down -v --remove-orphans

# restart all services
restart:
	docker compose restart

# build images
d-build:
	docker compose build

# build images without cache
build-no-cache:
	docker compose build --no-cache

# rebuild and start
rebuild:
	docker compose down && docker compose build && docker compose up -d

# view logs of all services
logs:
	docker compose logs -f

# view Django logs
logs-web:
	docker compose logs -f django-web

# view database logs
logs-db:
	docker compose logs -f db

# Service status
status:
	docker compose ps

# ========================================
# Commands for working inside containers
# ========================================

# enter Django container
d-shell:
	docker compose exec django-web bash

# enter Django shell
d-django-shell:
	docker compose exec django-web python manage.py shell

# enter database container
db-shell:
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# enter database container via bash
db-bash:
	docker compose exec db bash

# ========================================
# Django commands via Docker
# ========================================

# create migrations
d-migrations:
	docker compose exec django-web python manage.py makemigrations

# apply migrations
d-migrate:
	docker compose exec django-web python manage.py migrate

# create superuser
d-createsuperuser:
	docker compose exec django-web python manage.py createsuperuser

# collect static files
d-collectstatic:
	docker compose exec django-web python manage.py collectstatic --no-input

# create translations
d-messages:
	docker compose exec django-web python manage.py makemessages -a

# compile translations
d-compile:
	docker compose exec django-web python manage.py compilemessages

# ========================================
# Database commands
# ========================================

# create database backup
d-backup:
	docker compose exec db pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql

# restore database from backup (use: make docker-restore BACKUP_FILE=backup_name.sql)
d-restore:
	docker compose exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) < backups/$(BACKUP_FILE)

# reset database and reapply migrations
d-reset-db:
	docker compose down
	docker volume rm $$(docker volume ls -q | grep postgres_data) || true
	docker compose up -d db
	sleep 10
	docker compose up -d django-web
	docker compose exec django-web python manage.py migrate
	docker compose exec django-web python manage.py createsuperuser

# ========================================
# Development commands
# ========================================

# full cycle: stop, build, start, migrate
deploy:
	docker compose down
	docker compose build
	docker compose up -d
	sleep 15
	docker compose exec django-web python manage.py migrate
	docker compose exec django-web python manage.py collectstatic --no-input
	docker compose exec django-web python manage.py compilemessages

# quick start for development
d-dev-start:
	docker compose up -d
	sleep 10
	docker compose exec django-web python manage.py migrate

# clean unused Docker objects
d-clean:
	docker system prune -f
	docker volume prune -f
	docker image prune -f

# full cleanup (CAUTION - removes ALL unused Docker objects)
d-clean-all:
	docker system prune -a -f --volumes

# ========================================
# Information commands
# ========================================

# show Docker disk usage
d-space:
	docker system df

# show all containers (including stopped)
ps-all:
	docker ps -a

# show Docker images
images:
	docker images

# show Docker volumes
volumes:
	docker volume ls

# help for Docker and non-Docker commands
help:
	@echo "Main Docker commands:"
	@echo "  up              - Start services"
	@echo "  down            - Stop services"
	@echo "  restart         - Restart services"
	@echo "  d-build         - Build images"
	@echo "  rebuild         - Rebuild and start"
	@echo "  logs            - View logs"
	@echo "  d-shell         - Enter Django container"
	@echo "  db-shell        - Enter database"
	@echo "  d-migrate       - Apply migrations"
	@echo "  d-backup        - Create database backup"
	@echo "  deploy          - Full deployment"
	@echo "  d-clean         - Clean Docker objects"
	@echo ""
	@echo "Additional Docker commands:"
	@echo "  down-clean      - Stop and remove containers, networks, volumes"
	@echo "  build-no-cache  - Build images without cache"
	@echo "  logs-web        - View Django logs"
	@echo "  logs-db         - View database logs"
	@echo "  status          - Service status"
	@echo "  d-django-shell  - Enter Django shell"
	@echo "  db-bash         - Enter database container via bash"
	@echo "  d-migrations    - Create migrations"
	@echo "  d-createsuperuser - Create superuser"
	@echo "  d-collectstatic - Collect static files"
	@echo "  d-messages      - Create translations"
	@echo "  d-compile       - Compile translations"
	@echo "  d-restore       - Restore database from backup"
	@echo "  d-reset-db      - Reset and recreate database"
	@echo "  d-dev-start     - Quick start for development"
	@echo "  d-clean-all     - Full Docker cleanup (WARNING!)"
	@echo "  d-space         - View Docker disk usage"
	@echo "  ps-all          - View all containers"
	@echo "  images          - View Docker images"
	@echo "  volumes         - View Docker volumes"
	@echo ""
	@echo "Available non-Docker commands:"
	@echo "  build           - Install dependencies, collect static, migrations, superuser"
	@echo "  dev             - Run local server"
	@echo "  start           - Run production server"
	@echo "  lint            - Code style check with flake8"
	@echo "  test            - Run tests"
	@echo "  cov             - Create test coverage report"
	@echo "  test-cov        - Show test coverage in %"
	@echo "  migrations      - Create migrations"
	@echo "  migrate         - Apply migrations"
	@echo "  shell           - Enter Django shell"
	@echo "  messages        - Create translation files"
	@echo "  compile         - Compile translations"
