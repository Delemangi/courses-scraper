import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from app.constants import columns, fields, selectors


def get_profile_name(element: Tag) -> str:
    return element.select_one(selectors["name_selector"]).text


def get_profile_description(element: Tag) -> str:
    description = element.select_one(selectors["description_selector"])

    if description is None:
        return ""

    return description.text


def get_profile_description_images(element: Tag) -> str:
    images = element.select(selectors["description_images_selector"])
    return "\n".join([image["src"] for image in images])


def get_profile_details(element: Tag) -> dict[str, str]:
    attributes: dict[str, str] = {}
    details = element.select(selectors["details_selector"])

    for detail in details:
        text = detail.dt.text

        if text in fields:
            if text == "Interests":
                interests = detail.dd.select(selectors["interests_selector"])
                value = "\n".join(interest.text.strip() for interest in interests)
            elif text == "Email address":
                value = detail.dd.text.replace(
                    " (Visible to other course participants)", ""
                )
            else:
                value = detail.dd.text

            attributes[fields[text]] = value

    return attributes


def get_profile_courses(element: Tag) -> str:
    courses_tags = element.select(selectors["courses_selector"])
    courses = [li.text for li in courses_tags]

    return "\n".join(courses)


def get_profile_last_access(element: Tag) -> str:
    return element.select_one(selectors["last_access_selector"]).text.replace(
        "\xa0", ";"
    )


def get_profile_attributes(element: Tag) -> dict[str, str]:
    profile: dict[str, str] = {}
    sections = element.select(selectors["sections_selector"])

    if len(sections) == 0:
        return {}

    profile["Name"] = get_profile_name(element)
    profile["Description"] = get_profile_description(element)
    profile["Images"] = get_profile_description_images(element)

    for section in sections:
        attribute = section.select_one(selectors["attribute_selector"])

        if attribute.text == "User details":
            profile |= get_profile_details(section)
        elif attribute.text == "Course details":
            profile["Courses"] = get_profile_courses(section)
        elif attribute.text == "Login activity":
            profile["Last Access"] = get_profile_last_access(section)

    return profile


def get_profile(session: requests.Session, profile_id: int) -> dict[str, str]:
    profile_url = f"https://courses.finki.ukim.mk/user/profile.php?id={profile_id}&showallcourses=1"
    response = session.get(profile_url)

    if response.status_code != 200:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        profile = get_profile_attributes(soup)
    except Exception:
        return {}

    if profile:
        profile["ID"] = profile_id

    return profile


def get_profiles(
    session: requests.Session, profile_ids: range, threads: int
) -> list[dict[str, str]]:
    with ThreadPoolExecutor(max_workers=threads) as executor:
        profiles = list(
            tqdm(
                executor.map(lambda x: get_profile(session, x), profile_ids),
                total=len(profile_ids),
            )
        )

    return list(filter(len, profiles))


def reorder_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            df[column] = ""

    return df[columns]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Courses profiles")

    parser.add_argument("-c", type=str, required=True, help="Courses session cookie")
    parser.add_argument("-o", type=str, default="profiles.csv", help="Output file")
    parser.add_argument("-t", type=int, default="10", help="How many threads to use")

    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("-i", type=int, nargs="+", help="Profile IDs to scrape")
    id_group.add_argument("-m", type=int, help="Highest ID")

    return parser.parse_args()


def get_courses_session(cookie: str) -> requests.Session:
    retry_strategy = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=4,
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.cookies.set("MoodleSession", cookie)

    return session


def main() -> None:
    args = parse_args()
    session = get_courses_session(args.c)
    start = time.time()

    if args.i is not None:
        profiles = get_profiles(session, args.i, args.t)
    elif args.m is not None:
        profiles = get_profiles(session, range(1, args.m + 1), args.t)
    else:
        return

    os.makedirs("output", exist_ok=True)
    df = reorder_columns(pd.DataFrame(profiles), columns)
    df.to_csv("output/" + args.o, index=False)

    print(df.tail())
    print(f"Finished in {time.time() - start} seconds")


if __name__ == "__main__":
    main()
