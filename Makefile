MANAGE := poetry run python manage.py

build:
	./build.sh

# run local server
dev:
	$(MANAGE) runserver

# run production server
start:
	gunicorn task_manager.wsgi:application

# when you want to check code style with flake8
lint:
	poetry run flake8
	$(MANAGE) test

# create & show test-coverage for project in github
cov:
	poetry run coverage run --source='task_manager' manage.py test && poetry run coverage xml

# show all files with they test-coverage in %
test-cov:
	poetry run coverage run manage.py test && poetry run coverage report

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
	django-admin makemessages -a

# make all added translates is compiled
compile:
	django-admin compilemessages

# use path=<path to app> to check your home page for russian language
check lang:
	$(MANAGE) runserver & sleep 3 && curl http://127.0.0.1:8000/$(if $(path),$(path),)$(if $(path),/,) -H "Accept-Language: ru" && pkill -f "python3 manage.py runserver"
