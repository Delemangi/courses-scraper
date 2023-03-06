# Courses Scraper

Script for scraping all profiles from Courses.

## Installation

Python >= 3.9 is required.

`python -m pip install -r requirements.txt`

## Running

`python scraper.py <arguments>`

Arguments:

1. `-h` - shows help message
2. `-c` - set `MoodleSession` cookie content
3. `-o` - output file name
4. `-i` - profile IDs to be scraped
5. `-m` - upper limit of profile IDs to be scraped

The arguments `-c` and either one of `-i` or `-m` are required.
