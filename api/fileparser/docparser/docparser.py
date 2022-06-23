"""
Docstring Parser

Extracts information from the Docstring of a Class:

- Description
- Parameters
- Return value

Based on:
- https://github.com/offscale/cdd-python
- https://github.com/offscale/cdd-python/blob/37810ff/doctrans/info.py
- https://github.com/openstack/rally
- https://github.com/openstack/rally/blob/master/rally/common/plugin/info.py
"""

import re
import sys

PARAM_OR_RETURNS_REGEX = re.compile(":(?:param|returns?)")
RETURNS_REGEX = re.compile(":returns?: (?P<doc>.*)", re.S)
PARAM_REGEX = re.compile(
    r":param (?P<name>[\*\w]+): (?P<doc>.*?)" r"(?:(?=:param)|(?=:return)|(?=:raises)|\Z)",
    re.S,
)


class DocParser:
    """Implements the parsing of the Docstring of a Class"""

    def __init__(self, docstring):
        """Receives the Docstring to be parsed"""
        self.docstring = docstring

    def parse(self):
        """Returns the extracted information from the Docstring"""
        doc = self._parse_docstring(self.docstring)
        # Clean new lines and multiples spaces
        for param in doc["params"]:
            param["doc"] = " ".join(param["doc"].split())
        # TODO
        # description = "".join(doc['short_description'].splitlines())
        # print(description)
        # print("***********************")
        description = (
            f"{doc['short_description']} {' '.join(doc['long_description'].splitlines())}".replace("\t", " ")
            .replace("  ", " ")
            .replace("  ", " ")
            .replace("  ", " ")
        )
        return {
            "description": description,
            "parameters": doc["params"],
            "returns": doc["returns"],
        }

    def _trim(self, docstring):
        """trim function from PEP-257"""
        if not docstring:
            return ""
        # Convert tabs to spaces (following the normal Python rules)
        # and split into a list of lines:
        lines = docstring.expandtabs().splitlines()
        # Determine minimum indentation (first line doesn't count):
        indent = sys.maxsize
        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
        # Remove indentation (first line is special):
        trimmed = [lines[0].strip()]
        if indent < sys.maxsize:
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())
        # Strip off trailing and leading blank lines:
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        # Current code/unittests expects a line return at
        # end of multiline docstrings
        # workaround expected behavior from unittests
        if "\n" in docstring:
            trimmed.append("")
        # Return a single string:
        return "\n".join(trimmed)

    def _reindent(self, string):
        return "\n".join(line.strip() for line in string.strip().split("\n"))

    def _doc_to_type_doc(self, name, doc):
        doc = self._trim(doc).splitlines()
        docs, typ = [], []
        for line in doc:
            if line.startswith(":type"):
                line = line[len(":type ") :]
                colon_at = line.find(":")
                # TODO
                # found_name = line[:colon_at]
                # assert name == found_name, "{!r} != {!r}".format(
                #     name, found_name
                # )
                line = line[colon_at + 2 :]
                typ.append(line[3:-3] if line.startswith("```") and line.endswith("```") else line)
            elif len(typ):
                typ.append(line)
            else:
                docs.append(line)
        return dict(doc="\n".join(docs), **{"typ": "\n".join(typ)} if len(typ) else {})

    def _parse_docstring(self, docstring):
        """Parse the docstring into its components.
        :returns: a dictionary of form
                {
                    'short_description': ...,
                    'long_description': ...,
                    'params': [{'name': ..., 'doc': ..., 'typ': ...}, ...],
                    "returns': {'name': ..., 'typ': ...}
                }
        """
        short_description = long_description = returns = ""
        params = []
        if docstring:
            docstring = self._trim(docstring.lstrip("\n"))
            lines = docstring.split("\n", 1)
            short_description = lines[0]
            if len(lines) > 1:
                long_description = lines[1].strip()
                params_returns_desc = None
                match = PARAM_OR_RETURNS_REGEX.search(long_description)
                if match:
                    long_desc_end = match.start()
                    params_returns_desc = long_description[long_desc_end:].strip()
                    long_description = long_description[:long_desc_end].rstrip()
                if params_returns_desc:
                    params = [
                        dict(name=name, **self._doc_to_type_doc(name, doc))
                        for name, doc in PARAM_REGEX.findall(params_returns_desc)
                    ]
                    match = RETURNS_REGEX.search(params_returns_desc)
                    if match:
                        returns = self._reindent(match.group("doc"))
                    if returns:
                        r_dict = {"name": ""}
                        for idx, char in enumerate(returns):
                            if char == ":":
                                r_dict["typ"] = returns[idx + len(":rtype:") :].strip()
                                if r_dict["typ"].startswith("```") and r_dict["typ"].endswith("```"):
                                    r_dict["typ"] = r_dict["typ"][3:-3]
                                break
                            else:
                                r_dict["name"] += char
                        r_dict["name"] = r_dict["name"].rstrip()
                        returns = r_dict
        return {
            "short_description": short_description,
            "long_description": long_description,
            "params": params,
            "returns": returns,
        }
