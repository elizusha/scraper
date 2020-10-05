#!/usr/bin/env python3

import rdflib
import json
import glob

from extruct.jsonld import JsonLdExtractor
from rdflib.plugin import register, Parser

register("json-ld", Parser, "rdflib_jsonld.parser", "JsonLDParser")
from rdflib import Graph, URIRef, Literal


def main():
    g = Graph()
    paths = glob.glob("/home/elizusha/data_extractor/data/*")
    for path in paths:
        file = open(path)
        html = file.read()
        jslde = JsonLdExtractor()
        data = jslde.extract(html)
        json_data = json.dumps(data)
        g.parse(data=json_data, format="json-ld")
    print(g.serialize(format="n3").decode("utf-8"))


if __name__ == "__main__":
    main()
