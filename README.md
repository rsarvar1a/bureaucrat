<img src="assets/banner.png">

### An all-in-one Discord application for Blood On The Clocktower, built for uWaterloo BOTC.

# Features

- text game management
- custom script generation
- storyteller feedback

# Installation

## Scriptmaker

Bureaucrat depends on [`scriptmaker`](https://www.github.com/rsarvar1a/scriptmaker), which has some extra dependencies.

1. Install the dependencies listed on `scriptmaker`'s README.
    - `apt install -y pango poppler-utils ghostscript`

## Bureaucrat

1. Ensure you have a compatible version of Python.
    - `apt install -y python3.12 pipx`

2. Install `poetry`, the python environment manager.
    - `pipx install poetry`

3. Clone this repository.
    - `git clone git@github.com:rsarvar1a/bureaucrat && cd bureaucrat`

4. Install Bureaucrat's dependencies.
    - `poetry install`

## PostgreSQL

1. Install PostgreSQL on your machine. It can be found in most package managers as `postgresql`.
    - `apt install -y postgresql`  

2. Create a user for Bureaucrat in `psql`; ensure it has sufficient permissions.
    - `postgres=# CREATE ROLE 'bureaucrat' WITH LOGIN PASSWORD 'password';`

3. Create a new database named `bureaucrat` or similar in `psql`. Ensure that its owner is the user you created in step 2.
    - `postgres=# CREATE DATABASE 'bureaucrat' WITH OWNER 'bureaucrat';`

4. Run migrations to populate the database.
    - `poetry run alembic upgrade head`

# Configuration

See `.env.example` for an example file.
