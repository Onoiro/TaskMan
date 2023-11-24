dev:
	poetry run python3 manage.py runserver

lint:
	poetry run flake8

install:
	poetry install
