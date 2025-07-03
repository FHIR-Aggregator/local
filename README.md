
# FHIR Aggregator Import System

This project launches a HAPI FHIR server and imports public datasets from Google Cloud Storage.

## Requirements
- Docker & Docker Compose

## Setting Up Docker & Docker Compose

If you are new to Docker, follow these official guides to install and configure Docker and Docker Compose:

- [Get Docker](https://docs.docker.com/get-docker/)
- [Install Docker Compose](https://docs.docker.com/compose/install/)

Once installed, you can verify Docker works by running:
```bash
docker --version
docker-compose --version
```
You should see version information for both.

If you're completely new to Docker, this beginner guide is also helpful:
- [Docker Overview](https://docs.docker.com/get-started/overview/)

## Quick Start

1. Launch the system:
```bash
docker-compose up --build
```
The FHIR server is accessible at:
```
http://localhost:8080/fhir
```

## Using the Importer Service

The importer code is located in the `importer/` directory. It has its own Docker image built using the included `importer/Dockerfile`. The `docker-compose.yml` is configured to build the importer from `./importer`.

To list available datasets:
```bash
docker-compose run importer list
```

Import all datasets (skipping legacy datasets by default):
```bash
docker-compose run importer import
```

To import only datasets matching a keyword (e.g., GTEx):
```bash
docker-compose run importer import --only GTEx
```


## Stopping the System
```bash
docker-compose down
```
To remove persistent data:
```bash
docker-compose down -v
```
