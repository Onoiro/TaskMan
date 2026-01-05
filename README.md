[![CI-check](https://github.com/Onoiro/TaskMan/actions/workflows/abo-check.yml/badge.svg)](https://github.com/Onoiro/TaskMan/actions/workflows/abo-check.yml)
[![Actions Status](https://github.com/Onoiro/TaskMan/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Onoiro/TaskMan/actions)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Onoiro_TaskMan&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Onoiro_TaskMan)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=Onoiro_TaskMan&metric=coverage)](https://sonarcloud.io/summary/new_code?id=Onoiro_TaskMan)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Onoiro_TaskMan&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Onoiro_TaskMan)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Onoiro_TaskMan&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Onoiro_TaskMan)

# [TaskMan](https://taskman.2-way.ru)
TaskMan is a web application designed to manage tasks individually or in teams (or families). It allows users to register, create teams, and effectively manage tasks with team-based isolation. The application is deployed and accessible at: https://taskman.2-way.ru

## Features

- **User Registration**: Users can register to create an account and log in to the TaskMan application.
- **Team Management**: Users can create teams and invite other users to join, or work independently without a team
- **Task Management**: Create tasks with detailed information including title and description
- **Team-Based Isolation**: All task-related entities (executors, statuses, labels) are isolated by team membership
- **Task Assignment**: Assign tasks to team members only*
- **Custom Task Status**: Create and manage custom task statuses (e.g., To Do, In Progress, Done) within your team
- **Labels**: Organize tasks with custom labels created by team members
- **Advanced Filtering**: Filter tasks by executors, statuses, and labels - all scoped to your team

## Language Support
The TaskMan application is available in two languages:
- **English**
- **Russian**

## Requirements
- **OS**: Linux (recommended)
- **Python**: ^3.11
- **Poetry**: ^1.2.2 (for non-Docker setup)
- **Docker Engine**: ^20.10 (for Docker setup)
- **Docker Compose**: ^2.0 (for Docker setup)

## Getting Started

The project includes an `.env.example` file in the repository root. You will use this as a template to create configuration files for different environments.

### Option 1: Docker Setup (Recommended)
**Prerequisites**
- Docker and Docker Compose installed on your system

**Quick Start**
```bash
# clone the repository:
git clone https://github.com/Onoiro/TaskMan.git
cd TaskMan

# create the Docker environment file from example:
cp .env.example .env.docker

# configure .env.docker:
# Open .env.docker and update the variables for production/docker environment:

# --- .env.docker example content ---
DEBUG=False
SECRET_KEY=generate_a_strong_secret_key_here
DJANGO_LANGUAGE_CODE=en-us

# Database settings (PostgreSQL)
POSTGRES_DB=taskman_db
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432

# Optional: Rollbar integration
# POST_SERVER_ITEM_ACCESS_TOKEN=your_token
# -----------------------------------

# Note: The Makefile commands for Docker automatically use .env.docker

# build and start the application for first time:

# build images
make d-build # docker compose build

# start all services in background
make up # docker compose up -d

# run database migrations
make d-migrate # docker compose exec django-web python manage.py migrate

# create superuser
make d-createsu # docker compose exec django-web python manage.py createsuperuser

# collect static files:
make d-collect # docker compose exec django-web python manage.py collectstatic --no-input
```
**Access the application**:
Open your browser and navigate to: http://localhost:8001

**Docker Management Commands**
```bash
make up # start services
make down # stop services
make logs # view logs
make restart # restart services
make deploy # rebuild and deploy
make d-bash # enter Django container
make db-shell # access database
make d-backup # create database backup
make help # view all available commands
```

### Option 2: Traditional Setup (Without Docker)
**Prerequisites**
- Python 3.11 or higher
- Poetry 1.2.2 or higher
- PostgreSQL (for production) or SQLite (for development included)

**Setup Steps**
```bash
# clone the repository:
git clone https://github.com/Onoiro/TaskMan.git
cd TaskMan

# create the local environment file from example:
cp .env.example .env

# configure environment variables in .env:

# Open .env and ensure it is set for local development:

# --- .env example content ---
DEBUG=True
SECRET_KEY=dev_secret_key
DJANGO_LANGUAGE_CODE=en-us
ADMIN_PASSWORD=admin
DATABASE_URL=sqlite:///db.sqlite3
# if you use postgresql instead of sqlite, add the following
# DATABASE_URL=postgresql://your_db_user:your_password@localhost:5432/your_db_name
# ----------------------------

# install dependencies and setup database:
make build

# run local development server:
make dev
```
**Access the application**:
Open your browser and navigate to: http://127.0.0.1:8001/

**Traditional Management Commands**
```bash
make dev # run development server
make start # run production server
make test # run tests
make lint # check code style
make migrations # create migrations
make migrate # apply migrations
make messages # create translations
make compile # compile translations
make shell # access Django shell
```

## Team-Based Workflow

TaskMan implements a team-based isolation system:
- **Teams**: Users can create teams and invite other members
- **Task Isolation**: When creating or editing tasks, only team members are available as executors
- **Status & Labels**: Custom statuses and labels are shared only within team members
- **Filtering**: Task filters show only values created by team members
- **Independent Work**: Users can also work independently without joining any team

## Development

### Code Quality
```bash
# check code style
make lint
# run tests
make test
# generate test coverage
make test-cov
```
### Database Operations
```bash
# create new migrations
make migrations  # or make d-migrations for Docker
# apply migrations
nake migrate     # or make d-migrate for Docker
# access database shell
make shell       # or make db-shell for Docker
```
### Internationalization
```bash
# extract translatable strings
make messages    # or make d-makemessages for Docker
# compile translations
make compile     # or make d-compilemessages for Docker
```
### Production Deployment

For production deployment with Docker:
- **Configure production environment variables**
Ensure your .env.docker file contains production values (DEBUG=False, strong SECRET_KEY).
- **Use the deploy command**:
```bash
make deploy
# docker compose down
# docker compose build
# docker compose up -d
# sleep 15
# docker compose exec django-web python manage.py migrate
# docker compose exec django-web python manage.py collectstatic --no-input
# docker compose exec django-web python manage.py compilemessages
```
This command will:
- Stop existing containers
- Rebuild images
- Start services
- Run migrations
- Collect static files
- Compile translations

### Database Backup and Restore
```bash
# create backup
make d-backup
# restore from backup
make d-restore BACKUP_FILE=backup_filename.sql
# reset database completely
make d-reset-db
```

## Troubleshooting
**Docker Issues**
```bash
# check service status:
make status
# view logs:
make logs
# or:
make logs-web
# clean Docker objects:
make d-clean
# check disk usage:
make d-space
```
**Common Solutions**
- If using Docker commands, ensure .env.docker exists and is configured correctly.
- If using local 'make dev', ensure .env exists and is configured correctly.
- For database connection issues, ensure PostgreSQL container is healthy ('make status').
- Use 'make help' to see all available commands

### Contributing
- Fork the repository
- Create a feature branch
- Make your changes
- Run tests and linting
- Submit a pull request

### License
This project is licensed under the MIT License.

### Links
- Live Application: https://taskman.2-way.ru
- Repository: https://github.com/Onoiro/taskman
- Author: Andrey Bogatyrev <mailto:donoriono@gmail.com>
