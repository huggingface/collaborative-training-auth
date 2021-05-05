# Collaborative Hub Training Authentication API

Collaborative Hub Training Authentication API server-side machinery

## Overview

cf this [issue](https://github.com/learning-at-home/hivemind/issues/253)

API with fastapi & postgres database

## Developer guide

### Requirements for local development

-   Python 3.8
-   Docker (& docker-compose)

### Getting Started

Build & launch services with this command

```Bash
docker-compose up --build
```

Run tests

```Bash
docker exec -it redapi_server_1 pytest -vv
```
