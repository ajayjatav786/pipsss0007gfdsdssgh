cd mongodb/
docker-compose up -d
docker-compose down

docker-compose -f docker-compose-mongodb.yml --env-file .env-mongodb up -d
docker-compose -f docker-compose-mongodb.yml --env-file .env-mongodb down

# TODO 

# Check if repo non existant
if repo_name not in [r.name for r in user.get_repos()]:
    # Create repository
    user.create_repo(repo_name)

# Cuentas de prueba de GitHub

-------------------------------------------------
https://github.com/xfusiontest01?tab=repositories

user:   xfusiontest01
pass:   xfusion2021

Access Test for sergio 2
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

-------------------------------------------------
https://github.com/xfusiontest02?tab=repositories

user:   xfusiontest02
pass:   xfusion2021

-------------------------------------------------

## GitHub topics

Error saving your changes: Repository topics Topics must start with a lowercase letter or number, consist of 35 characters or less, and can include hyphens.

# Apache Airflow Parser

git clone https://github.com/apache/airflow.git
cd airflow/
git checkout tags/2.1.0
mkdir /home/sergio/huenei/xfusion_python_back/airflow/v2/
cp -r airflow/ /home/sergio/huenei/xfusion_python_back/airflow/v2/
cp CHANGELOG.txt /home/sergio/huenei/xfusion_python_back/airflow/v2/

## Container for MongoDB

docker-compose -f docker-compose-mongodb.yml --project-name xfusion-mongodb up -d 
docker-compose -f docker-compose-mongodb.yml --project-name xfusion-mongodb down

docker-compose -f docker-compose-mongodb.yml up -d 
docker-compose -f docker-compose-mongodb.yml down

## Container for API

docker-compose up --build -d
docker-compose down

## Dependencies

pip install fastapi
pip install uvicorn[standard]
pip install pylint
pip install python-dotenv
pip install pymongo
pip install black

## Setup with Docker Compose

1) Create folder "airflow" anywhere in the filesystem
2) Create folder "mongodbdata" anywhere in the filesystem
3) Copy "airflow-versions.json" inside this "airflow" folder
4) Edit docker-compose.yml and adjust:
   Line 18 => - {PATH TO mongodbdata folder}:/data/db
   Line 43 => - {PATH TO airflow folder}:/mnt/airflow
5) Run with : docker-compose up -d
6) Stop with: docker-compose down

## Debug (after running with Docker Compose)

1) Create new Python Environment
2) Enter this env
3) Install requirements inside env
4) Run with: python api/app.py

docker-compose up --build -d
docker-compose down

MongoDB Express
http://localhost:8081/

Flask API
http://localhost:5000/

## Modules

### According Airflow

* Operators: determine what actually gets done by a task
* Sensors: are special types of operators whose purpose is to wait on some external or internal trigger
* Hooks: provides a uniform interface to access external services

## According Astronomer

* Hooks: (inherits from BaseHook)
* Log: (inherits from FileTaskHandler and LoggingMixin, or logging.Handler)
* Operators: (inherits from BaseOperator)
* Secrets: (inherits from BaseSecretsBackend)
* Sensors: (inherits from BaseSensorOperator)
* Transfers: (inherits from BaseOperator)

## Find in files

grep -Ril "LocalFilesystemBackend" airflow/

## PIP

python -m pip freeze > requirements.txt

### Queries

Flatten nested array in mongodb
https://gist.github.com/usametov/2aa98d5d66bf1d650f3032691cadf0f8

Distinct
https://www.tutorialspoint.com/mongodb-query-to-get-only-distinct-values

### MongoDB with Docker

https://www.bmc.com/blogs/mongodb-docker-container/

https://marioyepes.com/mongodb-express-using-docker/

docker build -t xfusion-python-api:latest .

https://vsupalov.com/docker-arg-env-variable-guide/
docker run -e "env_var_name=another_value" alpine env
docker run -e env_var_name alpine env
docker run --env-file=env_file_name alpine env
=> docker run --env-file=.env xfusion-python-api:latest xfusion-python-api

docker-compose up -d
WARNING: Image for service api was built because it did not already exist. To rebuild this image you must use docker-compose build
docker-compose up --build
docker-compose down

docker container prune

Check MongoDB
mongo localhost:27017/admin -u xfusion -p xfusion

docker exec -it mongodb bash
mongo -u xfusion -p xfusion

docker exec -it xfusion-python-api /bin/sh

show dbs
use catalog
db.createCollection("operators")
db.operators.insertOne({name: "banana", origin: "brazil", price: 10})
db.operators.insertMany([ {name: "apple", origin: "usa", price: 5}, {name: "orange", origin: "italy", price: 3}, {name: "mango", origin: "malaysia", price: 3} ])

https://docs.mongodb.com/manual/reference/method/db.collection.find/#db.collection.find
db.operators.find().pretty()
db.operators.find({origin: "brazil"})
db.operators.find({price: { $gt: 4 }})

exit

docker logs mongodb

### Schema validation

https://docs.mongodb.com/manual/core/schema-validation/

## Flask

flask run

https://medium.com/swlh/how-to-set-up-a-react-app-with-a-flask-and-mongodb-backend-using-docker-19b356180199

## Testing

### Hierarchies

BigQueryCheckOperator
	_BigQueryDbHookMixin
	SQLCheckOperator
		BaseSQLOperator
			BaseOperator
				Operator
				LoggingMixin
				TaskMixin


### TODO

xFusion_unfold: Unkown instance <_ast.Ellipsis object at 0x7f38000816a0>

#### Check all BAD types

- DynamoDBToS3Operator    process_func    Callable[,bytes] => should be: Callable[[Dict[str, Any]], bytes]

python parser/parser.py airflow/airflow/operators/bash.py

python parser/parser.py airflow/airflow/operators/python.py

python parser/parser.py airflow/airflow/providers/google/cloud/operators/bigquery.py

airflow/providers/google/cloud/operators/bigquery.py
    class _BigQueryDbHookMixin: => EMPTY
    BigQueryCheckOperator(_BigQueryDbHookMixin, SQLCheckOperator)

airflow/airflow/operators/sql.py
    class BaseSQLOperator(BaseOperator):
    class SQLCheckOperator(BaseSQLOperator):

airflow/airflow/models/baseoperator.py
    class BaseOperator(Operator, LoggingMixin, TaskMixin, metaclass=BaseOperatorMeta):

## References

### FastAPI

https://python.plainenglish.io/3-ways-to-handle-errors-in-fastapi-that-you-need-to-know-e1199e833039

### Python modules

Python filenames are not module names:
https://stackoverflow.com/questions/7948494/whats-the-difference-between-a-python-module-and-a-python-package/49420164#49420164

### Python arguments

https://www.python.org/dev/peps/pep-3102/

The second syntactical change is to allow the argument name to
be omitted for a varargs argument. The meaning of this is to
allow for keyword-only arguments for functions that would not
otherwise take a varargs argument:

    def compare(a, b, *, key=None):
        ...

Bare * is used to force the caller to use named arguments - so you cannot define a function with * as an argument when you have no following keyword arguments.

All positional (unnamed) arguments, including *args, must occur before the bare *

* is in place of *args, and vice-versa; they can't coexist in a signature. That's why they chose *; previously, *args was the only way to force purely positional arguments, and it marked the end of arguments which could be passed positionally (since it collected all remaining positional arguments, they could reach the following named arguments). * means the same "positional arguments can't go beyond here", but the lack of a name means "but I won't accept them at all, because I chose not to provide a place to put them"

https://www.digitalocean.com/community/tutorials/how-to-use-args-and-kwargs-in-python-3#

When ordering arguments within a function or function call, arguments need to occur in a particular order:
- Formal positional arguments
- *args
- Keyword arguments
- **kwargs
