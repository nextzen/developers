# Nextzen Developers

Developer portal for managing Nextzen tile service API keys. Deployed as an AWS Lambda function using [Zappa](https://github.com/zappa/Zappa).

**Note:** Nextzen is no longer accepting new signups. The service is winding down.

## Setup

Requires [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

## Local Development

```bash
uv run python wsgi_server.py
```

## Deployment

Deploy to dev:

```bash
uv run zappa update dev
```

Deploy to production:

```bash
uv run zappa update prod
```
