import datetime
# from settings import TIMEZONE



def _get_timestamp() -> str:
    """Get now timestamp to insert into database"""
    # timestamp = datetime.datetime.now(TIMEZONE).timestamp()
    timestamp = datetime.datetime.now().timestamp()
    ts = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return ts



def _process_sitemap_field(sitemap:str):
    """Process sitemap field in 'site' table"""
    sitemap_list = []
    if ',' in sitemap:
        for s in sitemap.split(','):
            sitemap_list.append(s.strip())
    else:
        sitemap_list.append(sitemap)
    return sitemap_list



def _convert_sitemap_list_string(sitemap_list:list) -> str:
    """Convert sitemap list to comma separated string to be able to put into database"""
    return ','.join(sitemap_list).strip()


def _escape_field(string:str) -> str:
    """Escape special characters in the string before insert or update them into database"""
    if "'" in string:
        string = string.replace("'", "''")
    if '"' in string:
        string = string.replace('"', '""')
    return string



def _convert_persian_numbers(text:str) -> str:
    """Check received link for persian numbers and convert them to english numbers"""
    persian_to_english = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        # Add more mappings for other Persian characters if needed
    }
    converted_text = ''
    for char in text:
        if char in persian_to_english:
            converted_text += persian_to_english[char]
        else:
            converted_text += char
    return converted_text
