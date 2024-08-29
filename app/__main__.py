import argparse
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

from app.constants import columns, fields, http_ok, selectors


def get_profile_name(element: Tag) -> str:
    name = element.select_one(selectors["name_selector"])

    if name is None:
        return ""

    return name.text


def get_profile_avatar(element: Tag) -> str:
    avatar = element.select_one(selectors["avatar_selector"])

    if avatar is None or "defaultuserpic" in avatar.attrs["class"]:
        return ""

    return avatar.attrs["src"]


def get_profile_description(element: Tag) -> str:
    description = element.select_one(selectors["description_selector"])

    if description is None:
        return ""

    return description.text


def get_profile_description_images(element: Tag) -> str:
    images = element.select(selectors["description_images_selector"])

    return "\n".join([image.attrs["src"] for image in images])


def get_profile_details(element: Tag) -> dict[str, str]:
    attributes: dict[str, str] = {}
    details = element.select(selectors["details_selector"])

    for detail in details:
        field_element = detail.dt
        value_element = detail.dd

        if field_element is None or value_element is None:
            continue

        field = field_element.text.strip().lower()

        if field in fields:
            value = value_element.text.strip()

            if field == "interests":
                interests = value_element.select(selectors["interests_selector"])
                value = "\n".join(interest.text.strip() for interest in interests)
            elif field == "email address":
                value = value.replace(" (Visible to other course participants)", "")

            attributes[fields[field]] = value

    return attributes


def get_profile_courses(element: Tag) -> str:
    courses_tags = element.select(selectors["courses_selector"])
    courses = [li.text for li in courses_tags]

    return "\n".join(courses)


def get_profile_last_access(element: Tag) -> str:
    last_access = element.select_one(selectors["last_access_selector"])

    if last_access is None:
        return ""

    return last_access.text.replace("\xa0", ";")


def get_profile_attributes(element: Tag) -> dict[str, str]:
    profile: dict[str, str] = {}
    sections = element.select(selectors["sections_selector"])

    if len(sections) == 0:
        return {}

    profile["Name"] = get_profile_name(element)
    profile["Description"] = get_profile_description(element)
    profile["Images"] = get_profile_description_images(element)
    profile["Avatar"] = get_profile_avatar(element)

    for section in sections:
        attribute = section.select_one(selectors["attribute_selector"])

        if attribute is None:
            continue

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

    if response.status_code != http_ok:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        profile = get_profile_attributes(soup)
    except Exception:
        return {}

    if profile:
        profile["ID"] = str(profile_id)

    return profile


def get_lambda(session: requests.Session) -> Callable[[int], dict[str, str]]:
    return lambda x: get_profile(session, x)


def get_profiles(
    session: requests.Session, profile_ids: range, threads: int
) -> list[dict[str, str]]:
    with ThreadPoolExecutor(max_workers=threads) as executor:
        profiles = list(
            tqdm(
                executor.map(get_lambda(session), profile_ids),
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

    output_path = Path("output")

    output_path.mkdir(exist_ok=True, parents=True)
    df = reorder_columns(pd.DataFrame(profiles), columns)
    df.to_csv(output_path / args.o, index=False)

    print(df.tail())
    print(f"Finished in {time.time() - start} seconds")


if __name__ == "__main__":
    main()
