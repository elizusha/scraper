#!/usr/bin/env python3

import rdflib
import json
import glob
import os
import argparse
from google.cloud import storage
from extruct.jsonld import JsonLdExtractor
from rdflib.plugin import register, Parser

register("json-ld", Parser, "rdflib_jsonld.parser", "JsonLDParser")
from rdflib import Graph, URIRef, Literal


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", help="directory with data files")
    parser.add_argument(
        "--bucket_name", help="storage bucket", default="wikidata-collab-1-crawler"
    )
    return parser.parse_args()


class Parser:
    def __init__(self, args):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(args.bucket_name)
        self.work_dir = args.work_dir

    def parse(self):
        for blob in self._list_input_htmls():
            print("HTML: ", blob.name, end=" --- ")
            json_data = self._extract_json_data(blob)
            if json_data is None:
                continue
            graph = Graph()
            graph.parse(data=json_data, format="json-ld")
            if not graph:
                print("No json-ld data")
                continue
            result_path = os.path.join(
                self.work_dir,
                "nt_data",
                f"{os.path.splitext(os.path.basename(blob.name))[0]}.nt",
            )
            self.bucket.blob(result_path).upload_from_string(
                graph.serialize(format="ntriples").decode()
            )
            print("OK")

    def _list_input_htmls(self):
        return self.storage_client.list_blobs(
            self.bucket, prefix=os.path.join(self.work_dir, "html_data")
        )

    def _extract_json_data(self, blob):
        html = blob.download_as_string().decode()
        try:
            jslde = JsonLdExtractor()
            data = jslde.extract(html)
            return json.dumps(data)
        except Exception as e:
            print("Extraction error")
            return None


def main():
    args = parse_args()

    parser = Parser(args)
    parser.parse()


if __name__ == "__main__":
    main()
