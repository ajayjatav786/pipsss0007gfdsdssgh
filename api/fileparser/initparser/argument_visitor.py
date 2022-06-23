"""
AST Argument Visitor

Parses arguments from a method.

Based on:
- https://github.com/AtomLinter/linter-pylama
- https://github.com/modelop/hadrian/blob/7c63e539d79e6e3cad959792d313dfc8b0c523ea/titus/titus/producer/expression.py
"""
import ast
import json
from typing import (
    Any,
    Dict,
    List,
)

from collections import OrderedDict
from pprint import pprint
import astpretty


def _ifchain(state, stmt, chain):
    test = _expression(stmt.test, _newscope(state))
    thenClause = _statements(stmt.body, _newscope(state))
    chain.append(OrderedDict([("if", test), ("then", thenClause)]))

    if len(stmt.orelse) == 0:
        return chain

    elif len(stmt.orelse) == 1 and isinstance(stmt.orelse[0], ast.If):
        return _ifchain(state, stmt.orelse[0], chain)

    else:
        chain.append(_statements(stmt.orelse, _newscope(state)))
        return chain


def _statement(stmt, state):
    if isinstance(stmt, ast.Assign):
        if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            name = stmt.targets[0].id
            expr = _expression(stmt.value, state)
            if name in state["symbols"]:
                letset = "set"
            else:
                letset = "let"
            state["symbols"].add(name)
            return _form(state, stmt.lineno, {letset: {name: expr}})

        elif (
            len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Tuple)
            and all(isinstance(x, ast.Name) for x in stmt.targets[0].elts)
            and isinstance(stmt.value, ast.Tuple)
        ):
            out = OrderedDict()
            lets = 0
            sets = 0
            for name, value in zip(stmt.targets[0].elts, stmt.value.elts):
                if name.id in state["symbols"]:
                    sets += 1
                else:
                    lets += 1
                    state["symbols"].add(name.id)
                out[name.id] = _expression(value, state)
            if lets > 0 and sets == 0:
                letset = "let"
            elif lets == 0 and sets > 0:
                letset = "set"
            else:
                raise Exception(
                    "cannot declare {0} symbols and reassign {1} in the same statement (source line {2})".format(
                        lets, sets, stmt.lineno
                    )
                )
            return _form(state, stmt.lineno, {letset: out})

    # elif isinstance(stmt, ast.Print):
    #     return _form(
    #         state,
    #         stmt.lineno,
    #         {"log": [_expression(x, state) for x in stmt.values]},
    #     )

    elif isinstance(stmt, ast.For):
        if isinstance(stmt.target, ast.Name):
            newvar = stmt.target.id
            array = _expression(stmt.iter, _newscope(state))
            body = _statements(stmt.body, _newscope(state, [newvar]))
            return _form(
                state, stmt.lineno, OrderedDict([("foreach", newvar), ("in", array), ("do", body), ("seq", True),]),
            )

        elif (
            isinstance(stmt.target, ast.Tuple)
            and len(stmt.target.elts) == 2
            and all(isinstance(x, ast.Name) for x in stmt.target.elts)
        ):
            keyvar = stmt.target.elts[0].id
            valvar = stmt.target.elts[1].id
            mapping = _expression(stmt.iter, _newscope(state))
            body = _statements(stmt.body, _newscope(state, [keyvar, valvar]))
            return _form(
                state,
                stmt.lineno,
                OrderedDict([("forkey", keyvar), ("forval", valvar), ("in", mapping), ("do", body),]),
            )

    elif isinstance(stmt, ast.While):
        test = _expression(stmt.test, _newscope(state))
        body = _statements(stmt.body, _newscope(state))
        return _form(state, stmt.lineno, OrderedDict([("while", test), ("do", body)]))

    elif isinstance(stmt, ast.If):
        chain = _ifchain(state, stmt, [])
        if len(chain) == 1:
            return _form(state, stmt.lineno, chain[0])
        elif len(chain) == 2 and not isinstance(chain[1], OrderedDict):
            chain[0]["else"] = chain[1]
            return _form(state, stmt.lineno, chain[0])
        elif not isinstance(chain[-1], OrderedDict):
            ifThens, elseClause = chain[:-1], chain[-1]
            return _form(state, stmt.lineno, OrderedDict([("cond", ifThens), ("else", elseClause)]),)
        else:
            return _form(state, stmt.lineno, OrderedDict([("cond", chain)]))

    elif isinstance(stmt, ast.Raise):
        if isinstance(stmt.type, ast.Str):
            return _form(state, stmt.lineno, {"error": stmt.type.s})

    elif isinstance(stmt, ast.Expr):
        return _expression(stmt.value, state)

    elif isinstance(stmt, ast.Pass):
        return _form(state, stmt.lineno, {"doc": ""})

    raise Exception(
        "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(ast.dump(stmt), stmt.lineno)
    )


def _statements(stmts, state):
    return [_statement(x, state) for x in stmts]


def _form(state, lineno, others):
    if state["options"]["lineNumbers"] and lineno is not None:
        return OrderedDict([("@", "Python line {0}".format(lineno))] + others.items())
    else:
        return others


def _newscope(state, newvars=None):
    newstate = dict(state)
    newstate["symbols"] = set(newstate["symbols"])
    if newvars is not None:
        for x in newvars:
            newstate["symbols"].add(x)
    return newstate


def _literal(expr, state):
    if isinstance(expr, ast.Dict):
        out = OrderedDict()
        for key, value in zip(expr.keys, expr.values):
            if isinstance(key, ast.Str) or isinstance(key, ast.Name) and isinstance(state["subs"].get(key.id, None)):
                kkey = _literal(key, state)
                vvalue = _literal(value, state)
                out[kkey] = vvalue
            else:
                raise Exception(
                    "literal JSON keys must be strings or subs identifiers, not {0} (source line {1})".format(
                        ast.dump(expr), expr.lineno
                    )
                )
        return out

    elif isinstance(expr, ast.Num):
        return expr.n

    elif isinstance(expr, ast.Str):
        return expr.s

    elif isinstance(expr, ast.Name):
        if expr.id in state["subs"]:
            return state["subs"][expr.id]
        elif expr.id == "None":
            return None
        elif expr.id == "True":
            return True
        elif expr.id == "False":
            return False
        else:
            raise Exception(
                "identifiers ({0}) are not allowed in a literal expression, unless they are subs identifiers (source line {1})".format(
                    ast.dump(expr), expr.lineno
                )
            )

    elif isinstance(expr, ast.List):
        out = []
        for value in expr.elts:
            out.append(_literal(value, state))
        return out

    raise Exception("Python AST node {0} (source line {1}) is not literal JSON".format(ast.dump(expr), expr.lineno))


def _expression(expr, state):
    if isinstance(expr, ast.BoolOp):
        if isinstance(expr.op, ast.And):
            andor = "&&"
        else:
            andor = "||"

        items = list(reversed(expr.values))
        out = _form(
            state,
            expr.lineno,
            {andor: [_expression(items.pop(), _newscope(state)), _expression(items.pop(), _newscope(state)),]},
        )

        while len(items) > 0:
            out = _form(state, expr.lineno, {andor: [out, _expression(items.pop(), _newscope(state))]},)

        return out

    elif isinstance(expr, ast.BinOp):
        if isinstance(expr.op, ast.Add):
            op = "+"
        elif isinstance(expr.op, ast.Sub):
            op = "-"
        elif isinstance(expr.op, ast.Mult):
            op = "*"
        elif isinstance(expr.op, ast.Div):
            op = "/"
        elif isinstance(expr.op, ast.Mod):
            op = "%"
        elif isinstance(expr.op, ast.Pow):
            op = "**"
        elif isinstance(expr.op, ast.LShift):
            raise Exception(
                "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(
                    ast.dump(expr), expr.lineno
                )
            )
        elif isinstance(expr.op, ast.RShift):
            raise Exception(
                "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(
                    ast.dump(expr), expr.lineno
                )
            )
        elif isinstance(expr.op, ast.BitOr):
            op = "|"
        elif isinstance(expr.op, ast.BitXor):
            op = "^"
        elif isinstance(expr.op, ast.BitAnd):
            op = "&"
        elif isinstance(expr.op, ast.FloorDiv):
            op = "//"
        return _form(
            state,
            expr.lineno,
            {op: [_expression(expr.left, _newscope(state)), _expression(expr.right, _newscope(state)),]},
        )

    elif isinstance(expr, ast.UnaryOp):
        if isinstance(expr.op, ast.Invert):
            op = "~"
        elif isinstance(expr.op, ast.Not):
            op = "!"
        elif isinstance(expr.op, ast.UAdd):
            raise Exception(
                "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(
                    ast.dump(expr), expr.lineno
                )
            )
        elif isinstance(expr.op, ast.USub):
            op = "u-"
        return _form(state, expr.lineno, {op: _expression(expr.operand, _newscope(state))},)

    elif isinstance(expr, ast.IfExp):
        test = _expression(expr.test, _newscope(state))
        thenClause = _expression(expr.body, _newscope(state))
        elseClause = _expression(expr.orelse, _newscope(state))
        return _form(state, expr.lineno, OrderedDict([("if", test), ("then", thenClause), ("else", elseClause)]),)

    elif isinstance(expr, ast.Dict):
        return _literal(expr, state)

    elif isinstance(expr, ast.Compare):

        def opname(x):
            if isinstance(x, ast.Eq):
                return "=="
            elif isinstance(x, ast.NotEq):
                return "!="
            elif isinstance(x, ast.Lt):
                return "<"
            elif isinstance(x, ast.LtE):
                return "<="
            elif isinstance(x, ast.Gt):
                return ">"
            elif isinstance(x, ast.GtE):
                return ">="
            else:
                raise Exception(
                    "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(ast.dump(x), x.lineno)
                )

        ops = list(reversed(expr.ops))
        cmps = list(reversed(expr.comparators))

        lastexpr = _expression(cmps.pop(), _newscope(state))
        out = _form(state, expr.lineno, {opname(ops.pop()): [_expression(expr.left, _newscope(state)), lastexpr,]},)

        while len(ops) > 0 and len(cmps) > 0:
            newexpr = _expression(cmps.pop(), _newscope(state))
            out = _form(
                state,
                expr.lineno,
                {"&&": [out, _form(state, expr.lineno, {opname(ops.pop()): [lastexpr, newexpr]},),]},
            )
            lastexpr = newexpr

        return out

    elif isinstance(expr, ast.Call):

        def unfold(x):
            if isinstance(x, ast.Name):
                return x.id
            elif isinstance(x, ast.Attribute):
                return unfold(x.value) + "." + x.attr
            else:
                raise Exception(
                    "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(ast.dump(x), x.lineno)
                )

        specialForms = [
            "Int",
            "Long",
            "Float",
            "Double",
            "String",
            "Base64",
            "Type",
            "Value",
            "New",
            "Do",
            "Let",
            "Set",
            "Attr",
            "Path",
            "To",
            "Cell",
            "Pool",
            "Init",
            "If",
            "Then",
            "Else",
            "Cond",
            "While",
            "Until",
            "For",
            "Step",
            "Foreach",
            "In",
            "Forkey",
            "Forval",
            "Cast",
            "Cases",
            "Partial",
            "Upcast",
            "As",
            "Ifnotnull",
            "Doc",
            "Error",
            "Log",
            "Namespace",
            "Params",
            "Ret",
            "Fcn",
        ]
        coreLibrary = {
            "Plus": "+",
            "Minus": "-",
            "Times": "*",
            "Divide": "/",
            "FloorDivide": "//",
            "Negative": "U-",
            "Modulo": "%",
            "Remainder": "%%",
            "Pow": "**",
            "Comparison": "cmp",
            "Equal": "==",
            "GreaterOrEqual": ">=",
            "GreaterThan": ">",
            "NotEqual": "!=",
            "LessThan": "<",
            "LessOrEqual": "<=",
            "Max": "max",
            "Min": "min",
            "And": "&&",
            "Or": "||",
            "XOr": "^^",
            "Not": "!",
            "BitwiseAnd": "&",
            "BitwiseOr": "|",
            "BitwiseXOr": "^",
            "BitwiseNot": "~",
        }

        name = unfold(expr.func)
        if name in specialForms:
            name = name.lower()
        name = coreLibrary.get(name, name)

        args = [_expression(x, _newscope(state)) for x in expr.args]
        if len(args) == 1:
            args = args[0]

        if (
            name
            in [
                "string",
                "base64",
                "value",
                "attr",
                "cell",
                "pool",
                "foreach",
                "forkey",
                "forval",
                "doc",
                "error",
                "fcn",
            ]
            and isinstance(args, dict)
            and len(args) == 1
            and args.keys() == ["string"]
        ):
            (args,) = args.values()

        out = OrderedDict([(name, args)])

        for kwd in expr.keywords:
            kwdarg = kwd.arg
            if kwdarg in specialForms:
                kwdarg = kwdarg.lower()
            out[kwdarg] = _expression(kwd.value, _newscope(state))

        return _form(state, expr.lineno, out)

    elif isinstance(expr, ast.Num):
        return expr.n

    elif isinstance(expr, ast.Str):
        return {"string": expr.s}

    elif isinstance(expr, ast.Attribute):
        return _unfold(expr, [], state)

    elif isinstance(expr, ast.Subscript):
        return _unfold(expr, [], state)

    elif isinstance(expr, ast.Name):
        if expr.id in state["subs"]:
            return state["subs"][expr.id]
        elif expr.id == "None":
            return None
        elif expr.id == "True":
            return True
        elif expr.id == "False":
            return False
        else:
            return expr.id

    elif isinstance(expr, ast.List):
        return _literal(expr, state)

    elif isinstance(expr, ast.Tuple):
        return [_expression(x, state) for x in expr.elts]

    raise Exception(
        "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(ast.dump(expr), expr.lineno)
    )


def _unfold(x, path, state):
    if isinstance(x, ast.Attribute):
        path.insert(0, {"string": x.attr})
        return _unfold(x.value, path, state)

    elif isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Index):
        path.insert(0, _expression(x.slice.value, state))
        return _unfold(x.value, path, state)

    else:
        if isinstance(x, ast.Name) and x.id in state["cells"]:
            return _form(state, x.lineno, OrderedDict([("cell", x.id), ("path", path)]))
        elif isinstance(x, ast.Name) and x.id in state["pools"]:
            return _form(state, x.lineno, OrderedDict([("pool", x.id), ("path", path)]))
        else:
            return _form(state, x.lineno, OrderedDict([("attr", _expression(x, state)), ("path", path)]),)


class UnhandledKeyType(object):
    """
    A dictionary key of a type that we cannot or do not check for duplicates.
    """


class VariableKey(object):
    """
    A dictionary key which is a variable.
    @ivar item: The variable AST object.
    """

    def __init__(self, item):
        self.name = item.id

    def __eq__(self, compare):
        return compare.__class__ == self.__class__ and compare.name == self.name

    def __hash__(self):
        return hash(self.name)


def convert_to_value(item):
    if isinstance(item, ast.Str):
        return item.s
    elif hasattr(ast, "Bytes") and isinstance(item, ast.Bytes):
        return item.s
    elif isinstance(item, ast.Tuple):
        return tuple(convert_to_value(i) for i in item.elts)
    elif isinstance(item, ast.Num):
        return item.n
    elif isinstance(item, ast.Name):
        return item.id
    elif isinstance(item, ast.NameConstant):
        # None, True, False are nameconstants in python3, but names in 2
        return item.value
    else:
        return None


class ArgumentVisitor(ast.NodeVisitor):
    """Reports which arguments a function contains."""

    def __init__(self, *args, **kwargs):
        # type: (List[Any], Dict[str, Any]) -> None

        # https://github.com/python/mypy/issues/5887
        super(ArgumentVisitor, self).__init__(*args, **kwargs)  # type: ignore

        # The arguments found in the function.
        self.arguments = list()  # type: List[str]
        self.types = list()  # type: List[str]
        self.defaults = list()  # type: List[str]
        self.lineno = list()  # Line numbers of the args type: List[int]

    def xFusion_expression(self, expr, path):
        if isinstance(expr, ast.Num):
            return expr.n
        elif isinstance(expr, ast.Str):
            return {"string": expr.s}
        elif isinstance(expr, ast.Attribute):
            return self.xFusion_unfold(expr, path)
        elif isinstance(expr, ast.Subscript):
            return self.xFusion_unfold(expr, path)
        elif isinstance(expr, ast.Name):
            if expr.id == "None":
                return None
            elif expr.id == "True":
                return True
            elif expr.id == "False":
                return False
            else:
                return expr.id
        elif isinstance(expr, ast.Tuple):
            return [self.xFusion_expression(x, path) for x in expr.elts]
        raise Exception(
            "Python AST node {0} (source line {1}) does not have a PFA equivalent".format(ast.dump(expr), expr.lineno)
        )

    def xFusion_unfold(self, x, path):
        if isinstance(x, ast.Attribute):
            self.xFusion_unfold(x.value, path)
        elif isinstance(x, ast.Subscript):
            if isinstance(x.slice, ast.Index):
                path.append(getattr(x.value, "id"))
                path.append("[")
                self.xFusion_unfold(x.slice, path)
                path.append("]")
        elif isinstance(x, ast.Index):
            return self.xFusion_unfold(x.value, path)
        elif isinstance(x, ast.Tuple):
            for elt in x.elts:
                self.xFusion_unfold(elt, path)
                if elt != x.elts[-1]:
                    path.append(",")
        elif isinstance(x, ast.List):
            path.append("[")
            for elt in x.elts:
                self.xFusion_unfold(elt, path)
                if elt != x.elts[-1]:
                    path.append(",")
            path.append("]")
        else:
            if isinstance(x, ast.Name):
                z = getattr(x, "id")
                path.append(z)
            elif isinstance(x, ast.Str):
                path.append(f"'{x.s}'")
            elif isinstance(x, ast.NameConstant):
                # None, True, False are nameconstants in python3, but names in 2
                val = ""
                if x.value == None:
                    val = "None"
                if x.value == True:
                    val = "True"
                if x.value == False:
                    val = "False"
                path.append(val)
            else:
                print(f"xFusion_unfold: Unkown instance {x}")

    def xFusion_extract_complex_arg(self, name, arg):
        lista = []
        self.xFusion_unfold(arg, lista)
        return "".join(lista)

    def add_arg_by_name(self, name, arg):
        if name not in ["self", "*args", "**kwargs"]:
            self.arguments.append(name)
            self.lineno.append(arg.lineno)
            if arg.annotation is not None:
                if hasattr(arg.annotation, "id"):
                    self.types.append(arg.annotation.id)
                elif isinstance(arg.annotation, ast.Subscript):
                    complex = self.xFusion_extract_complex_arg(arg.arg, arg.annotation)
                    self.types.append(complex)
                else:
                    self.types.append(None)
            else:
                self.types.append(None)

    def visit_arguments(self, node):
        # type: (ast.arguments) -> ast.AST
        if hasattr(node, "posonlyargs"):
            for arg in node.posonlyargs:
                # pprint("===>node.posonlyargs")
                # astpretty.pprint(arg.arg)
                # pprint("====================")
                self.add_arg_by_name(arg.arg, arg)

        if hasattr(node, "args"):
            for arg in node.args:
                # pprint("===>node.args")
                # astpretty.pprint(arg.arg)
                # pprint("====================")
                self.add_arg_by_name(arg.arg, arg)

        if hasattr(node, "kwonlyargs"):
            for arg in node.kwonlyargs:
                # pprint("===>node.kwonlyargs")
                # astpretty.pprint(node.kwonlyargs)
                # pprint("====================")
                self.add_arg_by_name(arg.arg, arg)

        if hasattr(node, "kw_defaults") and len(node.kw_defaults) > 0:
            for arg in node.kw_defaults:
                # pprint("===>node.kw_defaults")
                # astpretty.pprint(arg)
                # pprint("====================")
                if arg:
                    self.defaults.append(convert_to_value(arg))
                else:
                    self.defaults.append("**NO_DEFAULT**")

        if len(self.defaults) == 0 and hasattr(node, "defaults") and len(node.defaults) > 0:
            line_first_default = node.defaults[0].lineno
            line_first_arg = self.lineno[0]
            if line_first_default > line_first_arg:
                # There are some arguments without default values
                # TODO Check this funcionality
                # print(f"EXISTS defaults starting: {line_first_default} VS ALL: {line_first_arg}")
                # pylint: disable=unused-variable
                for i in range(line_first_default - line_first_arg):
                    self.defaults.append("**NO_DEFAULT**")
            for arg in node.defaults:
                # pprint("===>node.defaults")
                # astpretty.pprint(arg)
                # pprint("====================")
                if arg:
                    self.defaults.append(convert_to_value(arg))
                else:
                    self.defaults.append(None)

        # Handle single-star arguments.
        if node.vararg is not None:
            # pprint("===>node.vararg")
            # astpretty.pprint(node.vararg)
            # pprint("====================")
            name = "*" + node.vararg.arg
            self.add_arg_by_name(name, node.vararg)

        if node.kwarg is not None:
            name = "**" + node.kwarg.arg
            self.add_arg_by_name(name, node.kwarg)

        return self.generic_visit(node)
