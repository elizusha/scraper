#!/usr/bin/env python3

import json
import argparse
from google.cloud import storage
from urllib.parse import urlparse, urlunparse
from extruct.jsonld import JsonLdExtractor
from rdflib.plugin import register, Parser
from os.path import basename, join, splitext

register("json-ld", Parser, "rdflib_jsonld.parser", "JsonLDParser")
from rdflib import Graph, URIRef, Literal, ConjunctiveGraph


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("work_dir", help="directory with data files")
    parser.add_argument(
        "--bucket_name", help="storage bucket", default="wikidata-collab-1-crawler"
    )
    parser.add_argument(
        "--common_graph",
        action="store_true",
        default=False,
        help="one graph name for the whole site",
    )
    parser.add_argument(
        "--http_to_https",
        action="store_true",
        default=False,
        help="replace http://schema.org to https://schema.org",
    )
    return parser.parse_args()


def strip_strings(data):
    if isinstance(data, str):
        if data.startswith("http"):
            return urlunparse(urlparse(data))
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
        self.common_graph = args.common_graph
        self.http_to_https = args.http_to_https

    def _get_page_urls(self):
        blob = self.bucket.blob(join(self.work_dir, "state.json"))
        json_string = blob.download_as_string().decode()
        state_json = json.loads(json_string)
        if "processed_pages" in state_json:
            url_by_filename = {
                value["file_name"]: url
                for url, value in state_json["processed_pages"].items()
                if value["status_code"] < 400 and value["file_name"]
            }
        else:
            url_by_filename = {
                value: url for url, value in state_json["saved_pages"].items()
            }
        return url_by_filename

    def parse(self):
        for blob in self._list_input_htmls():
            print("HTML: ", blob.name, end=" --- ")
            try:
                json_data = self._extract_json_data(blob)
            except Exception:
                print("Extraction error")
                continue
            if json_data is None:
                print("No json data")
                continue
            graph = ConjunctiveGraph(store="IOMemory")
            data_directory = "nq_data"
            if self.http_to_https:
                data_directory += "_https"
            if self.common_graph:
                public_id = (
                    ""
                    if "1.html" not in self.page_urls
                    else (
                        urlparse(self.page_urls["1.html"])._replace(
                            path="", params="", query="", fragment=""
                        )
                    ).geturl()
                )
                data_directory += "_common_graph"
            else:
                public_id = (
                    ""
                    if basename(blob.name) not in self.page_urls
                    else self.page_urls[basename(blob.name)]
                )
            if not public_id:
                print("File not found")
                continue
            graph.parse(
                data=json_data,
                format="json-ld",
                publicID=public_id,
            )
            if not graph:
                print("No json-ld data")
                continue
            result_path = join(
                self.work_dir,
                data_directory,
                f"{splitext(basename(blob.name))[0]}.nq",
            )
            try:
                nq_data = graph.serialize(format="nquads").decode()
                if self.http_to_https:
                    nq_data = nq_data.replace("http://schema.org", "https://schema.org")
                self.bucket.blob(result_path).upload_from_string(nq_data)
            except Exception:
                print("Extraction error")
            print("OK")

    def _list_input_htmls(self):
        return self.storage_client.list_blobs(
            self.bucket, prefix=join(self.work_dir, "html_data")
        )

    def _extract_json_data(self, blob):
        html = blob.download_as_string().decode()
        jslde = JsonLdExtractor()
        data = jslde.extract(html)
        return json.dumps(strip_strings(data))


def main():
    args = parse_args()
    parser = Parser(args)
    parser.parse()


if __name__ == "__main__":
    main()
