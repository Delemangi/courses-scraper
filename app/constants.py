selectors = {
    "name_selector": "#page-header > div > div > div > div.d-flex.align-items-center > div.mr-auto > div > div.page-header-headings > h1",
    "description_selector": "#region-main > div > div > div.description",
    "description_images_selector": "#region-main > div > div > div.description img",
    "courses_selector": "ul > li > dl > dd > ul > li",
    "last_access_selector": "ul > li > dl > dd",
    "details_selector": "ul > li.contentnode",
    "sections_selector": "#region-main > div > div > div.profile_tree > section",
    "interests_selector": "li:not(.visibleifjs)",
    "attribute_selector": "h3.lead",
    "avatar_selector": ".page-header-image > img",
}

fields = {
    "Email address": "Mail",
    "Web page": "Web",
    "Interests": "Interests",
    "ICQ number": "ICQ",
    "Skype ID": "Skype",
    "Yahoo ID": "Yahoo",
    "AIM ID": "AIM",
    "MSN ID": "MSN",
    "Country": "Country",
    "City/town": "City",
    "MoodleNet profile": "MoodleNet",
    "Avatar": "Avatar",
}

columns = [
    "ID",
    "Name",
    "Mail",
    "Courses",
    "Last Access",
    "Avatar",
    "Description",
    "Images",
    "Country",
    "City",
    "Interests",
    "Web",
    "MoodleNet",
    "Skype",
    "MSN",
    "Yahoo",
    "ICQ",
    "AIM",
]

http_ok = 200
