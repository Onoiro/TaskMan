[![CI-check](https://github.com/Onoiro/TaskMan/actions/workflows/abo-check.yml/badge.svg)](https://github.com/Onoiro/TaskMan/actions/workflows/abo-check.yml)
[![Actions Status](https://github.com/Onoiro/TaskMan/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Onoiro/TaskMan/actions)
[![Maintainability](https://qlty.sh/badges/8be7044b-186e-41ec-94eb-26e8be04d42b/maintainability.svg)](https://qlty.sh/gh/Onoiro/projects/TaskMan)
[![Test Coverage](https://api.codeclimate.com/v1/badges/3c6f1330d7e0f614ccb3/test_coverage)](https://codeclimate.com/github/Onoiro/TaskMan/test_coverage)

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=abo>&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=abo)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=abo&metric=coverage)](https://sonarcloud.io/summary/new_code?id=abo)

# [TaskMan](https://taskman.2-way.ru)
TaskMan is a web application designed to manage tasks in organizations and teams. It allows users to register, create teams, and effectively manage tasks with team-based isolation. The application is deployed and accessible at: https://taskman.2-way.ru

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
- **Python**: ^3.8.1
- **Poetry**: ^1.2.2 (for non-Docker setup)
- **Docker Engine**: ^20.10 (for Docker setup)
- **Docker Compose**: ^2.0 (for Docker setup)

## Getting Started

### Option 1: Docker Setup (Recommended)
**Prerequisites**
- Docker and Docker Compose installed on your system

**Quick Start**
```bash
# clone the repository:
git clone https://github.com/Onoiro/TaskMan.git
cd TaskMan

# create environment variables file:
touch .env

# configure environment variables in .env:

# database settings
DATABASE_URL=postgresql://your_db_user:your_password@db:5432/your_db_name
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432
# django settings
SECRET_KEY=your_secret_django_key
DEBUG=False
# optional: Rollbar integration
ROLLBAR_ACCESS_TOKEN=your_rollbar_token

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
- Python 3.8.1 or higher
- Poetry 1.2.2 or higher
- PostgreSQL (for production) or SQLite (for development included)

**Setup Steps**
```bash
# clone the repository:
git clone https://github.com/Onoiro/TaskMan.git
cd TaskMan

# create environment variables file:
touch .env

# configure environment variables in .env:

# for development (SQLite)
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
SECRET_KEY=your_secret_key
DJANGO_LANGUAGE_CODE=en-us

# for production (PostgreSQL)
DEBUG=False
DATABASE_URL=postgresql://your_db_user:your_password@localhost:5432/your_db_name
SECRET_KEY=your_secret_key

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
- If containers fail to start, check your .env file configuration
- For database connection issues, ensure PostgreSQL container is healthy
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
