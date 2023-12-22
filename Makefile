dev:
	poetry run python3 manage.py runserver

PORT ?= 10000
start:
	poetry run gunicorn -w 5 -b 0.0.0.0:$(PORT) task_manager.wsgi:application

lint:
	poetry run flake8

install:
	poetry install

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

shell:
	python manage.py shell

# use path=<path to app> to check your app for russian language
check lang:
	poetry run python3 manage.py runserver & sleep 3 && curl http://127.0.0.1:8000/$(if $(path),$(path),)$(if $(path),/,) -H "Accept-Language: ru" && pkill -f "python3 manage.py runserver"
