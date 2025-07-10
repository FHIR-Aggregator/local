
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
 ✔ Container fhir-aggregator-import-db-1           Running                                                    0.0s 
 ✔ Container fhir-aggregator-import-fhir-server-1  Runnin...                                                  0.0s 
🔍 Discovering datasets...

Available datasets:
- FHIRIZED-1KGENOMES/META (Size: 14.83 MB)
- FHIRIZED-CDA/META (Size: 1920.23 MB)
- FHIRIZED-CELLOSAURUS/META (Size: 2.98 MB)
- FHIRIZED-GDC/META (Size: 5076.96 MB)
- FHIRIZED-GTEX/META (Size: 165.15 MB)
- FHIRIZED-HTAN/META (Size: 1720.20 MB)
- FHIRIZED-ICGC/META (Size: 36.23 MB)
- IG/META (Size: 0.02 MB)
```

> Note: IG/META is an "Implementation Guide" dataset, which used to setup the FHIR server with the necessary resources and profiles. It is not a dataset in the traditional sense.

Import all datasets (skipping legacy datasets by default):
```bash
docker-compose run importer import
```

To import only datasets matching a keyword (e.g., 1KGENOMES):
```bash
docker-compose run importer import --only FHIRIZED-1KGENOMES/META

```


## Stopping the System
```bash
docker-compose down
```
To remove persistent data:
```bash
docker-compose down -v
```

## Using the FHIR Server

Specify the endpoint:
```bash
export FHIR_BASE=http://localhost:8080/fhir
```

See [GraphDefinitions](https://colab.research.google.com/drive/1G1c_2gNNUdicFWeImN2_zFAjmSwfewYI?usp=drive_link)
You can interact with the FHIR server using any FHIR client or tools like Postman.

Now that you have the endpoint, if you are comfortable with FHIR, that is all you need. For example:

This query returns the official identifier for all ResearchStudy resources.

* $FHIR_BASE is the environment variable we set earlier, which holds the FHIR server's base URL. It's expanded to the actual URL during execution.
* /ResearchStudy is the FHIR resource type we are interested in (in this case, "ResearchStudy").
* ?_elements=identifier is a FHIR search parameter that limits the returned data to only include the 'identifier' element of the ResearchStudy resources.

Example query:
```bash
curl -s $FHIR_BASE'/ResearchStudy?_elements=identifier&identifier.use=official' | jq -rc '.entry[] | [ (.resource.identifier[] | .value), .fullUrl]' | sort
```

For more see [FHIR Aggregator Documentation](https://fhir-aggregator.readthedocs.io/en/latest/#fhir-query-your-fhir-querying-assistant)