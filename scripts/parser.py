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
from rdflib import Graph, URIRef, Literal, ConjunctiveGraph


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", help="directory with data files")
    parser.add_argument(
        "--bucket_name", help="storage bucket", default="wikidata-collab-1-crawler"
    )
    return parser.parse_args()


def strip_strings(data):
    if isinstance(data, str):
        return data.strip()
    if isinstance(data, list):
        return [strip_strings(element) for element in data]
    if isinstance(data, dict):
        return {key.strip(): strip_strings(value) for key, value in data.items()}
    return data


class Parser:
    def __init__(self, args):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(args.bucket_name)
        self.work_dir = args.work_dir
        self.page_urls = self._get_page_urls()

    def _get_page_urls(self):
        blob = self.bucket.blob(os.path.join(self.work_dir, "state.json"))
        json_string = blob.download_as_string().decode()
        state_json = json.loads(json_string)
        if "processed_pages" in state_json:
            url_by_filename = {
                value["file_name"]: url
                for url, value in state_json["processed_pages"].items()
                if value["status_code"] == 200 and value["file_name"]
            }
        else:
            url_by_filename = {
                value: url
                for url, value in state_json["saved_pages"].items()
            }
        return url_by_filename

    def parse(self):
        for blob in self._list_input_htmls():
            print("HTML: ", blob.name, end=" --- ")
            json_data = self._extract_json_data(blob)
            if json_data is None:
                continue
            graph = ConjunctiveGraph(store="IOMemory")
            graph.parse(
                data=json_data,
                format="json-ld",
                publicID=self.page_urls[os.path.basename(blob.name)],
            )
            if not graph:
                print("No json-ld data")
                continue
            result_path = os.path.join(
                self.work_dir,
                "nq_data",
                f"{os.path.splitext(os.path.basename(blob.name))[0]}.nq",
            )
            self.bucket.blob(result_path).upload_from_string(
                graph.serialize(format="nquads").decode()
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
            return json.dumps(strip_strings(data))
        except Exception as e:
            print("Extraction error")
            return None


def main():
    args = parse_args()

    parser = Parser(args)
    parser.parse()


if __name__ == "__main__":
    main()
