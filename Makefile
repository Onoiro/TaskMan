MANAGE := poetry run python manage.py

dev:
	$(MANAGE) runserver

PORT ?= 10000
start:
	poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) task_manager.wsgi:application

render:
	$(MANAGE) migrate && gunicorn task_manager.wsgi:application

USERNAME ?= admin
EMAIL ?= t2way@yandex.ru
PASSWORD ?= admin
render createsuperuser:
	$(MANAGE) migrate && $(MANAGE) createsuperuser --username $(USERNAME) --email $(EMAIL) --noinput && $(MANAGE) changepassword $(USERNAME) $(PASSWORD) && gunicorn task_manager.wsgi:application

lint:
	poetry run flake8

install:
	poetry install

migrations:
	$(MANAGE) makemigrations

migrate:
	$(MANAGE) migrate

shell:
	$(MANAGE) shell

# use path=<path to app> to check your app for russian language
check lang:
	$(MANAGE) runserver & sleep 3 && curl http://127.0.0.1:8000/$(if $(path),$(path),)$(if $(path),/,) -H "Accept-Language: ru" && pkill -f "python3 manage.py runserver"
