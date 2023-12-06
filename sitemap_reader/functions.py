import settings
from .url_parsers import _normalize_domain, _parse_url_title_product, _parse_url_title_sitemaps,\
    _create_product_url_pattern, _is_product_url, _second_layer_product_url_filter,\
    _parse_url_title_category
from drivers.selenium_driver import call_selenium_driver
from drivers.requests_setup import requests_init
from logs.exception_logs import exception_line
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidArgumentException, WebDriverException
import bs4
from bs4 import BeautifulSoup
import logging
import validators
from urllib.parse import urljoin, urlparse
from urllib.request import urlretrieve
import time
import gzip
import os
import ssl




def extract_robots_sitemaps(url:str, driver:object, api_agent:str='selenium', timeout:int=40) -> list|None:
    """Extract all links from any sitemap links in 'robots.txt'. If any error encountered or no sitemap links found return empty list"""
    try:
        links = []
        sitemap_link = ''
        if api_agent == 'selenium':
            site_url = f'http://{_normalize_domain(url)}'
            robot_url = f'{site_url}/robots.txt'
            driver.get(robot_url)
            # Scrap robots.txt file to extrace all sitemap links from it
            soup = bs4.BeautifulSoup(driver.page_source, features='lxml')
        elif api_agent == 'requests':
            site_url = f'https://{_normalize_domain(url)}'
            robot_url = f'{site_url}/robots.txt'
            # Scrap robots.txt file to extrace all sitemap links from it
            response = requests_init(url=robot_url)
            if not response:
                logging.error(f'An error in requests then cannot extract robots.txt for "{url}"')
                return None
            if response.status_code != 200:
                logging.error(f'status_code: {response.status_code} - cannot extract robots.txt for {url}')
                return None
            soup = bs4.BeautifulSoup(response.content, features='lxml')
        # If found a links started with 'Sitemap' or 'sitemap', append both links with '.xml' and without '.xml' to the links
        robots_rows = [rr.strip() for rr in soup.text.split('\n')]
        # for robots_row in soup.text.split('\n'):
        for robots_row in robots_rows:
            if robots_row.startswith('Sitemap'):
                sitemap_link = robots_row.split('Sitemap:')[1].strip()
                links.append(sitemap_link)
            if robots_row.startswith('sitemap'):
                sitemap_link = robots_row.split('sitemap:')[1].strip()
                links.append(sitemap_link)
            if robots_row.startswith('#Sitemap'):
                sitemap_link = robots_row.split('#Sitemap:')[1].strip()
                links.append(sitemap_link)
            if robots_row.startswith('#sitemap'):
                sitemap_link = robots_row.split('#sitemap:')[1].strip()
                if not sitemap_link.endswith('.xml'):
                    sitemap_link = sitemap_link.split('.xml')[0].strip() + '.xml'
                    links.append(sitemap_link)
                links.append(robots_row.split('Sitemap:')[1].strip())
            if robots_row.endswith('.xml'):
                links.append(sitemap_link)
            # Following 'if' clause is very generic and must be tested carefully
            if validators.url(robots_row):
                links.append(robots_row)
        if sitemap_link == '':
            return []
        return links
    except Exception as e:
        logging.error(f'Error in "sitemap_reader.functions.extract_robots_sitemaps": {e.__str__()}')
        logging.warn(exception_line())
        return None


def append_common_sitemaps(domain:str, sitemap_links, api_agent:str='selenium') -> list:
    """try to check and append common sitemap links to the sitemap_links list"""
    if validators.url(f'http://{domain}/sitemap.xml'):
        if f'http://{domain}/sitemap.xml' not in sitemap_links:
            sitemap_links.append(f'http://{domain}/sitemap.xml')
            if api_agent == 'requests':
                sitemap_links.append(f'https://{domain}/sitemap.xml')

    if validators.url(f'http://{domain}/sitemap_index.xml'):
        if f'http://{domain}/sitemap_index.xml' not in sitemap_links:
            sitemap_links.append(f'http://{domain}/sitemap_index.xml')
            if api_agent == 'requests':
                sitemap_links.append(f'https://{domain}/sitemap_index.xml')
                
    if validators.url(f'http://{domain}/site/sitemap_index.xml'):
        if f'http://{domain}/site/sitemap.xml' not in sitemap_links:
            sitemap_links.append(f'http://{domain}/site/sitemap.xml')
            if api_agent == 'requests':
                sitemap_links.append(f'https://{domain}/site/sitemap.xml')
            
    if validators.url(f'http://{domain}/site/sitemap_index.xml'):
        if f'http://{domain}/site/sitemap_index.xml' not in sitemap_links:
            sitemap_links.append(f'http://{domain}/site/sitemap_index.xml')
            if api_agent == 'requests':
                sitemap_links.append(f'https://{domain}/site/sitemap_index.xml')

    if validators.url(f'http://{domain}/sitemap'):
        if f'http://{domain}/sitemap' not in sitemap_links:
            sitemap_links.append(f'http://{domain}/sitemap')
            if api_agent == 'requests':
                sitemap_links.append(f'https://{domain}/sitemap')
            
    return sitemap_links



def extract_links(sitemap_url:str, sitemap_links:list=[], readed_sitemaps:set=set(), end_set:set=set(), category_set:set=set(), removed_sitemaps_set:set=set(), product_url_pattern:str|None=None, product_url_pattern_scheme:str|None=None, driver:object=None, root_sitemap_field:str=None, api_agent:str='selenium', timeout:int=25) -> tuple:
    """Extract all links from any sitemap xml related link. returns a 4-element tuple:
    first element is the list of extracted sitemap links
    second element is the set of endlinks
    third element is the root_sitemap_field
    fourth element is the set of category links"""
    try:
        if api_agent == 'selenium':
            if not driver:
                driver = call_selenium_driver(site_url=sitemap_url, timeout=timeout, is_url_sitemap=True)
                if not driver:
                    raise Exception('Error in setup the selenium')
            try:
                driver.get(sitemap_url)
            except InvalidArgumentException:
                if 'CDATA' in sitemap_url:
                    sitemap_url = sitemap_url[9:-3]
                    print('cleaned_sitemap:        ', sitemap_url.strip())
                    driver.get(sitemap_url.strip())
                else:
                    return sitemap_links, end_set, root_sitemap_field, category_set
            except WebDriverException:
                return sitemap_links, end_set, root_sitemap_field, category_set
            soup = bs4.BeautifulSoup(driver.page_source, features='lxml')
        elif api_agent == 'requests':
            if 'CDATA' in sitemap_url:
                sitemap_url = sitemap_url[9:-3].strip()
                print('cleaned sitemap_url:  ', sitemap_url)
            response = requests_init(url=sitemap_url, is_url_sitemap=True)
            if not response:
                logging.error(f'Cannot open "{sitemap_url}"')
                return sitemap_links, end_set, root_sitemap_field, category_set
            if response.status_code != 200:
                logging.error(f'status_code: {response.status_code} - cannot extract links for {sitemap_url}')
                return sitemap_links, end_set, root_sitemap_field, category_set
            soup = bs4.BeautifulSoup(response.content, features='lxml')
        link_tags = []
        # website_link and website_domain
        website_domain = _normalize_domain(sitemap_url)
        website_link = f'{urlparse(sitemap_url).scheme}://{website_domain}'
        # Find all links in the current sitemap
        link_tags.extend(soup.find_all('loc'))
        link_tags.extend(soup.find_all('a', href=True))
        # ! Minority of websites like digimomarket.com has it's sitemap links very weird like this: "https://digimomarket.com/sitemap" so we have to add some functionality to it
        td_tags = soup.find_all('td')
        if td_tags:
            for td_tag in td_tags:
                if website_domain in td_tag.get_text():
                    link_tags.append(td_tag)
        # ! Minority of websites, have their sitemap in .txt files like http://alldigitall.ir and they need their own functionality
        if sitemap_url.endswith('.txt'):
            sitemap_rows = [rr.strip() for rr in soup.text.split('\n')]
            for sr in sitemap_rows:
                if sr.startswith('http'):
                    new_div = soup.new_tag('div')
                    new_div.string = sr
                    link_tags.append(new_div)
        if link_tags:
            # 'i' is a counter to know where to place founded 'sitemap' link in the list of sitemaps to extract respectively
            i = 0
            for link_tag in link_tags:
                # If current link is a sitemap link insert it the 'sitemap_links' list else it's a endlink and we must append it to the 'end_links' list
                # Any new sitemap found, must be inserted into start of the 'sitemap_links'
                # ! If global variable 'root_sitemap_field' is empty, set it's value as first sitemap link processed
                if root_sitemap_field is None:
                    root_sitemap_field = sitemap_url
                try:
                    founded_link = link_tag['href']
                except KeyError:
                    founded_link = link_tag.get_text()
                # print('founded link: ', founded_link)
                # Check if founded_link is internal link. If it's and external link, ignore it
                # ! Some urls has 'www' in them. Remember this...
                # if urlparse(founded_link).netloc != urlparse(sitemap_url).netloc:
                if not website_domain in founded_link:
                    # print('external link in founded link: ', founded_link)
                    continue
                # If 'CDATA' is in the 'founded_link' parse the link:
                if 'CDATA' in founded_link:
                    founded_link = founded_link[founded_link.find('h'):-3].strip()
                # Extract '.gz' files if encountered
                if founded_link.endswith('.gz'):
                    if founded_link in readed_sitemaps:
                        continue
                    sitemap_links , end_set = extract_gz_links(gz_url=founded_link,
                                                                sitemap_links=sitemap_links,
                                                                readed_sitemaps=readed_sitemaps,
                                                                removed_sitemaps_set=removed_sitemaps_set,
                                                                end_set=end_set,
                                                                product_url_pattern=product_url_pattern,
                                                                product_url_pattern_scheme=product_url_pattern_scheme)
                # ! If 'localhost' is in the lilnk instead of the website domain name, replace 'localhost' with domain_name
                if 'localhost' in founded_link:
                    founded_link = founded_link.replace('localhost', website_domain)
                # print('founded link: ', founded_link)
                # If founded_link is a sitemap add it to sitemap_list else check if it's a product link and add to to link list
                # if founded_link.endswith('.xml') or founded_link.endswith('.gz') or 'page' in founded_link or 'sitemap' in founded_link or 'Sitemap' in founded_link:
                # if founded_link.endswith('.xml') or 'page' in founded_link or 'sitemap' in founded_link or 'Sitemap' in founded_link:
                if founded_link.endswith('.xml') or 'sitemap' in founded_link or 'Sitemap' in founded_link or 'site' in founded_link or 'sites' in founded_link:
                    # Check if current sitemap is already crawled
                    if founded_link in removed_sitemaps_set or founded_link == website_link:
                        continue
                    # We should parse and check founded link to know if the link belongs to 'products' or not. Only append current link to sitemap list if the link is not already in the 'readed_sitemaps' set
                    if _parse_url_title_sitemaps(founded_link):
                        if not founded_link in readed_sitemaps:
                            sitemap_links.insert(i, founded_link)
                # If the link is not sitemap, check if it's a product link
                else:
                    # Check if founded link belongs to 'category'
                    if _parse_url_title_category(founded_link) and (settings.SITEMAP_SEARCH_CATEGORY_PRODUCTS_ANYWAY or settings.SITEMAP_SEARCH_CATEGORY_ONLY_WITHOUT_PRODUCT):
                        category_set.add(founded_link)
                    # The priority is '_is_product_url'. But if it's not, check '_parst_url_title_product'
                    if _is_product_url(founded_link, product_url_pattern, product_url_pattern_scheme):
                        if _second_layer_product_url_filter(founded_link):
                            end_set.add(founded_link)
                    elif _parse_url_title_product(founded_link):
                        end_set.add(founded_link)
        else:
            logging.warning(f'{sitemap_url} is empty of links!')
    except Exception as e:
        logging.error(f'Error in "sitemap_reader.functions.extract_links": {e.__str__()}')
        logging.warning(exception_line())
    return (sitemap_links, end_set, root_sitemap_field, category_set)



def extract_gz_links(gz_url:str, sitemap_links:list, readed_sitemaps:set, removed_sitemaps_set:set, end_set:set, product_url_pattern:str, product_url_pattern_scheme:str) -> tuple:
    """Extract gz files and try to extract 'sitemap' links or 'product' links. Returns 2-element tuple:
    first element: list of sitemap links
    second elemenet: set of end links"""
    try:
        # Disable SSL certificate verification for urllib (Below line is enough maybe by itself only, but to be more certain we add the 'ctx' or context the the urllib object)
        ssl._create_default_https_context = ssl._create_unverified_context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        # Download gz file in the current directory
        file_name = urlparse(gz_url).path.replace('/', '-')
        urlretrieve(gz_url, file_name)
        # Read content of the downloaded file
        gz_file_data = None
        with gzip.open(file_name, 'rb') as f:
            gz_file_data = f.read()
        # Check if there are content in the gz_url, Analyze the content of the page
        if gz_file_data:
            link_tags = []
            soup = bs4.BeautifulSoup(gz_file_data, features='lxml')
            # website_link and website_domain
            website_domain = _normalize_domain(gz_url)
            website_link = f'{urlparse(gz_url).scheme}://{website_domain}'
            # Find all links in the current sitemap
            link_tags.extend(soup.find_all('loc'))
            link_tags.extend(soup.find_all('a', href=True))
            # ! Minority of websites like digimomarket.com has it's sitemap links very weird like this: "https://digimomarket.com/sitemap" so we have to add some functionality to it
            td_tags = soup.find_all('td')
            if td_tags:
                for td_tag in td_tags:
                    if website_domain in td_tag.get_text():
                        link_tags.append(td_tag)
            if link_tags:
                # 'i' is a counter to know where to place founded 'sitemap' link in the list of sitemaps to extract respectively
                i = 0
                for link_tag in link_tags:
                    # If current link is a sitemap link insert it the 'sitemap_links' list else it's a endlink and we must append it to the 'end_links' list
                    # Any new sitemap found, must be inserted into start of the 'sitemap_links'
                    try:
                        founded_link = link_tag['href']
                    except KeyError:
                        founded_link = link_tag.get_text()
                    # Check if founded_link is internal link. If it's and external link, ignore it
                    # ! Some urls has 'www' in them. Remember this...
                    # if urlparse(founded_link).netloc != urlparse(sitemap_url).netloc:
                    if not website_domain in founded_link:
                        # print('external link in founded link: ', founded_link)
                        continue
                    # If 'CDATA' is in the 'founded_link' parse the link:
                    if 'CDATA' in founded_link:
                        founded_link = founded_link[founded_link.find('h'):-3].strip()
                    # Check if link is a sitemap link, append it to the 'sitemap_links' list
                    # ! NOTE: some sites don't end up with .xml but maybe there is 'page' in the sitemap. Consider them as sitemap link for now
                    if founded_link.endswith('.gz'):
                        sitemap_links , end_set = extract_gz_links(gz_url=founded_link,
                                                                    sitemap_links=sitemap_links,
                                                                    readed_sitemaps=readed_sitemaps,
                                                                    removed_sitemaps_set=removed_sitemaps_set,
                                                                    end_set=end_set,
                                                                    product_url_pattern=product_url_pattern,
                                                                    product_url_pattern_scheme=product_url_pattern_scheme)
                    # ! If 'localhost' is in the lilnk instead of the website domain name, replace 'localhost' with domain_name
                    if 'localhost' in founded_link:
                        founded_link = founded_link.replace('localhost', website_domain)
                    # print('founded link: ', founded_link)
                    # if founded_link.endswith('.xml') or founded_link.endswith('.gz') or 'page' in founded_link or 'sitemap' in founded_link or 'Sitemap' in founded_link:
                    # if founded_link.endswith('.xml') or 'page' in founded_link or 'sitemap' in founded_link or 'Sitemap' in founded_link:
                    if founded_link.endswith('.xml') or 'sitemap' in founded_link or 'Sitemap' in founded_link or 'site' in founded_link or 'sites' in founded_link:
                        # Check if current sitemap is already crawled
                        if founded_link in removed_sitemaps_set or founded_link == website_link:
                            continue
                        # We should parse and check founded link to know if the link belongs to 'products' or not. Only append current link to sitemap list if the link is not already in the 'readed_sitemaps' set
                        # if _parse_url_title(link['href']):
                        if _parse_url_title_sitemaps(founded_link):
                            if not founded_link in readed_sitemaps:
                                sitemap_links.insert(i, founded_link)
                    # If the link is not sitemap, check if it's a product link
                    else:
                        # The priority is '_is_product_url'. But if it's not, check '_parst_url_title_product'
                        if _is_product_url(founded_link, product_url_pattern, product_url_pattern_scheme):
                            if _second_layer_product_url_filter(founded_link):
                                end_set.add(founded_link)
                        elif _parse_url_title_product(founded_link):
                            end_set.add(founded_link)
                        # end_set.append({url: founded_link})
                # ! Right now we don't need following block (It adds the supposly product_sitemap to the list of product_sitemaps)
                # If 'i == 0', then it means current 'url' is an end-sitemap link without any sitemap link in it
                # if not i:
                #     if parse_url_title(url):
                #         product_sitemaps.append(url)
            else:
                logging.info(f'{gz_url} is empty of links!')
        else:
            logging.warning(f'{gz_url} is empty of data')
    except Exception as e:
        logging.error(f'Error in "sitemap_reader.functions.extract_gz_links": {e.__str__()}')
        logging.warning(exception_line())
    try:
        os.remove(file_name)
    except FileNotFoundError:
        pass
    return (sitemap_links, end_set)



def extract_category_links(category_set:set, end_set:set, product_url_pattern:str, product_url_pattern_scheme:str, api_agent:str='selenium', driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> set:
    """Extract product links from category_set. Returns set of product link"""
    try:
        print(f'POTENTIAL PRODUCT CATEGORY LINK: {len(category_set)}')
        is_internal_driver = False
        if api_agent == 'selenium':
            error_counter = 0
            # For now call driver headless everytime
            if not driver:
                driver = call_selenium_driver(timeout=timeout, implicit_wait=4)
                is_internal_driver = True
                if not driver:
                    raise Exception(f'Driver did not created')
        for category_link in category_set:
            website_domain = _normalize_domain(category_link)
            website_link = f'{urlparse(category_link).scheme}://{website_domain}'
            # Check api_agent
            if api_agent == 'selenium':
                try:
                    driver.get(category_link)
                    time.sleep(3)
                except WebDriverException:
                    error_counter += 1
                    if error_counter < 10:
                        continue
                    else:
                        raise Exception('WebDriver Exception: Cannot open url')
                # Assume page is an xml page
                soup = bs4.BeautifulSoup(driver.page_source, features='html.parser')
            elif api_agent == 'requests':
                response = requests_init(url=category_link)
                if not response:
                    logging.error(f'Cannot open "{category_link}"')
                    continue
                    # return end_set
                if response.status_code != 200:
                    logging.error(f'status_code: {response.status_code} - cannot extract links for {category_link}')
                    continue
                    # return end_set
                # Assume page is an xml page
                soup = bs4.BeautifulSoup(response.content, features='html.parser')
            link_tags = []
            # Find all links in the current sitemap
            link_tags.extend(soup.find_all('loc'))
            link_tags.extend(soup.find_all('a', href=True))
            if not link_tags:
                # Assume page should be read with parser.html
                if api_agent == 'selenium':
                    soup = bs4.BeautifulSoup(driver.page_source, features='lxml')
                elif api_agent == 'requests':
                    soup = bs4.BeautifulSoup(response.content, features='lxml')
                link_tags.extend(soup.find_all('loc'))
                link_tags.extend(soup.find_all('a', href=True))
            if link_tags:
                for link_tag in link_tags:
                    try:
                        founded_link = link_tag['href']
                    except KeyError:
                        founded_link = link_tag.get_text()
                    if \
                    (founded_link and not founded_link.startswith('#') and not founded_link.endswith('.jpg') and not founded_link.endswith('png') and not founded_link.endswith('.webp') and\
                    not '/#' in founded_link and not 'search' in founded_link and not 'post' in founded_link and not 'about-us' in founded_link and\
                    not 'linkedin' in founded_link and not 'instagram' in founded_link and not 'twitter' in founded_link and not 'telegram' in founded_link or 't.me' in founded_link\
                    and not founded_link.startswith('http'))\
                    or\
                    (founded_link.startswith('http') and _normalize_domain(founded_link) in website_domain):
                        # Join the relative URL with the base URL to get the absolute URL
                        if not founded_link.startswith('http'):
                            founded_link = urljoin(website_link, founded_link)
                            # print('founded_link: ', founded_link)
                            # Check if founded_link is a product_link
                            if _is_product_url(founded_link, product_url_pattern, product_url_pattern_scheme):
                                if _second_layer_product_url_filter(founded_link):
                                    # print('founded_product: ', founded_link)
                                    end_set.add(founded_link)
                            elif _parse_url_title_product(founded_link):
                                # print('founded_product: ', founded_link)
                                end_set.add(founded_link)
                    else:
                        continue
            else:
                logging.warning(f'{category_link} is empty of links!')
    except Exception as e:
        print('Len product_set: ', len(end_set))
        logging.error(f'Error in "sitemap_reader.functions.extract_category_links": {e.__str__()}')
        logging.warning(exception_line())
    try:
        if is_internal_driver:
            driver.close()
    except Exception:
        pass
    return end_set





def look_for_all_links(url:str, seed_domain:str, use_requests:bool=settings.USE_REQUESTS_FIND_ALL_LINKS, driver:object=None, product_url_pattern:str=None, product_url_pattern_scheme:str=None, product_found:set=set(), timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> set:
    """Look for all links in the url and try to find all product links in the website. Return set"""
    print(f'NOW EXTRACTING ALL URLS FROM \'{url}\' WITH PATTERN \'{product_url_pattern}\'...')
    try:
        # Use 'selenium' to extract all links
        is_internal_driver = False
        if not use_requests:
            if not driver:
                driver = call_selenium_driver(site_url=url, timeout=timeout, implicit_wait=settings.GENERAL_IMPLICIT_WAIT, disable_css=False)
                is_internal_driver = True
                if not driver:
                    raise Exception('Driver did not created')
            # Wait 2 seconds to fully initialize the selenium driver
            time.sleep(2)
            # ! Some website does not neccessary load the webpage user want but redirect user to the index page. This is a problem with catastophic result and needed to be addressed
            if not driver.find_elements(By.TAG_NAME, 'main'):
                logging.info('wait more to extract all links better...')
                time.sleep(4)
                driver.get(url)
                is_internal_driver = True
                # Check again if website redirected the bot to the main page of the website we want. If that not happened stop proceeds with current function
                if not driver.find_elements(By.TAG_NAME, 'main'):
                    logging.warning(f'Website did not redirect the bot to the main page of the \'{seed_domain}\' so use \'requests\' to extract links')
                    use_requests = True
        # Or use 'requests' to extract all links
        if use_requests:
            if not url.startswith('https'):
                url = url.replace('http', 'https')
            try:
                requests_errors = 0
                response = requests_init(url=url)
                if not response:
                    logging.error(f'Cannot open "{url}"')
                    requests_errors += 1
                if response.status_code != 200:
                    logging.error(f'status_code: {response.status_code} - cannot extract links for {url}')
                    requests_errors += 1
                # 'requests' is sensitive to 'www'
                if requests_errors >= 0:
                    url = f'{urlparse(url).scheme}://www.{urlparse(url).netloc}'
                    response = requests_init(url=url)
                    if not response:
                        logging.error(f'Cannot open "{url}"')
                        return product_found
                    if response.status_code != 200:
                        logging.error(f'status_code: {response.status_code} - cannot extract links for {url}')
                        return product_found
            # Sometimes HTTPSCONNECTION error happens
            except Exception:
                url = f'{urlparse(url).scheme}://www.{urlparse(url).netloc}'
                response = requests_init(url=url)
                if not response:
                    logging.error(f'Cannot open "{url}"')
                    return product_found
                if response.status_code != 200:
                    logging.error(f'status_code: {response.status_code} - cannot extract links for {url}')
                    return product_found
        # 'urls_to_be_extracted' link and 'visited_pages' set are used to extract links correctly without reading a link twice and make sure to read all links in the website
        urls_to_be_extracted = [url]
        visited_pages = set()
        # ? This loop used for iteration of reading all links of a website
        while True:
            try:
                current_url = urls_to_be_extracted[0]
            # If no link remains to be extracted data from, break the loop and end reading of the links
            except IndexError:
                break
            # Remove current url from the 'urls_to_be_extracted'
            urls_to_be_extracted.remove(current_url)
            # If current url is already in the 'visited_page' jump to the next page
            if current_url in visited_pages:
                continue
            # For unicoded urls like persian or arabic languages, a url may contains lower case while in other page same url may contains upper case. To not insert the same url into 'visited_page' we also insert lower cased url
            visited_pages.add(current_url)
            visited_pages.add(current_url.lower())
            # Get page data (selenium)
            if not use_requests:
                try:
                    driver.get(current_url)
                    if not driver.find_elements(By.TAG_NAME, 'main'):
                        time.sleep(3)
                except WebDriverException:
                    logging.warning(f'Error in reading {current_url}')
                    continue
                    # return product_found
                page_data = driver.page_source
            # Get page data (request)
            if use_requests:
                response = requests_init(url=current_url)
                if not response:
                    logging.error(f'Cannot open "{current_url}"')
                    continue
                if response.status_code != 200:
                    logging.error(f'status_code: {response.status_code} - cannot extract links for {current_url}')
                    continue
                page_data = response.content
            # Try to extract data from page_data
            if page_data:
                # Parse the HTML content of the page using BeautifulSoup (If BS cannot get the links, try extract links using chrome webdriver)
                _parser_is_bs = True
                soup = BeautifulSoup(page_data, 'html.parser')
                links_in_page = soup.find_all('a')
                if not links_in_page:
                    _parser_is_bs = False
                    # If 'page_data' created by selenium, use selenium driver to find all links in the page
                    if not use_requests:
                        links_in_page = driver.find_elements(By.TAG_NAME, 'a')
                if not links_in_page:
                    logging.warning(f'\'{url}\' does not have any link inside it or has a problem with getting them')
                    continue
                # Extract and print the href attribute (link) from each anchor tag
                for link in links_in_page:
                    try:
                        href = None
                        if _parser_is_bs:
                            href = link.get('href')
                        # If href not found with beautiful soup and page data extracted by selenium try to extract href attribute value using driver selenium
                        elif not href and not use_requests:
                            href = link.get_attribute('href')
                        if not href:
                            continue
                    except Exception:
                        continue
                    # Below is a long list of filters we set on 'href' to get the code more faster and produce less garbage while does not pass legitimate urls
                    if \
                    href and not href.startswith('#') and not href.endswith('.jpg') and not href.endswith('.png') and not href.endswith('.webp') and\
                    not 'search' in href and not 'post' in href and not 'about-us' in href and not 'blog' in href and not 'cart' in href and not 'auth' in href and\
                    not 'linkedin' in href and not 'instagram' in href and not 'twitter' in href and not 'telegram' in href or 't.me' in href\
                    :   # Exclude jump links
                        # If '#' is in the href, delete every characters after '#'
                        if '#' in href:
                            href = href[: href.find('#')]
                        # If '?' is in the href, delete every characters after '?'
                        if '?' in href:
                            href = href[: href.find('?')]
                        # If founded url is a relative url, join the relative URL with the base URL to get the absolute URL
                        if not seed_domain in href:
                            absolute_url = urljoin(current_url, href)
                        else:
                            absolute_url = href
                        # Add current absolute_url to the 'urls_to_be_extracted' list
                        # Check if the link is an internal link (same domain as the seed URL)
                        if seed_domain.replace('www.', '') in absolute_url:
                            # If absolute_url and its lower sample is not already in the 'visited_pages' and 'urls_to_be_extracted', insert it into the list
                            if absolute_url not in visited_pages and absolute_url.lower() not in visited_pages and absolute_url not in urls_to_be_extracted:
                                urls_to_be_extracted.insert(0, absolute_url)
                            if absolute_url not in product_found and absolute_url.lower() not in product_found:
                                # Pass link through the product_link_pattern_filter
                                if product_url_pattern:
                                    if _is_product_url(absolute_url, product_url_pattern):
                                        # if _second_layer_product_url_filter(absolute_url):
                                        print('AP(pa): ', absolute_url)
                                        product_found.add(absolute_url)
                                else:
                                    # if _parse_url_title_product(absolute_url):
                                    print('AP: ', absolute_url)
                                    product_found.add(absolute_url)
            else:
                logging.warning(f"Failed to fetch {current_url}")
            # If no url remains to be extracted, end the loop
            if not urls_to_be_extracted:
                break
        if is_internal_driver:
            try:
                driver.close()
            except Exception:
                pass
    except Exception as e:
        logging.error(f'Error in "sitemap_reader.functions.look_for_all_links": {e.__str__()}')
        logging.warning(exception_line())
        if is_internal_driver:
            try:
                driver.close()
            except Exception:
                pass
    return product_found
