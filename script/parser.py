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
    paths = glob.glob("/home/elizusha/data_extractor/data/*.html")
    for path in paths:
        print("HTML: ", path, end=" --- ")
        with open(path) as file:
            try:
                html = file.read()
                jslde = JsonLdExtractor()
                data = jslde.extract(html)
            except Exception as e:
                print("Extraction error")
                continue
            json_data = json.dumps(data)
            g.parse(data=json_data, format="json-ld")
            print("OK")
    print("++++++++++++++++++++++++++++++++++++++++++")
    g_turtle = g.serialize(format="turtle").decode("utf-8")
    print(g_turtle)
    with open("../result.ttl", "w") as output:
        output.write(g_turtle)


if __name__ == "__main__":
    main()
