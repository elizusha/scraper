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
    state_path = os.path.join(args.output_directory, "state.json")
    if not os.path.exists(state_path):
        with open(state_path, "w") as f:
            new_state = {
                "saved_pages": {},
                "new_pages": [args.input_link],
                "counter": 0,
            }
            f.write(json.dumps(new_state))
    state = json.load(open(state_path))
    while state["new_pages"]:
        page = state["new_pages"].pop()
        print("CURRENT_PAGE:", page)
        page_url = urlparse(page)
        try:
            file_name = str(state["counter"]) + ".html"
            state["saved_pages"][page] = file_name
            state["counter"] += 1
            urllib.request.urlretrieve(
                page, os.path.join(args.output_directory, file_name)
            )
            time.sleep(1)
            # save state
            response = requests.get(page)
            time.sleep(1)
        except:
            print(":(")
            continue
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup.findAll("a"):
            if "href" in str(tag):
                link = tag["href"]
                print("#", link)
                link_url = urlparse(link)
                link_url = link_url._replace(
                    scheme=link_url.scheme or page_url.scheme,
                    netloc=link_url.netloc or page_url.netloc,
                )
                if link_url.netloc != page_url.netloc:
                    print(f"Link to different site: {link_url.netloc} != {page_url.netloc}")
                    continue
                link = link_url.geturl()
                print("NORMALIZED_LINK:", link)
                if link in state["saved_pages"]:
                    print(f"Link already saved")
                    continue
                if link in state["new_pages"]:
                    print(f"Link already in queue")
                    continue
                print("NEW_LINK:", link)
                state["new_pages"].append(link)


if __name__ == "__main__":
    main()
