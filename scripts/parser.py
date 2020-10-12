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
    parser.add_argument("input_dir", help="directory with html files")
    parser.add_argument("output_dir", help="directory with ntriples files")
    return parser.parse_args()


def upload_blob(bucket_name, source_file, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(source_file)

def download_blob(bucket_name, source_blob_name, destination_file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

def main():
    g = Graph()
    args = parse_args()
    client = storage.Client()
    bucket = client.bucket("wikidata-collab-1-crawler")
    blobs = client.list_blobs(bucket, prefix=os.path.join(args.input_dir, "html_data"))
    for blob in blobs:
        path = blob.name
        print(path)
        print("HTML: ", path, end=" --- ")
        data_file_path = "../tmp.html"
        download_blob("wikidata-collab-1-crawler", path, data_file_path)
        with open(data_file_path) as file:
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
            result_path = os.path.join(args.output_dir, "nt_data", f"{os.path.splitext(base)[0]}.nt")
            upload_blob("wikidata-collab-1-crawler", g_nt, result_path)
            print("OK")


if __name__ == "__main__":
    main()
