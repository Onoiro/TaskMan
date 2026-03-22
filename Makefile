MANAGE := poetry run python manage.py
DC := docker compose --env-file .env.docker

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

# linting
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
	poetry run coverage run --source='task_manager' manage.py test && poetry run coverage report --show-missing

# local migrations
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
# Docker commands (use .env.docker)
# ========================================

POSTGRES_USER := $(shell $(DC) exec db printenv POSTGRES_USER)
POSTGRES_DB := $(shell $(DC) exec db printenv POSTGRES_DB)

# start all services in background
up:
	$(DC) up -d

# stop all services
down:
	$(DC) down

# stop and remove containers, networks, volumes
down-clean:
	$(DC) down -v --remove-orphans

# restart all services
restart:
	$(DC) restart

# build images
d-build:
	$(DC) build

# build images without cache
build-no-cache:
	$(DC) build --no-cache

# rebuild and start
rebuild:
	$(DC) down && $(DC) build && $(DC) up -d

# view logs of all services
logs:
	$(DC) logs -f

# view Django logs
logs-web:
	$(DC) logs -f django-web

# view database logs
logs-db:
	$(DC) logs -f db

# Service status
status:
	$(DC) ps

# ========================================
# Commands for working inside containers
# ========================================

# enter Django container
d-bash:
	$(DC) exec django-web bash

# enter Django shell
d-shell:
	$(DC) exec django-web python manage.py shell

# enter database container
db-shell:
	$(DC) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# enter database container via bash
db-bash:
	$(DC) exec db bash

# ========================================
# Django commands via Docker
# ========================================

# create migrations
d-migrations:
	$(DC) exec django-web python manage.py makemigrations

# apply migrations
d-migrate:
	$(DC) exec django-web python manage.py migrate

# create superuser
d-createsu:
	$(DC) exec django-web python manage.py createsuperuser

# collect static files
d-collect:
	$(DC) exec django-web python manage.py collectstatic --no-input

# create translations
d-messages:
	$(DC) exec django-web python manage.py makemessages -a

# compile translations
d-compile:
	$(DC) exec django-web python manage.py compilemessages

# ========================================
# Database commands
# ========================================

# create database backup
d-backup:
	$(DC) exec db pg_dump -U $(POSTGRES_USER) -d $(POSTGRES_DB) > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql

# restore database from backup (use: make docker-restore BACKUP_FILE=backup_name.sql)
d-restore:
	$(DC) exec -T db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) < backups/$(BACKUP_FILE)

# reset database and reapply migrations
d-reset-db:
	$(DC) down
	docker volume rm $$(docker volume ls -q | grep postgres_data) || true
	$(DC) up -d db
	sleep 10
	$(DC) up -d django-web
	$(DC) exec django-web python manage.py migrate
	$(DC) exec django-web python manage.py createsuperuser

# ========================================
# Development commands
# ========================================

# full cycle: build, start, migrate, static, clean up, check
deploy:
	mkdir -p staticfiles
	$(DC) build
	$(DC) up -d
	sleep 5
	$(DC) exec django-web python manage.py migrate
	$(DC) exec django-web python manage.py collectstatic --no-input --clear

	@echo "=== Make rights on static files for Nginx ==="
	chmod -R o+rX staticfiles/

	@echo "=== Restart Django to reload staticfiles manifest ==="
	$(DC) restart django-web
	sleep 5
	
	@echo "=== Clear Docker-cache ==="
	docker system prune -f
	
	@echo "=== Check ==="
	$(DC) ps
	@echo ""
	@curl -sf -o /dev/null -w "HTTP Status: %{http_code}\n" http://127.0.0.1:8001/ || echo "WARNING: App not responding!"
	@echo ""
	@echo "=== Deploy complete at $$(date) ==="

# full redeploy use when: docker-compose.yml changes, DB image updates, or container state issues
# stops all containers, rebuilds images without cache, recreates from scratch 
redeploy:
	mkdir -p staticfiles
	$(DC) down
	$(DC) build --no-cache
	$(DC) up -d
	sleep 15
	$(DC) exec django-web python manage.py migrate
	$(DC) exec django-web python manage.py collectstatic --no-input --clear
	chmod -R o+rX staticfiles/
	$(DC) restart django-web
	sleep 5
	docker image prune -f
	docker builder prune -f
	$(DC) ps
	@echo "=== Full redeploy complete ==="

# quick start for development
d-dev:
	$(DC) up -d
	sleep 10
	$(DC) exec django-web python manage.py migrate

# clean unused Docker objects
d-clean:																																																																																																																																												
	docker system prune -f
	docker volume prune -f

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
	@echo ""
	@echo "Main Docker commands:"
	@echo "  up              - Start services"
	@echo "  down            - Stop services"
	@echo "  restart         - Restart services"
	@echo "  d-build         - Build images"
	@echo "  rebuild         - Rebuild and start"
	@echo "  logs            - View logs"
	@echo "  d-bash          - Enter Django container"
	@echo "  db-shell        - Enter database"
	@echo "  d-migrate       - Apply migrations"
	@echo "  d-backup        - Create database backup"
	@echo "  deploy          - Full deployment"
	@echo "  redeploy        - Full redeployment"
	@echo "  d-clean         - Clean Docker objects"
	@echo ""
	@echo "Additional Docker commands:"
	@echo "  down-clean      - Stop and remove containers, networks, volumes"
	@echo "  build-no-cache  - Build images without cache"
	@echo "  logs-web        - View Django logs"
	@echo "  logs-db         - View database logs"
	@echo "  status          - Service status"
	@echo "  d-shell         - Enter Django shell"
	@echo "  db-bash         - Enter database container via bash"
	@echo "  d-migrations    - Create migrations"
	@echo "  d-createsu      - Create superuser"
	@echo "  d-collect       - Collect static files"
	@echo "  d-messages      - Create translations"
	@echo "  d-compile       - Compile translations"
	@echo "  d-restore       - Restore database from backup"
	@echo "  d-reset-db      - Reset and recreate database"
	@echo "  d-dev           - Quick start for development"
	@echo "  d-clean-all     - Full Docker cleanup (WARNING!)"
	@echo "  d-space         - View Docker disk usage"
	@echo "  ps-all          - View all containers"
	@echo "  images          - View Docker images"
	@echo "  volumes         - View Docker volumes"
