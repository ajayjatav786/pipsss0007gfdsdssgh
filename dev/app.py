import os
import json
import datetime
from typing import Optional
from flask import Flask, jsonify, make_response, request, abort, Response
from flask_cors import CORS
from parser import Parser
import bson.objectid
from dotenv import load_dotenv

load_dotenv()


class MongoDBEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, bson.objectid.ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def custom_error(message, status_code):
    return make_response(jsonify(message), status_code)


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["CORS_HEADERS"] = "Content-Type"

# Custom JSON encoder for Flask
# https://gist.github.com/claraj/3b2b95a62c5ba6860c03b5c737c214ab
app.json_encoder = MongoDBEncoder

# Root folder relative inside Docker container
ROOT_FOLDER = f"../airflow/"

# MongoDB connection string, defined in ENVIRONMENT variables
mongodb_conn = (
    f'mongodb://{os.environ.get("MONGODB_USER")}:{os.environ.get("MONGODB_PASS")}@{os.environ.get("MONGODB_HOST")}'
)


@app.route("/")
def home():
    return """
    <body style="height: 100%; position: relative">
        <div style="margin: 0; position: absolute; top: 50%; left: 50%; margin-right: -50%; transform: translate(-50%, -50%);">
            <h1 style="font-family: Calibri;">xFusion Operator Catalog API</h1>
        </div>
    </body>
    """


@app.route("/stats", methods=["GET"])
@app.route("/stats/<version>", methods=["GET"])
def get_stats(version: Optional[str] = None):
    """Return stats about the Catalog"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    stats = parser.get_stats(version)
    return jsonify(stats)


@app.route("/modules/<version>", methods=["GET"])
def modules(version: str):
    """Returns a list with the available modules"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    modules = parser.get_distinct_modules(version)
    return jsonify(modules)


@app.route("/types/<version>", methods=["GET"])
def types(version: str):
    """Returns a list with the distinct types"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    types = parser.get_distinct_types(version)
    return jsonify(types)


@app.route("/operators/<version>", methods=["GET"])
def get_operators(version: str):
    """Return full listing of Operators"""
    mode = "tree"
    args = request.args
    if "mode" in args:
        mode = args["mode"]
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    if mode == "list":
        operators = parser.get_operators_list(version)
    elif mode == "original-lite":
        operators = parser.get_operators_list_original(version, mode="lite")
    elif mode == "original-full":
        operators = parser.get_operators_list_original(version, mode="full")
    elif mode == "nested":
        operators = parser.get_operators_nested(version)
    elif mode == "treev2":
        operators = parser.get_operators_tree_v2(version)
    else:  # "tree"
        operators = parser.get_operators_tree(version)
    return jsonify(operators)


@app.route("/operators/<version>/search", methods=["GET"])
def get_operators_search(version: str):
    """Return full listing of Operators with parameters of specif types"""
    args = request.args
    if "type" not in args:
        return custom_error({"message": f"Url should contains => search?type=(part of desired data type)"}, 400)
    target_type = args["type"]
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    operators = parser.get_operators_search_parameters_type(version, target_type)
    return jsonify(operators)


@app.route("/operators/<version>/<operator_id>", methods=["GET"])
def get_operator(version: str, operator_id: str):
    """Returns individual Operator"""
    debugging = "debug" in request.args
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    operator = parser.get_operator(version, operator_id, debugging)
    if not operator:
        return custom_error({"message": f"Operator {version}.{operator_id} not found."}, 404)
    return jsonify(operator)


@app.route("/operators/<version>/<operator_id>/tree", methods=["GET"])
def get_operator_tree(version: str, operator_id: str):
    """Returns individual Operator"""
    parser = Parser(ROOT_FOLDER, mongodb_conn)
    operator = parser.get_operator_tree(version, operator_id)
    if not operator:
        return custom_error({"message": f"Operator {version}.{operator_id} not found."}, 404)
    return jsonify(operator)


@app.route("/catalog/<version>/<source>", methods=["POST"])
def post_catalog(version: str, source: str):
    """Parse Operators from Airflow, Providers, UDP and Customer"""
    # print(f'post_catalog(version: "{version}", source: "{source}")')
    source = source.lower()
    if source not in ["airflow", "providers", "udp"]:
        return custom_error({"message": f"Source should be: airflow | providers | udp"}, 400)
    parser = create_parser(verbose=False)
    parser.delete_catalog_by_source("catalog", "operators", version, source)
    response = parser.scan(version=version, source=source)
    return {"message": f"{source} {version} operators parsed successfully. {response}"}


@app.route("/catalog", methods=["DELETE"])
@app.route("/catalog/<version>", methods=["DELETE"])
def delete_all(version: Optional[str] = None):
    """Deletes all operators in Catalog"""
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    res = parser.delete_catalog("catalog", "operators", version)
    return {"message": res}


@app.route("/catalog/<version>/<source>", methods=["DELETE"])
def delete_airflow(version: str, source: str):
    """Deletes operators from Airflow/Providers/UDP"""
    source = source.lower()
    if source not in ["airflow", "providers", "udp"]:
        return custom_error({"message": f"Source should be: airflow | providers | udp"}, 400)
    parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=False)
    res = parser.delete_catalog_by_source("catalog", "operators", version, source)
    return {"message": res}


@app.route("/catalog/init", methods=["POST"])
def init_airflow_folder():
    """Initializes Airflow folders with defined major versions"""
    res = do_init_airflow_folder()
    if res == "":
        return {"message": "Operator Catalog initialized successfully."}
    return custom_error({"message": res}, 500)


def do_init_airflow_folder() -> str:
    """Updates Airflow folders with defined major versions"""
    parser = create_parser(on_error_abort=False)
    if type(parser) is str:
        print(parser)
    else:
        try:
            parser.init_root_folder()
        except Exception as ex:
            msg = f"Failed to create parser: {ex}"
            print(msg)
            return msg
    return ""


def create_parser(verbose: bool = False, on_error_abort: bool = True):
    parser = None
    try:
        parser = Parser(ROOT_FOLDER, mongodb_conn, verbose=verbose)
    except Exception as ex:
        msg = f"Failed to create parser: {ex}"
        if on_error_abort:
            print(msg)
            abort(custom_error({"message": msg}, 500))
        return msg
    return parser


if __name__ == "__main__":
    ROOT_FOLDER = os.environ.get("XFUSION_ROOT_FOLDER")
    app.run(host="0.0.0.0", port=os.environ.get("XFUSION_API_PORT"))
