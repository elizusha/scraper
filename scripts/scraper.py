#!/usr/bin/env python3

import os
import json
import requests
import urllib.request
import time
import argparse
import logging
import urllib.robotparser
from selenium import webdriver
from google.cloud import storage
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from typing import NamedTuple, List, Dict, Optional, Any
from urllib.parse import urlencode, parse_qsl
from os.path import join, normpath


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("start_link", help="site page")
    parser.add_argument("work_dir", help="google cloud directory")
    parser.add_argument(
        "--bucket_name", help="storage bucket", default="wikidata-collab-1-crawler"
    )
    parser.add_argument(
        "--chromedriver_path",
        help="chromedriver full path",
        default="/home/elizusha/soft/chromedriver/chromedriver",
    )
    parser.add_argument(
        "--start_new", action="store_true", default=False, help="ignore status.json and start scraper"
    )
    return parser.parse_args()


class ScrapedPageInfo(NamedTuple):
    file_name: Optional[str]
    status_code: int
    site_error: str


class ScraperState:
    def __init__(
        self,
        counter: int,
        page_queue: List[str],
        processed_pages: Dict[str, ScrapedPageInfo],
    ):
        self.counter: int = counter
        self.page_queue: List[str] = page_queue
        self.processed_pages: Dict[str, ScrapedPageInfo] = processed_pages

    @staticmethod
    def from_json(json_str: str) -> "ScraperState":
        json_data: Dict[str, Any] = json.loads(json_str)
        return ScraperState(
            counter=json_data["counter"],
            page_queue=json_data["page_queue"],
            processed_pages={
                url: ScrapedPageInfo(**info_dict)
                for url, info_dict in json_data["processed_pages"].items()
            },
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "counter": self.counter,
                "page_queue": self.page_queue,
                "processed_pages": {
                    url: info._asdict() for url, info in self.processed_pages.items()
                },
            }
        )

    def get_next_filename(self) -> str:
        self.counter += 1
        return f"{self.counter}.html"

    def add_processed_url(self, url: str, info: ScrapedPageInfo) -> None:
        self.processed_pages[url] = info

    def add_urls_to_queue(self, urls: List[str]) -> None:
        for url in urls:
            if url not in self.processed_pages and url not in self.page_queue:
                self.page_queue.append(url)


class Scraper:
    def __init__(self, args):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(args.bucket_name)
        self.work_dir = args.work_dir
        self.start_link = args.start_link
        self.start_new = args.start_new
        self.chromedriver_path = args.chromedriver_path

    @property
    def state_path(self):
        return join(self.work_dir, "state.json")

    def _init_state(self) -> ScraperState:
        state_blob = self.bucket.blob(self.state_path)
        if self.start_new or not state_blob.exists():
            return ScraperState(0, [self.start_link], {})
        return ScraperState.from_json(state_blob.download_as_string().decode())

    def _save_state(self, state: ScraperState) -> None:
        state_blob = self.bucket.blob(self.state_path)
        state_blob.upload_from_string(state.to_json())

    def extract_urls(self, text, page_str):
        urls = []
        page_url = urlparse(page_str)
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup.findAll("a"):
            if "href" not in tag.attrs:
                continue
            link = tag["href"]
            logging.info(f"New link: {link}")
            link_url = urlparse(link)
            if link_url.scheme not in ["http", "https", ""]:
                logging.warning(f"Link to different site: {link_url.scheme} != {page_url.scheme}")
                continue
            if page_url.path and page_url.path[-1] == "/":
                new_path = join(page_url.path, link_url.path)
            else:
                new_path = link_url.path
            link_url = link_url._replace(
                scheme=link_url.scheme or page_url.scheme,
                netloc=link_url.netloc or page_url.netloc,
                path=normpath(new_path),
                query=urlencode(parse_qsl(link_url.query)),
            )
            if link_url.netloc != page_url.netloc:
                logging.warning(f"Link to different site: {link_url.netloc} != {page_url.netloc}")
                continue
            url = link_url.geturl()
            urls.append(url)
        return urls

    def _upload_blob(self, source_file, destination_file_name):
        blob = self.bucket.blob(
            join(self.work_dir, "html_data", destination_file_name)
        )

        blob.upload_from_string(source_file)

    def _cteate_robotparser(self):
        link_url = urlparse(self.start_link)
        robots_url = link_url._replace(
            path="robots.txt", params="", query="", fragment=""
        )
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url.geturl())
        rp.read()
        return rp

    def scrape(self):
        state = self._init_state()
        rp = self._cteate_robotparser()
        while state.page_queue:
            page = state.page_queue.pop()
            print("CURRENT_PAGE:", page)
            logging.info(f"CURRENT_PAGE: {page}")
            if not rp or not rp.can_fetch("*", page):
                logging.warning("Disallow robots.txt")
                continue
            try:
                response = requests.get(page, headers={'Accept': 'text/html'}, timeout=60)
            except Exception as e:
                logging.error(f"Site error:\n{e}")
                response = None
            time.sleep(1)

            file_name = None
            site_error = None
            urls = []

            if response and response.ok:
                content_type = response.headers.get("Content-Type")
                if content_type and not content_type.startswith("text/html"):
                    logging.warning(f"Wrong format: {content_type}")
                    site_error = f"Wrong format: {content_type}"
                elif not content_type:
                    logging.warning(f"Wrong format: no content type")
                    site_error = f"Wrong format: no content type"
                else:
                    file_name = state.get_next_filename()
                    options = webdriver.ChromeOptions()
                    options.add_argument("headless")
                    driver = webdriver.Chrome(self.chromedriver_path, options=options)
                    driver.get(page)
                    source = driver.page_source
                    driver.quit()
                    self._upload_blob(source, file_name)
                    urls = self.extract_urls(source, page)

            state.add_processed_url(
                page,
                ScrapedPageInfo(
                    file_name=file_name,
                    status_code=response.status_code if response else -1,
                    site_error=site_error,
                ),
            )
            print(f"htmls saved: {state.counter}")
            state.add_urls_to_queue(urls)
            self._save_state(state)


def main():
    args = parse_args()
    FORMAT = '%(asctime)-15s %(levelname)s: %(message)s'
    logging.basicConfig(filename=f'../scraper_{args.work_dir}.log', format=FORMAT, level=logging.INFO)
    scraper = Scraper(args)
    scraper.scrape()


if __name__ == "__main__":
    main()
