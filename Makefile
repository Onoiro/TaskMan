MANAGE := poetry run python manage.py

build:
	./build.sh

dev:
	$(MANAGE) runserver

start:
	gunicorn task_manager.wsgi:application

lint:
	poetry run flake8

test:
	$(MANAGE) test

cov:
	poetry run coverage run --source='task_manager' manage.py test && poetry run coverage xml

test-cov:
	poetry run coverage run manage.py test && poetry run coverage report


migrations:
	$(MANAGE) makemigrations

migrate:
	$(MANAGE) migrate

shell:
	$(MANAGE) shell

# use path=<path to app> to check your app for russian language
check lang:
	$(MANAGE) runserver & sleep 3 && curl http://127.0.0.1:8000/$(if $(path),$(path),)$(if $(path),/,) -H "Accept-Language: ru" && pkill -f "python3 manage.py runserver"
