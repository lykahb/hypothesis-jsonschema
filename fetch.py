"""
Fetch lots of real-world schemata to test against.

Uses https://github.com/json-schema-org/JSON-Schema-Test-Suite for big and
complex schemata, and http://schemastore.org/json/ for smaller schemata
that - as the official test suite - should cover each feature in the spec.
"""

import concurrent.futures
import io
import json
import urllib.request
import zipfile
from typing import Any


def get_json(url: str) -> Any:
    """Fetch the json payload at the given url."""
    with urllib.request.urlopen(url) as handle:
        return json.load(handle)


# Load cached schemas, so we cope with flaky connections and keep deleted entries
try:
    with open("corpus-schemastore-catalog.json") as f:
        schemata = json.load(f)
except FileNotFoundError:
    schemata = {}

# Download all the examples known to schemastore.org, concurrently!
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for future in concurrent.futures.as_completed(
        ex.submit(lambda c: (c["description"], get_json(c["url"])), c)
        for c in get_json("http://schemastore.org/api/json/catalog.json")["schemas"]
    ):
        try:
            name, value = future.result()
            schemata[name] = value
        except Exception:
            print(f"Could not retrieve schema: {name}")

# Dump them all back to the catalog file.
with open("corpus-schemastore-catalog.json", mode="w") as f:
    json.dump(schemata, f, indent=4, sort_keys=True)


# Part two: fetch the official jsonschema compatibility test suite
suite: dict = {}
invalid_suite: dict = {}

with urllib.request.urlopen(
    "https://github.com/json-schema-org/JSON-Schema-Test-Suite/archive/master.zip"
) as handle:
    start = "JSON-Schema-Test-Suite-master/tests/draft7/"
    with zipfile.ZipFile(io.BytesIO(handle.read())) as zf:
        for path in zf.namelist():
            if "/optional/" in path or not (
                path.startswith(start) and path.endswith(".json")
            ):
                continue
            for v in json.load(zf.open(path)):
                if any(t["valid"] for t in v["tests"]):
                    suite[v["description"]] = v["schema"]
                else:
                    invalid_suite[v["description"]] = v["schema"]

with open("corpus-suite-schemas.json", mode="w") as f:
    json.dump([suite, invalid_suite], f, indent=4, sort_keys=True)