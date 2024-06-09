[![Actions Status](https://github.com/Onoiro/python-project-52/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/Onoiro/python-project-52/actions)
[![Maintainability](https://api.codeclimate.com/v1/badges/3c6f1330d7e0f614ccb3/maintainability)](https://codeclimate.com/github/Onoiro/python-project-52/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/3c6f1330d7e0f614ccb3/test_coverage)](https://codeclimate.com/github/Onoiro/python-project-52/test_coverage)

## Welcome to [Task manager](https://task-manager-wh08.onrender.com)
Task Manager is a web application designed to facilitate task management within an organization or team. It allows users to register, create, and manage tasks efficiently. Key features include:

### Features

- **User Registration**: Users can register to create an account and log in to the Task Manager application.
- **Task Creation**: Users can create tasks with details such as title and description.
- **Assign Task**: Each task can be assigned to a specific user who will be responsible for completing it.
- **Task Status**: Tasks can have various and custom statuses (e.g., To Do, In Progress, Done), making it easy to track progress.
- **Labels**: Tasks can be tagged with labels for better organization and filterability.

### Getting Started

To get started with the Task Manager, follow these steps:
```bash
# clone the repository:
git clone git@github.com:Onoiro/python-project-52.git

# navigate to the project directory:
cd python-project-52

# install dependencies, migrate a database, create superuser for admin:
make build

# create .env file contains environment variables:
touch .env

# open .env file for edit:
nano .env

# specify environment variables in .env, for example:
DEBUG=True
DATABASE_URL=postgresql://user:password@connect_url/database
SECRET_KEY="secret_key"

# run app in development mode on local web server:
make dev

# run production:
make start

# check code style with flake8:
make lint

# run tests:
make test

# more helpful service commands can be found in Makefile
```
### Requirements
* OS Linux  
* python = ^3.8.1
* poetry = ^1.2.2
