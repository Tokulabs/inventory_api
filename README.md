# Signos POS API

This repo contains all services for the Signos POS Project

## Setup

### Prerequesites
- Python3
- Pip
- Docker
- pgAdmin

### Set up Virtual Environment
Install virtual env and project dependencies

```
pip install venv
python3 -m venv ./venv
source venv/bin/activate
pip install -r requirements.txt
```

### Set up local database
1. Create local db in docker
    ```
    cd db
    docker-compose up
    ```

2. Access db from pgadmin
    - host, user, password as in ./db/docker-compose.yml
    - database: postgresql

3. Create database with on a sql file and execute: 
    ```
    CREATE DATABASE inventory_db
    ```

4. Create database and structure
    ```
    python3 manage.py migrate
    python3 manage.py runserver
    ```