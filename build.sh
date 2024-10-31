#!/usr/bin/env bash

set -o errexit

poetry install

poetry run python3 manage.py collectstatic --no-input
poetry run python3 manage.py migrate
poetry run python3 manage.py createsu
