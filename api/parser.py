"""
Airflow Parser

Extracts information from Airflow files:

- Core Operators
- Provider
- Custom code

"""

import os
import json
import subprocess
import re
from pprint import pprint
from typing import Optional
from operator import itemgetter
from pymongo import MongoClient, collection
from folderparser.folderparser import FolderParser
from validator.validator import validate_file
from fileparser.fileparser import FileParser
import itertools
#from logger.logger import get_logger


_BASE_CLASSES = ["BaseOperator", "BaseHook"]

_SKIP_CLASSES = [
    "LoggingMixin",
    "SkipMixin",
]

_MULTILEVEL_CATEGORIES = ["providers"]


#logger = get_logger(__name__)


class Parser:
    """Implements the parsing of Airflow files"""

    def __init__(self, root_folder: str, mongodb_conn: str = None, verbose: bool = False):
        # Check root folder
        if not os.path.isdir(root_folder):
            try:
                os.mkdir(root_folder)
            except OSError:
                raise Exception(f'Unrecognized folder "{root_folder}"')
        # Add trailing slash if it's not already there..
        self.root_folder = os.path.join(root_folder, "")
        self.mongodb_conn = mongodb_conn
        self.verbose = verbose
        self.folders = {}
        self.folders["airflow"] = [
            "airflow/models/",  # => Contains Base classes
            "airflow/hooks/",
            "airflow/operators/",
            "airflow/sensors/",
            "airflow/utils/",
        ]
        # Airflow v1
        # self.folders["providers"] = ["airflow/contrib/"]
        # Airflow v2
        self.folders["providers"] = ["airflow/providers/"]

    def init_airflow_folder(self, starting: bool = False):
        if starting and os.path.exists(os.path.join(self.root_folder, "airflow")):
            return
        # print("@@@@@@@@@@@@@@@ PARSER do_init_airflow_folder() @@@@@@@@@@@@@@")    
        control_file = os.path.join(self.root_folder, "../airflow-versions.json")
        # print(f"Parser.init_root_folder() => {control_file}")
        if not os.path.exists(control_file):
            raise Exception(f'Control file not found at "{control_file}"')
        with open(control_file) as json_file:
            data = json.load(json_file)
        repo = data["repository"]
        # Check local repo
        if os.path.exists(os.path.join(self.root_folder, "airflow")):
            # If exists => PULL
            if starting:
                return
            bashCommand = f"git pull {repo}"
            process = subprocess.Popen(bashCommand.split(), cwd=self.root_folder, stdout=subprocess.PIPE)
            _, error = process.communicate()
            if error:
                # print(error)
                # raise Exception(f'Can\'t clone "{repo}"')
                return
        else:
            # If not exists => CLONE
            # Step 2: Clone Airflow GitHub repository
            # print(f"CLONE: {self.root_folder}")
            bashCommand = f"git clone {repo} ."
            process = subprocess.Popen(bashCommand.split(), cwd=self.root_folder, stdout=subprocess.PIPE)
            _, error = process.communicate()
            if error:
                # print(error)
                return
            # logger.info(f"{self.root_folder} - CLONED.")    
        # Read folders in Airflow cloned repo, check airflow folder & explore version folders major version
        # IF airflow is not in the repo folder
        if not os.path.exists(os.path.join(self.root_folder,"airflow")):
            raise Exception("Error: not airflow folder in repo.")        
        # Parse Airflow
        airflow_path = os.path.join(self.root_folder, "airflow")
        ver_name_chk = re.compile(r"^v\d{1,2}$")  # Validate => v2, v1, v10
        # Scan version's folders
        version_folders = [ name for name in os.listdir(airflow_path) 
                            if ( os.path.isdir(os.path.join(airflow_path, name)) and re.search(ver_name_chk,name) ) 
        ]    
        if len(version_folders) == 0:
            raise Exception("Error: not version folder inside /repo/airflow.")           
        # Find major version in repo/airflow
        max_version = 0
        for idx, version in enumerate(version_folders):
            ver_num = version.split('v')[1:][0]
            if int(ver_num) > max_version:
                max_version = int(ver_num)
                max_idx = idx                    
        major_version = version_folders[max_idx]
        print(f"Airflow major version  => {major_version}")
        # Parse requiered folders
        res = self.scan(major_version, "airflow")
        res = self.scan(major_version, "providers")
        res = self.scan_udp(major_version, "udp")        
        print(f"Results of parser.scan => {res}")

    
    def init_version_folder(self, repository: str, subfolder: str, version: str, tag_id: str):
        print(f"Initializating {subfolder}...")
        # https://stackoverflow.com/a/4256153
        # Step 1: Create folder
        bashCommand = f"mkdir {subfolder}"
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        _, error = process.communicate()
        if error:
            print(error)
            raise Exception(f'Can\'t create version {version} folder at "{subfolder}"')
        # Step 2: Clone Airflow GitHub repository
        bashCommand = f"git clone {repository} ."
        process = subprocess.Popen(bashCommand.split(), cwd=subfolder, stdout=subprocess.PIPE)
        _, error = process.communicate()
        if error:
            print(error)
            raise Exception(f'Can\'t clone "{repository}"')
        # # Step 3: Checkout specific Tag
        # bashCommand = f"git checkout tags/{tag_id}"
        # process = subprocess.Popen(bashCommand.split(), cwd=subfolder, stdout=subprocess.PIPE)
        # _, error = process.communicate()
        # if error:
        #     print(error)
        #     raise Exception(f'Can\'t checkout tag "{tag_id}"')

    def validate_version(self, subfolder: str, tag_id: str):
        readme = os.path.join(subfolder, "CHANGELOG.txt")
        with open(readme, "r") as file:
            first_line = file.readline()
            first_line = first_line.split(",")[0].replace("Airflow ", "")
            comparison = f"{tag_id} VS {first_line}"
            print(f'(expected/found) {comparison} {"OK" if tag_id in first_line else "ERROR"}')
            if not tag_id in first_line:
                raise Exception(f'Invalid folder contents ({comparison}) in "{subfolder}"')

    def validate_data_in_version(self, version: str):
        """Returns stats about data loaded in specific version"""
        items = self.get_stats(version)
        data_air = [x["total"] for x in items if x["source"] == "airflow"]
        data_pro = [x["total"] for x in items if x["source"] == "providers"]
        data_udp = [x["total"] for x in items if x["source"] == "udp"]
        res = []
        if len(data_air) == 0 or data_air[0] == 0:
            res.append("airflow")
            self.scan(version=version, source="airflow")
        if len(data_pro) == 0 or data_pro[0] == 0:
            res.append("providers")
            self.scan(version=version, source="providers")
        if len(data_udp) == 0 or data_udp[0] == 0:
            res.append("udp")
            self.scan_udp(version=version, source="udp")
        return res

    def delete_catalog(self, database: str, collection: str, version: Optional[str] = None):
        with MongoClient(self.mongodb_conn) as client:
            db = client[database]
            col = db[collection]
            if version:
                res = col.delete_many({"version": version})
                return f"{res.deleted_count} documents deleted in {database}.{collection}.{version}"
            res = col.delete_many({})
            return f"{res.deleted_count} documents deleted in {database}.{collection}"

    def delete_catalog_by_source(self, database: str, collection: str, version: str, source: str):
        with MongoClient(self.mongodb_conn) as client:
            db = client[database]
            col = db[collection]
            res = col.delete_many({"version": version, "source": source})
            return f"{res.deleted_count} documents deleted in {database}.{collection}.{version}.{source}"

    def get_stats(self, version: str = None):
        """Returns stats"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            pipeline = [{"$match": {"visible": True}}]
            if version:
                pipeline.append({"$match": {"version": version}})
            pipeline.extend(
                [
                    {"$group": {"_id": {"version": "$version", "source": "$source"}, "total": {"$sum": 1}}},
                    {"$unwind": "$_id"},
                ]
            )
            items = list(catalog.operators.aggregate(pipeline))
            items = [
                ({"version": x["_id"]["version"], "source": x["_id"]["source"], "total": x["total"]}) for x in items
            ]
            items = sorted(items, key=lambda x: (x["version"] or "", x["source"] or ""))
        return items

    def get_operators_search_parameters_type(self, version: str, target_type: str):
        """Searches Operators by data type"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            pipeline = [
                {"$unset": "_id"},
                {"$match": {"version": version}},
                {"$unwind": "$properties.parameters"},
                {"$match": {"properties.parameters.type": {"$regex": f".*{target_type}.*"}}},
            ]
            items = list(catalog.operators.aggregate(pipeline))
        return items

    
    def get_operators_list(self, version: str):
        """Returns all the Operators"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            items = list(catalog.operators.find({"version": version, "visible": True}, {"_id": 0}))
            items = sorted(items, key=lambda x: (x["category"] or "", x["subcategory"] or "", x["type"] or ""))
        return items

    def get_operators_list_original(self, version: str, mode: str):
        """Returns all the Operators"""
        """
            {
            "type": "GenericTransfer",
            "properties": {
                "description": "Moves data from a connection to another, assuming that they both\\nprovide the required methods in their respective hooks. The source hook\\nneeds to expose a `get_records` method, and the destination a\\n`insert_rows` method.\\n\\nThis is meant to be used on small-ish datasets that fit in memory.",
                "module": "airflow.operators.generic_transfer",
                "parameters": [
                {
                    "description": "SQL query to execute against the source database. (templated)",
                    "id": "sql",
                    "inheritedFrom": null,
                    "required": true,
                    "type": "str"
                },
            }
        """
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            if mode == "full":
                pipeline = [
                    {"$match": {"version": version}},
                    {"$match": {"visible": True}},
                    {
                        "$project": {
                            "_id": 0,
                            "type": "$type",
                            "properties.description": "$properties.description",
                            "properties.parameters": "$properties.parameters",
                            "properties.module": {
                                "$concat": [
                                    "$category",
                                    ".",
                                    {"$ifNull": ["$subcategory", "-"]},
                                    ".",
                                    {"$ifNull": ["$subcategory", "-"]},
                                ]
                            },
                            # "imagePath": None # "https://svn.apache.org/repos/asf/comdev/project-logos/originals/airflow-3.svg"
                        }
                    },
                ]
            else:
                pipeline = [
                    {"$match": {"version": version}},
                    {"$match": {"visible": True}},
                    {
                        "$project": {
                            "_id": 0,
                            "type": "$type",
                            "properties.description": "$properties.description",
                            "properties.parameters": None,
                            "properties.module": {
                                "$concat": [
                                    "$category",
                                    ".",
                                    {"$ifNull": ["$subcategory", "-"]},
                                    ".",
                                    {"$ifNull": ["$subcategory", "-"]},
                                ]
                            },
                            "imagePath": "https://svn.apache.org/repos/asf/comdev/project-logos/originals/airflow-3.svg",
                        }
                    },
                ]
            items = list(catalog.operators.aggregate(pipeline))
            items = sorted(items, key=lambda x: (x["properties"]["module"] or "", x["type"] or ""))
        return items

    # SV: Default call for Operators
    def get_operators_tree(self, version: str, customer_id: str):
        """Returns all Core Operators and Custom Operators of the provided customer_id"""
        items = None
        with MongoClient(self.mongodb_conn) as client:            
            catalog = client.catalog
            pipeline = [
                {"$match": {"version": version}},
                {"$match": {"visible": True}}
            ]
            if customer_id:
                pipeline.append(
                    {
                        "$match": {
                            "$or": [
                                {"source": {"$in": ["airflow", "providers","udp"] } },
                                {"$and":[
                                    {"source": "custom"},
                                    {"customer_id": customer_id}
                                ] 
                            }] 
                        }
                    }
                )
            else:
                pipeline.append(
                    { "$match": {"source": {"$in": ["airflow", "providers","udp"] } } }
                )            
            pipeline.append(
                {
                    "$replaceWith": {
                        "name": "$type",
                        "category": "$category",
                        "subcategory": "$subcategory",
                        "description": "$properties.description",
                    }
                }
            )
            items = list(catalog.operators.aggregate(pipeline))
            items = sorted(items, key=lambda x: (x["category"] or "", x["subcategory"] or "", x["name"] or ""))
            res = []
            level1 = itertools.groupby(items, lambda x: x["category"])
            for key1, group1 in level1:
                if key1 in _MULTILEVEL_CATEGORIES:
                    sub = []
                    level2 = itertools.groupby(group1, lambda x: x["subcategory"])
                    for key2, group2 in level2:
                        sub.append(
                            {
                                "name": key2,
                                "operators": [self._del_operator_categories(x) for x in list(group2)],
                            }
                        )
                    res.append({"name": key1, "subcategory": sub, "operators": None})
                else:
                    res.append(
                        {
                            "name": key1,
                            "subcategory": None,
                            "operators": [self._del_operator_categories(x) for x in list(group1)],
                        }
                    )
            items = res
        return items

    def get_operators_tree_v2(self, version: str):
        """Returns all the Operators"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            pipeline = [
                {"$match": {"version": version}},
                {"$match": {"visible": True}},
                {
                    "$replaceWith": {
                        "name": "$type",
                        "category": "$category",
                        "subcategory": "$subcategory",
                        "description": "$properties.description",
                    }
                },
            ]
            items = list(catalog.operators.aggregate(pipeline))
            items = sorted(items, key=lambda x: (x["category"] or "", x["subcategory"] or "", x["name"] or ""))
            res = {}
            level1 = itertools.groupby(items, lambda x: x["category"])
            for key1, group1 in level1:
                if key1 in ["providers"]:
                    res[key1] = {}
                    level2 = itertools.groupby(group1, lambda x: x["subcategory"])
                    for key2, group2 in level2:
                        res[key1][key2] = [self._del_operator_categories(x) for x in list(group2)]
                else:
                    res[key1] = [self._del_operator_categories(x) for x in list(group1)]
            items = res
        return items

    def get_operators_nested(self, version: str):
        """Returns all the Operators"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            pipeline = [
                {"$match": {"version": version}},
                {"$match": {"visible": True}},
                {
                    "$replaceWith": {
                        "name": "$type",
                        "category": "$category",
                        "subcategory": "$subcategory",
                        "description": "$properties.description",
                    }
                },
            ]
            items = list(catalog.operators.aggregate(pipeline))
            items = sorted(items, key=lambda x: (x["category"] or "", x["subcategory"] or "", x["name"] or ""))
            res = {}
            level1 = itertools.groupby(items, lambda x: x["category"])
            for key1, group1 in level1:
                if key1 in _MULTILEVEL_CATEGORIES:
                    res[key1] = {}
                    level2 = itertools.groupby(group1, lambda x: x["subcategory"])
                    for key2, group2 in level2:
                        res[key1][key2] = [self._del_operator_categories(x) for x in list(group2)]
                else:
                    res[key1] = [self._del_operator_categories(x) for x in list(group1)]
            items = res
        return items

    def _del_operator_categories(self, operator: dict):
        del operator["category"]
        del operator["subcategory"]
        return operator

    def get_operator_tree(self, version: str, operator_id: str):
        """Returns the Operator tree"""
        tree = []
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            if "." in operator_id:
                query = {"version": version, "properties.module": operator_id}
            else:
                query = {"version": version, "type": operator_id}
            item = catalog.operators.find_one(query)
            if item:
                indent = ""
                tree = list(self._nested_dict_values_iterator(catalog.operators, item, indent))
                tree.insert(0, item["type"])
        return tree

    #TODO [11012021] - The Operator's name (type) must be UNIQUE because get_operator() request not filter
    # by source -> (airflow, provider, udp, custom). If a customer load a operator with a name of an existing
    # one name no matter its source, the API return the first already loaded and parsed.
    #
    # To avoid this behavior to aproaches can be implemented:
    #
    # Approach 1: When a customer tries to upload a Operator with a name that already exists in the mongodb
    # prohibits the action and return an error message notifying this duplicity. This approach implies
    # changes in the UI to handle the reported error.
    #
    #
    # Approach 2: Add to the get_operator() and its url route the source to filter and return the
    # Operator's name -> (type) of the specified source.
    # This approches implies new request from the UI using the new route of get_operator()
    #
    #         {{API_URL}}/operators/v2/<source>/UDPDatasetOperator
    #
    def get_operator(self, version: str, operator_id: str, debugging: bool = False):
        """Returns 1 Operator"""
        item = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            if "." in operator_id:
                query = {"version": version, "properties.module": operator_id}
            else:
                query = {"version": version, "type": operator_id}
            # Remove parameters default value for testing the Frontend
            item = catalog.operators.find_one(
                query,
                # { "properties.parameters.default": 0 }
            )
            # Add parameters from parent classes
            if item:
                if not debugging:
                    parents = item["inherits"]
                    if parents:
                        for parent in item["inherits"]:
                            parent = catalog.operators.find_one(
                                {"type": parent},
                                # { "properties.parameters.default": 0 }
                            )
                            if parent and "properties" in parent and "parameters" in parent["properties"]:
                                item["properties"]["parameters"].extend(parent["properties"]["parameters"])
                # Refactor item
                tmp = {
                    "module": item["properties"]["module"],
                    "category": item["category"],
                    "subcategory": item["subcategory"],
                    "name": item["type"],
                    "description": item["properties"]["description"],
                    "parameters": item["properties"]["parameters"]
                }
                if "taskConfiguration" in item:
                    tmp["taskConfiguration"] = item["taskConfiguration"]
                if debugging:
                    tmp["inherits"] = item["inherits"]
                    tmp["source"] = item["source"]
                item = tmp
        return item

    def _nested_dict_values_iterator(self, db: collection.Collection, dic: dict, indent: str = ""):
        """Accepts a nested dictionary as argument
        and iterate over all values of nested dictionaries
        """
        if dic:
            if indent is None:
                indentation = ""
            else:
                indentation = f"--{indent}"
            current_type = dic.get("type")
            if current_type in _BASE_CLASSES:
                return
            for operator_id in dic.get("inherits"):
                if operator_id not in _SKIP_CLASSES:
                    yield f"{indentation}{operator_id}"
                    query = {"type": operator_id}
                    item = db.find_one(query)
                    for v in self._nested_dict_values_iterator(db, item, indent):
                        yield f"{indentation}{v}"

    def _normalize_type(self, field_type: str):
        if field_type is None:
            return ""
        if field_type.startswith("Optional["):
            return field_type[len("Optional[") : -1]
        return field_type

    def get_distinct_types(self, version: str):
        """Returns unique types definition"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            items = list(
                catalog.operators.distinct("properties.parameters.type", {"version": version, "visible": True})
            )
            items = [self._normalize_type(item) for item in items]
            # Unique values
            items = list(set(items))
        if items:
            # Sort case insensitive
            items.sort(key=str.lower)
        return items

    def get_distinct_modules(self, version: str):
        """Returns unique module names"""
        items = None
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            items = list(catalog.operators.distinct("properties.module", {"version": version, "visible": True}))
        if items:
            items.sort()
        return items

    def _save_operators(self, items):
        """Saves the extracted Operator information in the MongoDB database"""
        total = 0
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            response = catalog.operators.insert_many(items)
            total = len(response.inserted_ids)
        msg = f"{total} documents inserted"
        if self.verbose:
            print(msg)
        return msg
    
    #TODO SV: scan methods
    
    def scan(self, version: str, source: str):
        """Extracted information from the Core Airflow modules"""
        # SV: Habría q agregar  => source al path.join() ????
        version_root_folder = os.path.join(self.root_folder, "airflow", version)
        print(f"scan => version_root_folder={version_root_folder}")
        res = ""
        # Check version folder
        if not os.path.exists(version_root_folder):
             msg = f"Error, {source} version's folder {version} not found."
             return msg
        # 1) Scan folder/s
        files = []
        for folder in self.folders[source]:
            folder_path = os.path.join(version_root_folder, folder)
            if self.verbose:
                print(f"Scanning {folder_path} ...")
            dir = FolderParser(folder_path)
            dir.collect(filter_by_targets=False)
            files.extend(dir.get_files())
        if self.verbose:
            # pprint(files)
            print(f"{len(files)} files found in {self.root_folder}")
        # 2) Validate files
        valid_files = list(filter(lambda x: validate_file(x), files))
        if self.verbose:
            # pprint(valid_files)
            print(f"{len(valid_files)} valid files found in {self.root_folder}")
        # 3) Parse files
        results = []
        for filename in valid_files:
            fileparser = FileParser(
                filename, root_folder=version_root_folder, version=version, source=source, verbose=False
            )
            debug_parsing = filename == './airflow/v2/airflow/models/baseoperator.py'
            response = fileparser.parse(debug=debug_parsing)
            # if debug_parsing:
            #     print('************************************************************')
            #     print(filename)
            #     pprint(response)
            #     print('************************************************************')
            results.extend(response)
        # 4) Save to DB
        if self.verbose:
            print(f"{len(results)} classes found in {self.root_folder}")
        if self.mongodb_conn is None:
            raise Exception("Database connection not specified")
        if self.verbose:
            print("Saving...")
        res = self._save_operators(results)
        # 5) Post-processing
        results_with_parents = []
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            for result in results:
                parents = set()
                for parent in result["inherits"]:
                    parents.add(parent)
                    query = {"version": version, "type": parent}
                    item = catalog.operators.find_one(query)
                    if item:
                        parents.update(
                            list(self._nested_dict_values_iterator(catalog.operators, item, indent=None))
                        )
                parents = list(parents)
                result["inherits"] = parents
                result["visible"] = any(parent in _BASE_CLASSES for parent in parents)
                results_with_parents.append(result)
        self.delete_catalog_by_source("catalog", "operators", version, source)
        res = self._save_operators(results_with_parents)
        return res
    
    def scan_udp(self, version: str, source: str):
        """Extracted information from UDP custom operators"""
        version_root_folder = os.path.join(self.root_folder, source, version)
        if self.verbose:
            print(f"scan_udp({version_root_folder})")
        # 1) Scan files
        files = []
        folder_path = version_root_folder
        # Check version folder
        if not os.path.exists(folder_path):
             msg = f"Error, {source} version's folder {version} not found."
             return msg
        if self.verbose:
            print(f"Scanning {folder_path} ...")
        dir = FolderParser(folder_path)
        dir.collect(filter_by_targets=False)
        files.extend(dir.get_files())
        if self.verbose:
            # pprint(files)
            print(f"{len(files)} files found in {self.root_folder}")
        # 2) Validate files
        valid_files = list(filter(lambda x: validate_file(x), files))
        if self.verbose:
            # pprint(valid_files)
            print(f"{len(valid_files)} valid files found in {self.root_folder}")
        # 3) Parse files
        results = []
        for filename in valid_files:
            fileparser = FileParser(
                filename, root_folder=version_root_folder, version=version, source=source, verbose=False
            )
            debug_parsing = filename == './airflow/v2/airflow/models/baseoperator.py'
            response = fileparser.parse(debug=debug_parsing)
            if debug_parsing:
                print('************************************************************')
                print(filename)
                pprint(response)
                print('************************************************************')
            results.extend(response)
        # 4) Save to DB
        if self.verbose:
            print(f"{len(results)} classes found in {self.root_folder}")
        if self.mongodb_conn is None:
            raise Exception("Database connection not specified")
        if self.verbose:
            print("Saving...")
        res = self._save_operators(results)
        # 5) Post-processing
        results_with_parents = []
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            for result in results:
                parents = set()
                for parent in result["inherits"]:
                    parents.add(parent)
                    query = {"version": version, "type": parent}
                    item = catalog.operators.find_one(query)
                    if item:
                        parents.update(
                            list(self._nested_dict_values_iterator(catalog.operators, item, indent=None))
                        )
                parents = list(parents)
                result["inherits"] = parents
                result["visible"] = any(parent in _BASE_CLASSES for parent in parents)
                results_with_parents.append(result)
        self.delete_catalog_by_source("catalog", "operators", version, source)
        res = self._save_operators(results_with_parents)
        return res

    # Scan Customer 
    def scan_custom(self, version: str, source: str, customer_id: str, token: str):
        """Extracted information from Customer custom operators"""
        # Example: repo/custom/customer-a/
        customer_root_folder = os.path.join(self.root_folder, source, customer_id)
        if self.verbose:
            print(f"scan_custom({customer_root_folder})")
        # 0) Initialization
        # Si hay repo local => pull
        if os.path.exists(customer_root_folder):
            bashCommand = f"git pull"
            process = subprocess.Popen(bashCommand.split(), cwd=customer_root_folder, stdout=subprocess.PIPE)
            _, error = process.communicate()
            if error:
                print(error)
                raise Exception(f'Can\'t clone custom repo')
            #logger.info(f"{self.root_folder} - UPDATED.")    
        else:
            # Step 2: Clone Customer GitHub repository
            print(f"CLONE 0: Create folder {customer_root_folder}")
            os.makedirs(customer_root_folder)
            print(f"CLONE 1: {customer_root_folder}")
            repo = f"https://{token}@github.com/{customer_id}/custom-operators.git"
            bashCommand = f"git clone {repo} ."
            process = subprocess.Popen(bashCommand.split(), cwd=customer_root_folder, stdout=subprocess.PIPE)
            _, error = process.communicate()
            print(f"CLONE 2: {customer_root_folder}")
            if error:
                print(error)
                raise Exception(f'Can\'t clone "{repo}"')
            #logger.info(f"{self.root_folder} - CLONED.")
            print(f"CLONE 3: {customer_root_folder}")
        # 1) Scan files
        files = []
        folder_path = f"{customer_root_folder}/{version}"
        # if self.verbose:
        print(f"Scanning {folder_path} ...")
        dir = FolderParser(folder_path)
        dir.collect(filter_by_targets=False)
        files.extend(dir.get_files())
        if self.verbose:
            # pprint(files)
            print(f"{len(files)} files found in {self.root_folder}")
        # 2) Validate files
        valid_files = list(filter(lambda x: validate_file(x), files))
        if self.verbose:
            # pprint(valid_files)
            print(f"{len(valid_files)} valid files found in {self.root_folder}")
        # 3) Parse files
        files_with_errors = []
        results = []
        for filename in valid_files:
            fileparser = FileParser(
                filename,
                root_folder=customer_root_folder,
                version=version,
                source=source,
                verbose=False,
                customer_id=customer_id
            )
            # debug_parsing = filename == './airflow/v2/airflow/models/baseoperator.py'
            # response = fileparser.parse(debug=debug_parsing)
            try:
                response = fileparser.parse(debug=True)   # Trigger corrupt file exception if any 
                results.extend(response)
            except Exception as ex:
                files_with_errors.append({"file": filename, "error": str(ex)})
                # SV: Informar excepcion, anular rise
                #raise ex
            # if debug_parsing:
            # print('************************************************************')
            # print(filename)
            # pprint(response)
            # print('************************************************************')
            #results.extend(response)
        # 4) Save to DB
        if self.verbose:
            print(f"{len(results)} classes found in {self.root_folder}")
        if self.mongodb_conn is None:
            raise Exception("Database connection not specified")
        if self.verbose:
            print("Saving...")
        res = self._save_operators(results)
        # 5) Post-processing
        results_with_parents = []
        with MongoClient(self.mongodb_conn) as client:
            catalog = client.catalog
            for result in results:
                parents = set()
                for parent in result["inherits"]:
                    parents.add(parent)
                    query = {"version": version, "type": parent}
                    item = catalog.operators.find_one(query)
                    if item:
                        parents.update(
                            list(self._nested_dict_values_iterator(catalog.operators, item, indent=None))
                        )
                parents = list(parents)
                result["inherits"] = parents
                result["visible"] = any(parent in _BASE_CLASSES for parent in parents)
                results_with_parents.append(result)
        self.delete_catalog_by_source("catalog", "operators", version, source)
        res = self._save_operators(results_with_parents)
        return res, files_with_errors
    