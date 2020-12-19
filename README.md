# Scraper

This repository contains scripts for scraping websites, extracting structured data and saving this data to nq format.

This project allows to scrape structured data from the whole website starting from a single page.

## Scraping component

[scripts/scraper.py](scripts/scraper.py) takes start page for a website, finds all pages and saves html data into Google Cloud Storage.

For example run this command from the root of this repository to scrape the data for https://disprot.org site into disprot directory in wikidata-collab-1-crawler GCS bucket.
```
python3 scripts/scraper.py https://disprot.org disprot --bucket_name wikidata-collab-1-crawler
```  

## Parsing component

[scripts/parser.py](scripts/parser.py) takes a directory with html files produced by the scraping component, extracts structured data from each page, converts to nquads format and saves the resulting data back to GCS bucket.

For example run this command from the root of this repository to parse the data scraped in the previous example.
```
python3 scripts/parser.py disprot --bucket_name wikidata-collab-1-crawler
```  
