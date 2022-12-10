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

profile_name_selector = '#page-header > div > div > div > div.d-flex.align-items-center > div.mr-auto > div > div.page-header-headings > h1'
profile_description_selector = '#region-main > div > div > div.description > p'
profile_courses_selector = 'ul > li > dl > dd > ul > li'
profile_last_access_selector = 'ul > li > dl > dd'
profile_details_selector = 'ul > li.contentnode'

attribute_names = {
    'Email address': 'Mail',
    'Web page': 'Web',
    'Interests': 'Interests',
    'ICQ number': 'ICQ',
    'Skype ID': 'Skype',
    'Yahoo ID': 'Yahoo',
    'AIM ID': 'Aim',
    'MSN ID': 'MSN',
    'Country': 'Country',
    'City/town': 'City'
}
df_column_order = ['ID', 'Name', 'Mail', 'Courses', 'Last Access', 'Description', 'Country', 'City', 'Interests', 'Web', 'Skype', 'MSN', 'Yahoo', 'ICQ', 'AIM']


def get_profile_name(element: Tag):
    return element.select_one(profile_name_selector).text


def get_profile_description(element: Tag):
    p_description = element.select_one(profile_description_selector)

    if p_description:
        return p_description.text

    return ''


def get_profile_details(element: Tag):
    attributes: dict[str, str] = {}
    details_elements = element.select(profile_details_selector)

    for e in details_elements:
        text = e.dt.text

        if text in attribute_names:
            attribute_name = attribute_names[text]

            if attribute_name == 'Interests':
                interests_li = e.dd.select('li:not(.visibleifjs)')
                value = '\n'.join(li.text.strip(' \n') for li in interests_li)
            else:
                value = e.dd.text

            attributes[attribute_name] = value

    return attributes


def get_profile_courses(element: Tag):
    courses_li_tags = element.select(profile_courses_selector)
    courses = [course_li.text for course_li in courses_li_tags]

    return '\n'.join(courses)


def get_profile_last_access(element: Tag):
    return element.select_one(profile_last_access_selector).text.replace('\xa0', ';')


def get_profile_attributes(element: Tag):
    profile: dict[str, str] = {}
    sections = element.select('#region-main > div > div > div.profile_tree > section')

    if len(sections) == 0:
        return {}

    profile['Name'] = get_profile_name(element)
    profile['Description'] = get_profile_description(element)

    for section in sections:
        lead = section.select_one('h3.lead')

        if lead.text == 'User details':
            profile |= get_profile_details(section)
        elif lead.text == 'Course details':
            profile['Courses'] = get_profile_courses(section)
        elif lead.text == 'Login activity':
            profile['Last Access'] = get_profile_last_access(section)

    return profile


def get_profile(session: requests.Session, profile_id: int):
    profile_url = f'https://courses.finki.ukim.mk/user/profile.php?id={profile_id}&showallcourses=1'
    response = session.get(profile_url)

    if response.status_code != 200:
        print(profile_id, response)
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')

    try:
        profile = get_profile_attributes(soup)
    except Exception as e:
        print(e)
        print(profile_id, response)
        raise e

    if profile:
        profile['ID'] = profile_id

    return profile


def get_profiles(session: requests.Session, profile_ids: list[int], threads: int):
    with ThreadPoolExecutor(max_workers=threads) as executor:
        profiles = list(tqdm(executor.map(lambda x: get_profile(session, x), profile_ids), total=len(profile_ids)))

    return list(filter(len, profiles))


def reorder_columns(df: pd.DataFrame, columns: list[str]):
    for column in columns:
        if column not in df.columns:
            df[column] = ''

    return df[columns]


def parse_args():
    parser = argparse.ArgumentParser(description='Scrape Courses profiles')

    parser.add_argument('-c', type=str, required=True, help='Courses session cookie')
    parser.add_argument('-o', type=str, default='profiles.csv', help='Output file')
    parser.add_argument('-t', type=int, default='10', help='How many threads to use')

    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument('-i', type=int, nargs='+', help='Profile IDs to scrape')
    id_group.add_argument('-m', type=int, help='Highest ID')

    return parser.parse_args()


def get_courses_session(cookie: str):
    retry_strategy = Retry(total=5, status_forcelist=[429, 500, 502, 503, 504], backoff_factor=4, allowed_methods=['HEAD', 'GET', 'OPTIONS'])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.cookies.set('MoodleSession', cookie)

    return session


def main():
    args = parse_args()
    session = get_courses_session(args.c)
    start = time.time()

    if args.i is not None:
        profiles = get_profiles(session, args.i, args.t)
    elif args.m is not None:
        profiles = get_profiles(session, range(1, args.m + 1), args.t)
    else:
        print('No IDs provided')
        return

    os.makedirs('data', exist_ok=True)
    df = reorder_columns(pd.DataFrame(profiles), df_column_order)
    df.to_csv('data/' + args.o, index=False)

    print(df)
    print(f'Finished in {time.time() - start} seconds')


if __name__ == '__main__':
    main()
