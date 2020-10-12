#!/usr/bin/env python3

import rdflib
import json
import glob
import os
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
            g = Graph()
            g.parse(data=json_data, format="json-ld")
            if not g:
                print("No json-ld data")
                continue
            g_nt = g.serialize(format="ntriples").decode("utf-8")
            base = os.path.basename(path)
            with open(f"../result/{os.path.splitext(base)[0]}.nt", "w") as output:
                output.write(g_nt)
            print("OK")


if __name__ == "__main__":
    main()
