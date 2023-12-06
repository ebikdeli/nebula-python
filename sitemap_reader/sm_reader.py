import settings
import validators
import logging
from .functions import extract_robots_sitemaps, extract_links,\
    append_common_sitemaps, look_for_all_links, extract_category_links
from .url_parsers import _normalize_domain, _create_product_url_pattern, _parse_url_title_sitemaps
from logs.exception_logs import exception_line
from drivers.selenium_driver import call_selenium_driver
from urllib.parse import urlparse




def auto_sitemap_reader(url:str, api_agent:str='selenium', example_links:str=None, driver:object=None, timeout:int=40) -> list|str:
    """Main function to read sitemap of a site_url. returns a list. If any error return str contains error
    NOTE: 'api_agent' tell us to use 'selenium' or 'requests' library
    first element is the list of 'product_links' for the received url
    second element is a string to fill the sitemap field in the sites table"""
    try:
        is_internal_driver = False
        if api_agent == 'selenium':
            if not driver:
                driver = call_selenium_driver(site_url=url, timeout=timeout, implicit_wait=settings.GENERAL_IMPLICIT_WAIT)
                is_internal_driver = True
                if not driver:
                    logging.warning('Driver did not created')
                    return 'Selenium Driver did not created'
        # Search for product_sitemap_links from site_urls
        sitemap_links = []
        endpoint_set = set()
        root_sitemap_field = None
        removed_sitemaps_set = set()
        # readed_sitemaps hold any sitemap read by the bot
        readed_sitemaps = set()
        category_set = set()
        # check and complted url if needed
        url = url.strip()
        if api_agent == 'selenium':
            if not url.startswith('http'):
                url = 'http://' + url
        elif api_agent == 'requests':
            if not url.startswith('http'):
                url = 'https://' + url
        # normalize domain name
        domain = _normalize_domain(url)
        # Check if 'robots.txt' exists extract all sitemap links from the file
        if validators.url(url):
            sitemap_links = extract_robots_sitemaps(url, driver, api_agent)
        # Check if other common sitemap patterns are in the sitemap_links
        sitemap_links = append_common_sitemaps(domain, sitemap_links, api_agent)
        if not sitemap_links:
            logging.info(f'No sitemap found for this url: {url}')
            return 'No sitemap found for this url: {url}'
        # ! Get the root sitemap and return it to fill the 'sitemap' field in 'sitemap' table
        _smf_list = []
        for sitemap_link in sitemap_links:
            # Any link in the 'sitemap_links' must be internal link to the website we want to crawl
            if domain not in sitemap_link:
                print(f'this sitemap link ({_normalize_domain(sitemap_link)}) is not belongs to the ', domain)
                sitemap_links.remove(sitemap_link)
                continue
            if _parse_url_title_sitemaps(sitemap_link):
                _smf_list.append(sitemap_link)
        if not _smf_list:
            logging.warning('No sitemap found in the url after FILTER!')
            return 'No sitemap found in the url after FILTER!'
        # Use filtered sitemap_links for the rest of operation
        sitemap_links = _smf_list
        # ! From this line, iterating through sitemaps and links starts
        logging.info(f'NOW PROCESSING: "{url}"')
        logging.info("PLEASE WAIT, LINK PROCESSING MAY TAKES A LONG TIME!!!....")
        # Create pattern for product links
        if example_links:
            product_url_pattern = _create_product_url_pattern(example_links=example_links)
            if product_url_pattern:
                logging.info(f'product url pattern for this website is: "{product_url_pattern}"')
                product_url_pattern_scheme = urlparse(product_url_pattern).scheme
            else:
                product_url_pattern = None
                product_url_pattern_scheme = None
        else:
            logging.warning('no \'example_links\' provided for current site')
            product_url_pattern = None
            product_url_pattern_scheme = None
        # Begin crawling sitemap
        while True:
            if not sitemap_links:
                break
            current_sitemap = sitemap_links[0]
            print('Now Processing: ', current_sitemap)
            readed_sitemaps.add(current_sitemap)
            sitemap_links.remove(current_sitemap)
            removed_sitemaps_set.add(current_sitemap)
            # ! Some websites has 'localhost' instead of domain name in the sitemap
            if 'localhost' in current_sitemap:
                current_sitemap = current_sitemap.replace('localhost', domain)
                print('localhost in the sitemap. instead do: ', current_sitemap)
            sitemap_links, endpoint_set, root_sitemap_field, category_set = extract_links(sitemap_url=current_sitemap,
                                                                                            sitemap_links=sitemap_links,
                                                                                            readed_sitemaps= readed_sitemaps,
                                                                                            end_set=endpoint_set,
                                                                                            category_set=category_set,
                                                                                            removed_sitemaps_set=removed_sitemaps_set,
                                                                                            product_url_pattern=product_url_pattern,
                                                                                            product_url_pattern_scheme=product_url_pattern_scheme,
                                                                                            root_sitemap_field=root_sitemap_field,
                                                                                            api_agent=api_agent,
                                                                                            driver=driver)
            # If there is no sitemap in the 'sitemap_links' it means there is no sitemap in the site anymore
        # print('founded product links: ', endpoint_set)
        # If category_set is not empty, try to extract product links from category_set
        if domain not in settings.SITES_NOT_READ_CATEGORY_LIST:
            if (category_set and settings.SITEMAP_SEARCH_CATEGORY_PRODUCTS_ANYWAY) or\
            (category_set and not endpoint_set and settings.SITEMAP_SEARCH_CATEGORY_ONLY_WITHOUT_PRODUCT):
                endpoint_set = extract_category_links(category_set=category_set,
                                                        end_set=endpoint_set,
                                                        product_url_pattern=product_url_pattern,
                                                        product_url_pattern_scheme=product_url_pattern_scheme,
                                                        api_agent=api_agent,
                                                        driver=driver)
        if endpoint_set and not root_sitemap_field:
            logging.warning(f'all product links extracted from category links for {domain}')
            root_sitemap_field = ''
        if not endpoint_set and root_sitemap_field:
            logging.warning(f'sitemaps extracted but no product link founded. Ignore {domain} for now')
        if not endpoint_set and not root_sitemap_field:
            root_sitemap_field = None
            logging.warning(f'no sitemap exists or no product link founded or sitemap is very heavy to load. Ignore {domain} for now')
        # If no product found in the sitemaps, check for another way to find the sites
        # print('products found in sitemaps: ', endpoint_set)
        # ! Ignore extracting all links for the site for now
        # if not endpoint_set:
        #     # seed_domain = urlparse(url).netloc
        #     seed_domain = domain
        #     endpoint_set = look_for_all_links(url=url,
        #                                       seed_domain=seed_domain,
        #                                       driver=driver,
        #                                       product_url_pattern=product_url_pattern)
        if endpoint_set:
            logging.info('SUCCESFULLY EXTRACTED PRODUCTS FROM SITEMAP LINKS OR OTHER DOMAIN URLS')
        else:
            logging.warning('EXTRACTING PRODUCTS FROM SITEMAP LINKS FINISHED BUT NO PRODUCT FOUND IN SITEMAP LINKS AND URLS')
        if is_internal_driver:
            try:
                driver.close()
            except Exception:
                pass
        # logging.info([endpoint_set, root_sitemap_field])
        return [endpoint_set, root_sitemap_field]
    except Exception as e:
        logging.error(f'Error in "sitemap_reader.sm_reader.auto_sitemap_reader": {e.__str__()}')
        logging.warning(exception_line())
        if is_internal_driver:
            try:
                driver.close()
            except Exception:
                pass
        return e.__str__()
