#!/usr/bin/env python3

import os
import json
import requests
import urllib.request
import time
import argparse
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_link", help="site page")
    parser.add_argument("output_directory", help="directory with site pages")
    return parser.parse_args()


def main():
    args = parse_args()
    main_url = urlparse(args.input_link)
    state_path = os.path.join(args.output_directory, "state.json")
    if not os.path.exists(state_path):
        with open(state_path, "w") as f:
            new_state = {
                "saved_pages": {},
                "new_pages": [args.input_link],
                "counter": 0,
            }
            f.write(json.dumps(new_state))
    with open(state_path) as json_file:
        state = json.load(json_file)
    while state["new_pages"]:
        page = state["new_pages"].pop()
        print("CURRENT_PAGE:", page)
        with open("../urls.txt", "a") as f:
            f.write(page+"\n")
        page_url = urlparse(page)
        file_name = str(state["counter"]) + ".html"
        state["saved_pages"][page] = file_name
        state["counter"] += 1
        with open(state_path, 'w') as json_file:
            json.dump(state, json_file)
        try:
            response = requests.get(page, timeout=60)
            time.sleep(1)
        except Exception as e:
            print("Site error")
            print(e)
            continue
        if not response.ok:
             # print("Bad request")
             continue
        content_type = response.headers.get('Content-Type')
        # print("###", content_type)
        if content_type and not content_type.startswith("text/html"):
            # print("Wrong format: ", content_type)
            continue
        with open(os.path.join(args.output_directory, file_name), 'w') as file:
            file.write(response.text)
        soup = BeautifulSoup(response.text, "html.parser")


        for tag in soup.findAll("a"):
            if "href" in str(tag):
                link = tag["href"]
                # print("#", link)
                link_url = urlparse(link)
                if link_url.scheme not in ["http", "https", ""]:
                    # print(f"Link to different site: {link_url.scheme} != {page_url.scheme}")
                    continue
                if page_url.path and page_url.path[-1] == "/":
                    new_path = os.path.join(page_url.path, link_url.path)
                else:
                    new_path = link_url.path
                link_url = link_url._replace(
                    scheme=link_url.scheme or page_url.scheme,
                    netloc=link_url.netloc or page_url.netloc,
                    path=os.path.normpath(new_path)
                )
                if link_url.netloc != page_url.netloc:
                    # print(f"    Link to different site: {link_url.netloc} != {page_url.netloc}")
                    continue
                link = link_url.geturl()
                # print("NORMALIZED_LINK:", link)
                if link in state["saved_pages"]:
                    # print(f"    Link already saved")
                    continue
                if link in state["new_pages"]:
                    # print(f"    Link already in queue")
                    continue
                # print(" New link:", link)
                state["new_pages"].append(link)


if __name__ == "__main__":
    main()
