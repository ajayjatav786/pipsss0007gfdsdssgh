"""
Class Init Method Parser

Extracts information from the __init__ method of a Class:

- Description
- Parameters
- Return value

Based on:
- https://github.com/terrencepreilly/darglint
- https://github.com/terrencepreilly/darglint/blob/master/darglint/function_description.py
"""
# pylint: disable=import-error
import ast
from collections import deque
import sys
from enum import Enum
from typing import (
    Callable,
    Iterator,
    List,
    Set,
    Tuple,
    Optional,
    Union,
    Type,
    Any,
)
import json
from pprint import pprint
from .analysis_visitor import AnalysisVisitor
from .function_and_method_visitor import FunctionAndMethodVisitor
from .config import get_logger
from .analysis_helpers import _has_decorator


logger = get_logger()


FunctionDef = ast.FunctionDef  # type: Union[Type[Any], Tuple[Type[Any], Type[Any]]]  # noqa: E501
if hasattr(ast, "AsyncFunctionDef"):
    FunctionDef = (ast.FunctionDef, ast.AsyncFunctionDef)


class FunctionType(Enum):

    FUNCTION = 1
    METHOD = 2
    PROPERTY = 3


class FunctionDescription(object):
    """Describes a function or method.

    Whereas a `Docstring` object describes a function's docstring,
    a `FunctionDescription` describes the function itself.  (What,
    ideally, the docstring should describe.)

    """

    def __init__(self, function_type, function):
        # type: (FunctionType, Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> None
        """Create a new FunctionDescription.

        Args:
            function_type: Type of the function.
            function: The base node of the function.

        """
        self.is_method = function_type == FunctionType.METHOD
        self.is_property = function_type == FunctionType.PROPERTY
        self.function = function
        self.line_number = self.get_line_number_from_function(function)
        self.name = function.name
        visitor = AnalysisVisitor()
        try:
            visitor.visit(function)
        except Exception as ex:
            msg = "Failed to visit in {}: {}".format(self.name, ex)
            logger.debug(msg)
            return

        self.argument_names = visitor.arguments
        self.argument_types = visitor.types
        self.argument_defaults = visitor.defaults
        self.argument_lineno = visitor.lineno

        # if self.name == "__init__":
        #     pprint('INITPARSER***************************************************')
        #     pprint(self.argument_names)
        #     pprint(self.argument_types)
        #     pprint(self.argument_defaults)
        #     pprint(self.argument_lineno)
        #     pprint('*************************************************************')

        # Removes self parameter        
        # if function_type != FunctionType.FUNCTION and len(self.argument_names) > 0:
        #     if not _has_decorator(function, "staticmethod"):
        #         self.argument_names.pop(0)
        #         self.argument_types.pop(0)

        self.has_return = bool(visitor.returns)
        self.has_empty_return = False
        if self.has_return:
            return_value = visitor.returns[0]
            self.has_empty_return = return_value is not None and return_value.value is None
        self.return_type = self._get_return_type(function)
        self.has_yield = bool(visitor.yields)
        self.raises = visitor.exceptions
        self.docstring = self._get_docstring(function)
        self.variables = [x.id for x in visitor.variables]
        self.raises_assert = bool(visitor.asserts)
        self.is_abstract = visitor.is_abstract

    def _get_docstring(self, fun):
        # type: (ast.AST) -> Optional[str]
        return ast.get_docstring(fun)

    def _get_all_functions(self, tree):
        # type: (ast.AST) -> Iterator[Union[ast.FunctionDef, ast.AsyncFunctionDef]]  # noqa: E501
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                yield node
            elif hasattr(ast, "AsyncFunctionDef"):
                if isinstance(node, ast.AsyncFunctionDef):
                    yield node

    def _get_all_classes(self, tree):
        # type: (ast.AST) -> Iterator[ast.ClassDef]
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                yield node

    def _get_all_methods(self, tree):
        # type: (ast.AST) -> Iterator[Union[ast.FunctionDef, ast.AsyncFunctionDef]]  # noqa: E501
        for klass in self._get_all_classes(tree):
            for fun in self._get_all_functions(klass):
                yield fun

    def _get_return_type(self, fn):
        # type: (Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> Optional[str]
        if fn.returns is not None and hasattr(fn.returns, "id"):
            return getattr(fn.returns, "id")
        return None

    def get_line_number_from_function(self, fn):
        # type: (Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> int
        """Get the line number for the end of the function signature.

        The function signature can be farther down when the parameter
        list is split across multiple lines.

        Args:
            fn: The function from which we are getting the line number.

        Returns:
            The line number for the start of the docstring for this
            function.

        """
        line_number = fn.lineno
        if hasattr(fn, "args") and fn.args.args:
            last_arg = fn.args.args[-1]
            line_number = last_arg.lineno
        return line_number


class InitMethodParser:
    """Implements the parsing of the __init__ method of a Class"""

    def __init__(self, tree, filename):
        """Receives the AST tree of the Class to be parsed"""
        self.tree = tree
        self.filename = filename

    def parse(self):
        """Returns the extracted information from the __init__ method"""
        init = self._get_init_method_description()
        if init is None:
            return []
        params = []
        for i, val in enumerate(init.argument_names):
            if val == "*args" or val == "**kwargs":
                break            
            default_value = None
            if len(init.argument_defaults) > 0:
                if i <= len(init.argument_defaults) - 1:
                    default_value = init.argument_defaults[i]
                # TODO Check why there could be errors
                # else:
                #     print(f"ERROR init.argument_defaults: {val} in:")
                #     print(self.filename)
                #     print(json.dumps(init.argument_names))
                #     print(json.dumps(init.argument_types))
                #     print(json.dumps(init.argument_defaults))
            required = False
            if default_value == "**NO_DEFAULT**":
                required = True
                default_value = None
            # print(f"{i}: {val} {init.argument_types[i]}{ f' = {default_value}' if not required else ''}")
            params.append(
                {
                    "id": val,
                    "type": init.argument_types[i],
                    "default": default_value,
                    "required": required,
                    "inheritedFrom": None,
                }
            )
        return params

    def _get_init_method_description(self):
        # type: (ast.AST) -> FunctionDescription
        """
        Get function name, args, return presence and docstrings.

        Returns:
            A function description for the __init__ method.
        """
        # functions = self._get_function_descriptions()
        # filtered = list(filter(lambda function: function.name == "__init__", functions))
        # if len(filtered) == 1:
        #     return filtered[0]
        init_fun = self._get_function_description_for_init()
        return init_fun

    def _get_function_descriptions(self):
        # type: (ast.AST) -> List[FunctionDescription]
        """Get function name, args, return presence and docstrings.

        This function should be called on the top level of the
        document (for functions), and on classes (for methods.)

        Args:
            tree: The tree representing the entire program.

        Returns:
            A list of function descriptions pulled from the ast.

        """
        ret = list()  # type: List[FunctionDescription]
        visitor = FunctionAndMethodVisitor()
        visitor.visit(self.tree)
        for prop in visitor.properties:
            ret.append(FunctionDescription(function_type=FunctionType.PROPERTY, function=prop))
        for method in visitor.methods:
            ret.append(FunctionDescription(function_type=FunctionType.METHOD, function=method))
        for function in visitor.functions:
            ret.append(FunctionDescription(function_type=FunctionType.FUNCTION, function=function))
        return ret

    def _get_function_description_for_init(self):
        # type: (ast.AST) -> List[FunctionDescription]
        """Get function name, args, return presence and docstrings.

        This function should be called on the top level of the
        document (for functions), and on classes (for methods.)

        Args:
            tree: The tree representing the entire program.

        Returns:
            A list of function descriptions pulled from the ast.

        """
        visitor = FunctionAndMethodVisitor()
        visitor.visit(self.tree)
        # for prop in visitor.properties:
        #     ret.append(FunctionDescription(function_type=FunctionType.PROPERTY, function=prop))
        for method in visitor.methods:
            if method.name == '__init__':
                return FunctionDescription(function_type=FunctionType.METHOD, function=method)
        for function in visitor.functions:
            if function.name == '__init__':
                return FunctionDescription(function_type=FunctionType.FUNCTION, function=function)
        return None