# pylint: disable=import-error
import ast
import json
import os
import sys
import re
from pathlib import Path
from pprint import pprint
from typing import Dict
from .docparser.docparser import DocParser
from .initparser.initparser import InitMethodParser


class FileParser:
    """Implements the parsing of the Docstring and the Init Method of a Class"""

    def __init__(
        self,
        filename: str,
        root_folder: str,
        version: str,
        source: str,
        customer_id: str = None,
        verbose: bool = False
    ):
        """Receives the name of the file to be parsed"""
        self.filename = filename
        self.verbose = verbose
        self.source = source
        self.version = version
        self.customer_id = customer_id
        # Add trailing slash if it's not already there..
        self.root_folder = os.path.join(root_folder, "")

    def get_module(self):
        """Returns the Module name from the filename.
        :returns: str
        """
        if self.filename == "-":
            return "sys.stdin"
        if self.root_folder in self.filename:
            filename = self.filename.replace(self.root_folder, "")
        else:
            filename = self.filename
        module = filename.replace(".py", "").replace("/", ".")
        return module

    def get_subcategory(self):
        """Returns the Subcategory name from the filename.
        :returns: str
        """
        if self.filename == "-":
            return "sys.stdin"
        if self.source == "airflow":
            return None
        if self.root_folder in self.filename:
            filename = self.filename.replace(self.root_folder, "")
        else:
            filename = self.filename
        module = filename.replace(".py", "").replace("/", ".")
        parts = module.split(".")
        if len(parts) > 2:
            return parts[2]
        return None

    def parse(self, debug: bool = False):
        """Returns the extracted information from the Class/Classes.
        :returns: a array of dictionaries of form:
            [
                {
                    "type": str,
                    "inherits": list[str],
                    "properties": {
                        "description": str,
                        "module": str,
                        "parameters": [
                            {
                                "description": str,
                                "id": str,
                                "inheritedFrom": str or None,
                                "required": bool,
                                "type": str
                            }
                        ]
                    }
                }
            ]
        """
        contents = None
        if self.filename == "-":
            contents = sys.stdin.read()
        else:
            with open(self.filename, "rb") as fin:
                contents = fin.read()
        try:
            tree = ast.parse(contents) # Trigger exception at error in file
        except Exception as ex:
            file_with_error = self.filename
            try:
                p = Path(self.filename)
                file_with_error = p.name
            except Exception as ex:
                pass
            print(f'fileparser.py: Parsing Error! - {file_with_error}: {ex}')
            #raise Exception(f"Failed to parse {file_with_error}: {ex}")
            raise Exception(f"{ex}")
        
        class_definitions = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        results = []
        for class_def in class_definitions:
            properties = {}
            # PARENT CLASSES
            parents = []
            node = class_def
            for base in node.bases:
                if hasattr(base, "id"):
                    parents.append(getattr(base, "id"))
            # if self.verbose:
            # print(
            #     f"FILE  => {self.filename}\nMODULE=> {self.get_module()}\nCLASS => {class_def.name}({','.join(parents)})\n****************************************\n"
            # )
            properties["module"] = self.get_module()
            # DOCSTRING PARSER
            doc = DocParser(ast.get_docstring(class_def))
            doc_result = doc.parse()
            if self.verbose:
                pprint(doc_result)
            properties["description"] = doc_result["description"].strip()
            # INIT METHOD PARSER
            init = InitMethodParser(class_def, self.filename)
            parameters = init.parse()
            if len(parameters) > 0:
                # Add Descriptions?
                if bool(doc_result):
                    for param in parameters:
                        id = param["id"]
                        doc_params = next(
                            filter(
                                lambda x: x["name"] == id,
                                doc_result["parameters"],
                            ),
                            None,
                        )
                        if doc_params and doc_params["doc"]:
                            param["description"] = doc_params["doc"].strip()
                            if not param["type"]:
                                if "typ" in doc_params.keys():
                                    param["type"] = doc_params["typ"]
            # Clean parameters
            clean = []
            for param in parameters:
                type_name = param["type"]
                if type_name and "Optional" in type_name:
                    # print(type_name, " => ", self._normalize_type(type_name))
                    type_name = self._normalize_type(type_name)
                param["type"] = type_name
                type_category = self._calculate_category(type_name)
                param["typeCategory"] = type_category
                param["typeSubCategories"] = self._calculate_subcategories(type_category, type_name)
                clean.append(param)
            # Fix parameters as needed
            # 1) BaseOperator.retries default should be not None
            if self.filename.endswith("models/baseoperator.py") and class_def.name == "BaseOperator":
                # 1) BaseOperator.retries should be not None => retries = 0 (as fallback in code)
                for param in clean:
                    if param["id"] == "retries":
                        if param["default"] is None:
                            param["default"] = 0
            # Parameters ok
            properties["parameters"] = clean
            results.append(
                {
                    "type": class_def.name,
                    "version": self.version,
                    "source": self.source,
                    "customer_id": self.customer_id if self.customer_id else None,
                    "inherits": parents,
                    "properties": properties,
                    "category": self.source,
                    "subcategory": self.get_subcategory(),
                }
            )
        # Check for Task Configuration operator file
        # bash.py => OTCC-bash.json
        if len(results) > 0:
            p = Path(self.filename)
            otcc_file = f"{p.parents[0]}/OTCC-{p.stem}.json"
            if os.path.exists(otcc_file):
                print(f"OTCC => {self.filename} => {otcc_file}")
                with open(otcc_file) as json_file:
                    data = json.load(json_file)
                    # pprint(data)
                    results[0]["taskConfiguration"] = data
            # End of parsing
        return results

    def _normalize_type(self, field_type: str):
        if field_type is None:
            return ""
        if field_type.startswith("Optional["):
            return field_type[len("Optional[") : -1]
        return field_type

    # def _calculate_category(self, field_type: str):
    #     field_type = field_type or ""
    #     field_type = field_type.lower()
    #     if re.findall(r"dict\w*", str(field_type)):
    #         return "dict"
    #     if re.findall(r"union\w*", str(field_type)):
    #         return "union"
    #     if re.findall(r"list\w*", str(field_type)) or re.findall(r"sequence\w*", str(field_type)):
    #         return "list"
    #     if (
    #         field_type == "str"
    #         or field_type == "int"
    #         or field_type == "bool"
    #         or field_type == "float "
    #         or re.findall(r"callable\w*", str(field_type))
    #         or field_type == "timedelta"
    #         or field_type == "datetime"
    #         or re.findall(r"datetime.\w*", str(field_type))
    #     ):
    #         return "elem"
    #     return "complex"

    def _calculate_category(self, type_name: str):
        type_name = (type_name or "").strip().lower()
        if type_name.startswith("dict"):
            return "dict"
        if type_name.startswith("union"):
            return "union"
        if type_name.startswith("list") or type_name.startswith("iterable") or type_name.startswith("sequence"):
            return "list"
        if (
            type_name == "none"
            or type_name == "str"
            or type_name == "int"
            or type_name == "bool"
            or type_name == "float"
            or type_name == "timedelta"
            or type_name == "datetime"
            or type_name == "datetime.timedelta"
            or type_name == "datetime.datetime"
            or type_name.startswith("callable")
        ):
            return "elem"
        return "complex"

    def _calculate_subcategories(self, type_category: str, type_name: str):
        type_name = (type_name or "").strip().lower()
        # "elem" and "complex" don't have subcategories
        if type_category == "elem" or type_category == "complex":
            return None
        # “list”, “dict” and "union"
        parts = []
        if type_category == "list":
            if type_name.startswith("list") and "[" in type_name and type_name.endswith("]"):
                parts.append(type_name[len("list") + 1 : -1])
            if type_name.startswith("iterable") and "[" in type_name and type_name.endswith("]"):
                parts.append(type_name[len("iterable") + 1 : -1])
            if type_name.startswith("sequence") and "[" in type_name and type_name.endswith("]"):
                parts.append(type_name[len("sequence") + 1 : -1])
        elif type_category == "dict":
            if type_name.startswith("dict") and "[" in type_name and type_name.endswith("]"):
                inner = type_name[len("dict") + 1 : -1]
                inner_parts = inner.split(",")
                parts = [self._calculate_category(x.strip()) for x in inner_parts]
        elif type_category == "union":
            if type_name.startswith("union") and "[" in type_name and type_name.endswith("]"):
                inner = type_name[len("union") + 1 : -1]
                inner_parts = inner.split(",")
                parts = [self._calculate_category(x.strip()) for x in inner_parts]
        else:
            return None
        return parts
