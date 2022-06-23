# xFusion Operator Catalog API

## Instructions

Edit .env file and adjust values as necessary:
- export XFUSION_API_PORT=8000
- export MONGODB_PORT=27017
- export MONGODB_HOST=mongodb

## DEVELOPMENT

Create container for API:
- docker-compose up -d --build
- docker-compose down

# api/main.py line 41
# MongoDB connection string, defined in ENVIRONMENT variables
mongodb_conn = (
    # During DEV
    # f'mongodb://{os.environ.get("MONGODB_USER")}:{os.environ.get("MONGODB_PASS")}@{os.environ.get("MONGODB_HOST")}'
    # During PROD
    f'mongodb://{"xfadmin"}:{"admin123#"}@{"10.200.10.250"}:{"28050"}'
)

## Docs in Open API format

http://localhost:${XFUSION_API_PORT}/docs

## Unit Testing

https://www.sealights.io/agile-testing/test-metrics/python-code-coverage/

Coverage.py
Coverage.py is one of the most popular code coverage tools for Python. It uses code analysis tools and tracing hooks provided in Python standard library to measure coverage.

Pytest-cov
Pytest-cov is a Python plugin to generate coverage reports. In addition to functionalities supported by coverage command, it also supports centralized and distributed testing. It also supports coverage of subprocesses.

FULL COVERAGE ANALYSIS
docker exec -it xfusion-python-api pytest --cov /app --cov-branch --cov-report term-missing

BASIC COVERAGE ANALYSIS
docker exec -it xfusion-python-api pytest --cov=/app

https://fastapi.tiangolo.com/tutorial/testing/
https://medium.com/fastapi-tutorials/testing-fastapi-endpoints-f7e78f09b7b6
https://testdriven.io/blog/fastapi-crud/
https://www.jeffastor.com/blog/testing-fastapi-endpoints-with-docker-and-pytest

## Postman

Environment:
xfusion_python_api_postman_environment.json

Collection por Operator Catalog:
xfusion_python_api_postman_collection.json

Collection por GitHub Connector:
xfusion_python_api_postman_collection.json

## Upload Operators

### 4 scenarios

MULTIPLE FILES
+ 1 file
+ multiples files

ONE ZIP FILE
+ 1 folder => 1 zip
+ 1 zip file

## Test Repository

sergiomar73+xfusion.customer.1@gmail.com
sergiomar73+xfusion.customer.2@gmail.com

xfusion2021
# Data_pipelineV2
# Data_pipelineV2
# Data_pipelineV2
# Data_pipelineV2
