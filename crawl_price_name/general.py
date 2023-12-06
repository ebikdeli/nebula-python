import settings
from .functions import combine_parse_convert_tag, is_product_available, find_price_in_meta_tags,\
    meta_availability_tag
from .random_generator import get_random_string
from logs.exception_logs import exception_line
from drivers.selenium_driver import call_selenium_driver
from drivers.requests_setup import requests_init
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from urllib.request import urlretrieve
from urllib.parse import urlparse
from urllib.error import HTTPError
import logging
import os
import ssl
from PIL import Image
from http.client import InvalidURL
import validators




def general_match(parent_selector:str, page_data:str, driver:object, url:str, api_agent:str='selenium', title_selector:str=None, button_selector:str=None, site_name:str=None) -> list|str:
    """parent argument is a CSS_SELECTOR. returns 3-element list:
    first element is the product_name. second element is the product_price. third element is a boolean that tell if the product is available or not
    NOTE: Only return 'price' as -1 if there are any error in the function or price found but product is not available"""
    try:
        min_price = 0
        price_set = set()
        product_is_available = False
        product_name = ''
        _price_is_rial = False
        total_soup = BeautifulSoup(page_data, features='html.parser')
        soups = total_soup.select(parent_selector)
        logging.info('general match started')
        # If any error happens, in 'extractor' module the error logged and we don't need to log any error here
        if not soups:
            error_message = f"No css selector found with '{parent_selector}'"
            # logging.error(error_message)
            return error_message
        # CSS_SELECTOR might not be unique. So it's important to use for loop to iterate over all selectors
        # ! PRODUCT TITLE
        # If 'title_selector' is not empty, try to get 'product_title' from it
        if api_agent == 'selenium':
            if title_selector:
                titles = driver.find_elements(By.CSS_SELECTOR, title_selector)
                if titles:
                    product_name = titles[0].text.strip()
            # If not 'title_selector' received, try to find any tag with selector 'product_title' or 'product_name'
            if not product_name:
                titles = driver.find_elements(By.CSS_SELECTOR, '.product-title')
                if not titles:
                    titles = driver.find_elements(By.CSS_SELECTOR, '.product-name')
                if titles:
                    product_name = titles[0].text.strip()
            # If not 'title' found, try to find product_name in h1 tag and if not found get it from 'title' tag with some process
            if not product_name:
                h1_tags = driver.find_elements(By.TAG_NAME, 'h1')
                if h1_tags:
                    if len(h1_tags[0].text) > 0:
                        product_name = h1_tags[0].text
                    else:
                        for h1_tag in h1_tags:
                            if len(h1_tag.text) > 0:
                                product_name = h1_tag.text
                                break
            if not product_name:
                # logging.warning(f'{url} does not have \'h1\' as product title name')
                h2_tags = driver.find_elements(By.TAG_NAME, 'h2')
                for h2_tag in h2_tags:
                    if h2_tag.text:
                        product_name = h2_tag.text
                        break
                if not product_name:
                    # logging.warning(f'{url} does not have \'h2\' as product title name')
                    h3_tags = driver.find_elements(By.TAG_NAME, 'h3')
                    for h3_tag in h3_tags:
                        if h3_tag.text:
                            product_name = h3_tag.text
                            break
            if not product_name and site_name:
                try:
                    # logging.warning(f'{url} does not have \'h1\' and \'h2\' as product title name')
                    product_name = ' '.join([t_text.strip() for t_text in driver.find_element(By.TAG_NAME, 'title').text.split(site_name)])
                except Exception:
                    pass
            # If product name not found in h1 tag try title tag
            if not product_name and not site_name:
                # logging.warning('Product name not found at all! So return page "title" tag as title')
                # This is the last effort to return a title for the product
                product_name = driver.find_element(By.TAG_NAME, 'title').text
        elif api_agent == 'requests':
            if title_selector:
                titles = total_soup.select(title_selector)
                if titles:
                    product_name = titles[0].text.strip()
            # If not 'title_selector' received, try to find product_name in h1 tag and if not found get it from 'title' tag with some process
            if not product_name:
                h1_tags = total_soup.find_all('h1')
                if h1_tags:
                    if len(h1_tags[0].text) > 0:
                        product_name = h1_tags[0].text.strip()
                    else:
                        for h1_tag in h1_tags:
                            if len(h1_tag.text) > 0:
                                product_name = h1_tag.text.strip()
                                break
            if not product_name:
                # logging.warning(f'{url} does not have \'h1\' as product title name')
                h2_tags = total_soup.find_all('h2')
                for h2_tag in h2_tags:
                    if h2_tag.text:
                        product_name = h2_tag.text.strip()
                        break
                if not product_name:
                    # logging.warning(f'{url} does not have \'h2\' as product title name')
                    h3_tags = total_soup.find_all('h3')
                    for h3_tag in h3_tags:
                        if h3_tag.text:
                            product_name = h3_tag.text
                            break
            if not product_name and site_name:
                try:
                    # logging.warning(f'{url} does not have \'h1\' and \'h2\' as product title name')
                    product_name = ' '.join([t_text.strip() for t_text in total_soup.find('title').text.split(site_name)])
                except Exception:
                    pass
            # If product name not found in h1 tag try title tag
            if not product_name and not site_name:
                # logging.warning('Product name not found at all! So return page "title" tag as title')
                # This is the last effort to return a title for the product
                product_name = total_soup.find('title').text
        if not product_name:
            error_message = 'Could not find the title. Maybe this link is not a valid product link or maybe the title is not in h1, h2, or h3 tag'
            # logging.warning(error_message)
            return error_message
        # Remove special characters from product_title
        if product_name:
            product_name = product_name.replace('\t', '').replace('\r', '').replace('\n', '')
        # Check if there is button_selector use it to know if add-to-cart button is in the page (For now we keep it very simple)
        if button_selector:
            cart_tags = total_soup.select(button_selector)
            product_is_available = True if cart_tags else False
        # ! SCRAP PRICE
        # First we search in <meta> tags and try to find product price in them
        price_set = find_price_in_meta_tags(beautiful_soup_object=total_soup, price_set=price_set)
        if price_set:
            logging.info(f'SMALLEST PRICE FOUND IN META TAG: {price_set}')
            min_price = min(price_set)
        # ! We Assume all product data is in the first occurance of the parent selector (If there is more than one tag with the parent selector in the page)
        for soup in soups:
            tags = soup.find_all()
            # Iterate through all the tags in the page to find price and know if item is available
            for tag in tags:
                # Check if price is rial (For some odd reason in following line both 'ریال' are diffrent. first one is inserted directly with keyboard and the second one copied from a persian text)
                if 'ریال' in tag.text or 'ريال' in tag.text:
                    _price_is_rial = True
                if not button_selector:
                    if not product_is_available:
                        if not tag.text:
                            continue
                        # Check if product is available by known patterns
                        if is_product_available(tag.text):
                            product_is_available = True
                        # Some websites has <meta> tag with a 'property' attribute with value of 'og:availability'. It's 'content' attribute tells us if the product is available or not
                        else:
                            _meta_availability = meta_availability_tag(total_soup)
                            if _meta_availability is True:
                                product_is_available = True
                            elif _meta_availability is False:
                                product_is_available = False
                # Make sure if product is unavailable by known patterns
                if product_is_available:
                    # if is_product_not_available(tag.text):
                    #         product_is_available = False
                    #         min_price = -1
                    pass
                # If price not found in the <meta> tag and we are not sure if product is not available, try to find any potential price in the 'parent_selector' contents
                if min_price <= 0:
                    for attr, value in tag.attrs.items():
                        # print(attr, ' ==> ', value)
                        # Check 'class' attribute of the current tag
                        if attr == 'class':
                            for classes in value:
                                if 'price' in classes or 'Price' in classes or 'pricing' in classes:
                                    # Parse remaining tags to find prices
                                    price_set.add(combine_parse_convert_tag(tag))
                        # Check other attributes (other than class attribute) of the current tag to find price
                        if 'price' in attr or 'Price' in attr or 'price' in value or 'Price' in value or 'pricing' in value:
                            # Parse remaining tags to find prices
                            price_set.add(combine_parse_convert_tag(tag))
            # ! Only loop throught 'soups' objects for once (If we want to iterate over all the soup tags delete 'break' command below)
            if price_set:
                break
        if 0 in price_set:
            price_set.remove(0)
        if price_set:
            _price_set = price_set.copy()
            # Delete unrelated number from price_set
            for elem in _price_set:
                if elem < 999 or elem > 999999999:
                    price_set.remove(elem)
            try:
                logging.info(f'founded prices {price_set} in link: {url}')
                min_price = min(price_set)
            except Exception:
                min_price = -1
        else:
            min_price = -1
            product_is_available = False
        if not product_is_available:
            logging.warning(f'Product is not available so price should set to -1 in: {url}')
        if min_price > 0 and _price_is_rial:
            print('price is Rial')
            min_price = int(min_price / 10)
        return [product_name, min_price, product_is_available]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.general.general_match": {e.__str__()}')
        logging.warning(exception_line())
        return e.__str__()



def find_image_url(page_data:str=None, api_agent:str='selenium', url:str=None, save_image:bool=False, force_save_image:bool=False, image_parent_selector:str=None, site_id:int=None, link_id:int=None, driver:object=None, product_title:str=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> str:
    """Extract main image of the product, If any error occured or not page_data, url and driver provided, return None"""
    try:
        if api_agent == 'selenium':
            if not page_data or not product_title:
                if url and driver:
                    driver = call_selenium_driver(site_url=url, timeout=timeout, implicit_wait=settings.GENERAL_IMPLICIT_WAIT)
                    page_data = driver.get(url)
                    if not driver:
                        return ''
                else:
                    return ''
        elif api_agent == 'requests':
            if not page_data:
                response = requests_init(url=url)
                if not response:
                    logging.error(f'Cannot open "{url}"')
                    return ''
                if response.status_code != 200:
                    logging.error(f'{url} does not loaded well')
                    return ''
                page_data = response.content
            soup = BeautifulSoup(page_data, 'html.parser')
        image_url = ''
        # If 'image_parent_selector' exists, find image based on this selector
        if image_parent_selector:
            if api_agent == 'selenium':
                _img_selector_body = driver.find_elements(By.CSS_SELECTOR, image_parent_selector)
                if _img_selector_body:
                    _img_selector_body = _img_selector_body[0]
                    # If current tag is 'img', try to extract 'src' value from it, else find 'img' tag in it
                    if _img_selector_body.tag_name == 'img':
                        try:
                            image_url = _img_selector_body.get_attribute('src')
                        except Exception:
                            pass
                    # Try to find all 'img' tags in 'image_parent_selector' tag. If found any, return the 'src' of the first founded 'img'
                    else:
                        _img_tags = _img_selector_body.find_elements(By.TAG_NAME, 'img')
                        if _img_tags:
                            _img_tag = _img_tags[0]
                            try:
                                image_url = _img_tag.get_attribute('src')
                            except Exception:
                                pass
            elif api_agent == 'requests':
                _img_selector_body = soup.select(image_parent_selector)
                if _img_selector_body:
                    _img_selector_body = _img_selector_body[0]
                    # If current tag is 'img', try to extract 'src' value from it, else find 'img' tag in it
                    if _img_selector_body.name == 'img':
                        try:
                            image_url = _img_selector_body.attrs.get('src', '')
                        except Exception:
                            pass
                    # Try to find all 'img' tags in 'image_parent_selector' tag. If found any, return the 'src' of the first founded 'img'
                    else:
                        _img_tags = _img_selector_body.find_all('img')
                        if _img_tags:
                            _img_tag = _img_tags[0]
                            try:
                                image_url = _img_tag.attrs.get('src', '')
                            except Exception:
                                pass
        # If no 'image_url' returned, search all the body of the page for the image
        if not image_url:
            soup = BeautifulSoup(page_data, features='html.parser')
            image_url = ''
            # ? In many e-commerce websites, there is a meta tag with an attribute named 'property' with the value of 'og:image'. Commonly this tag contains main image of the product in the website
            meta_tags = soup.find_all('meta')
            for meta_tag in meta_tags:
                meta_propery = meta_tag.attrs.get('property', None)
                if meta_propery == 'og:image':
                    meta_og_image = meta_tag.attrs.get('content', None)
                    if meta_og_image:
                        image_url = meta_og_image
                        break
            if not image_url:
                # In the whole of the page try to find all img tags
                body = soup.find('body')
                img_tags = body.find_all('img')
                # ? Find image based on value of <img> 'data-lazy-src' attr
                for img_tag in img_tags:
                    _image_srcset = img_tag.attrs.get('data-lazy-src', None)
                    _image_src = img_tag.attrs.get('src', None)
                    if _image_srcset and _image_src:
                        if _image_src in _image_srcset:
                            image_url = _image_src
                            break
                # ? Many tags in wordpress websites has img tag with attribute 'data-magnify-src'
                for img_tag in img_tags:
                    data_magnify_src = img_tag.get('data-magnify-src', None)
                    if data_magnify_src:
                        if validators.url(data_magnify_src):
                            image_url = data_magnify_src
                            break
                # ? If any 'img' tag has 'data-src' attribute, and the value of the attribute is a valid url, get that url as 'image-url'
                for img_tag in img_tags:
                    data_src = img_tag.get('data-src', None)
                    if data_src:
                        if validators.url(data_src):
                            # print('data-src: ', data_src)
                            image_url = data_src
                            break
                # ? Try to find the first image that it's 'alt' attribute is equal to product title found in the 'general match' function
                if not image_url:
                    for img_tag in img_tags:
                        # ! Find image based on equality of <img> 'alt' attr and product_title
                        _alt_text = img_tag.attrs.get('alt', None)
                        if _alt_text:
                            if _alt_text == product_title or _alt_text.replace("'", " ") == product_title or _alt_text.replace('"', " ") == product_title:
                                try:
                                    image_url = img_tag.attrs['src']
                                    break
                                except KeyError:
                                    pass
            # If still not found 'image_url' get the first image in the received 'page_data'
            if not image_url:
                _img_tags = soup.select('img')
                if _img_tags:
                    _first_img_tag = _img_tags[0]
                    try:
                        image_url = _first_img_tag.attrs.get('src', None)
                    except Exception:
                        pass
        # If save_image flag is up, save image on in a file
        if image_url and save_image:
            site_id = str(site_id)
            link_id = str(link_id)
            # If 'force_save_image' flag is false, check if the image is already exist
            if not force_save_image:
                if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', site_id, f'{link_id}.webp')):
                    return image_url
            # Disable SSL certificate verification for urllib (Below line is enough maybe by itself only, but to be more certain we add the 'ctx' or context the the urllib object)
            ssl._create_default_https_context = ssl._create_unverified_context
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            # Download image and put it here temporary
            _temprary_image_name = f'{get_random_string(6)}.webp'
            # ! Does not seem urlretrieve can save image with non-ascii encoded url (like persian language urls) so we use requests library to save image
            try:
                urlretrieve(image_url, _temprary_image_name)
            except (UnicodeEncodeError, InvalidURL, HTTPError, ValueError) as _e:
                try:
                    import requests
                    r = requests.get(image_url)
                    if r.status_code == 200:
                        with open(_temprary_image_name, 'wb') as f:
                            f.write(r.content)
                            # print('image saved')
                    else:
                        return ''
                except Exception:
                    logging.warning('Image did not get downloaded')
                    return ''
            # Open and resize (800 * 600) recently downloaded image
            _original_image = Image.open(_temprary_image_name)
            _new_image = _original_image.resize((800, 600))
            # Save newly created image in a folder as 'images/site_id/link_id.webp'
            # Following path finder-creater is a little messy but it works on every OS!
            root_path = os.path.dirname(os.path.dirname(__file__))
            if not os.path.exists(os.path.join(root_path, "images", site_id)):
                os.makedirs(os.path.join(root_path, "images", site_id))
            image_path = os.path.join(root_path, "images", site_id)
            image_path_name = os.path.join(image_path, link_id)
            _new_image.save(f'{image_path_name}.webp', 'WEBP')
            # Close files to save resources
            _original_image.close()
            _new_image.close()
            # Delete downloaded file
            os.remove(_temprary_image_name)
        return image_url
    except Exception as e:
        logging.error(f'Error in crawl_price_name.general.find_image_url: {e.__str__()}')
        logging.warning(exception_line())
        return None



def get_title_price_image(parent:str, url:str, api_agent:str='selenium', driver:object=None, site_name:str=None, save_image:bool=False, force_save_image:bool=False, image_parent_selector:str=None, title_selector:str=None, button_selector:str=None, site_id:int=None, link_id:int=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, is_test:bool=False) -> list|str:
    """parent argumenet is a 'CSS_SELECTOR' with given url. If successful returns a 4-element list as [title, price, is_available, product_img_url] but if failed, return str"""
    try:
        if api_agent == 'selenium':
            if not driver:
                driver = call_selenium_driver(site_url=url, timeout=timeout, implicit_wait=settings.GENERAL_IMPLICIT_WAIT)
                if not driver:
                    raise Exception('selenium did not initialized!')
            driver.get(url)
            page_data = driver.page_source
            elem = driver.find_elements(By.CSS_SELECTOR, parent)
        elif api_agent == 'requests':
            response = requests_init(url=url)
            if not response:
                error_message = f"Cannot open '{url}'"
                logging.error(error_message)
                return error_message
            if response.status_code != 200:
                error_message = f'{url} did not loaded well'
                logging.error(error_message)
                return error_message
            page_data = response.content
            soup = BeautifulSoup(page_data, 'html.parser')
            elem = soup.select(parent)
        if not elem:
            error_message = f"No element with css selector '{parent}' found or maybe the url is not a valid product link in {url}"
            # logging.warning(error_message)
            return error_message
        product_name_price = general_match(parent_selector=parent,
                                            page_data=page_data,
                                            driver=driver,
                                            url=url,
                                            api_agent=api_agent,
                                            title_selector=title_selector,
                                            button_selector=button_selector,
                                            site_name=site_name)
        # If there is an error in 'general_match', 'product_name_price' would be an str
        if isinstance(product_name_price, str):
            return product_name_price
        image_url = find_image_url(page_data=page_data,
                                    api_agent=api_agent,
                                    product_title=product_name_price[0],
                                    save_image=save_image,
                                    force_save_image=force_save_image,
                                    image_parent_selector=image_parent_selector,
                                    site_id=site_id,
                                    link_id=link_id,
                                    driver=driver,
                                    timeout=timeout)
        if image_url is None:
            image_url = ''
        # Check if image_url is relative, change it to absolute_url
        if image_url:
            if not image_url.startswith('http') and urlparse(url).netloc.replace('www.', '') not in image_url:
                image_url = f'{urlparse(url).scheme}://{urlparse(url).netloc.replace("www.", "")}{image_url}'
        product_name_price.append(image_url)
        try:
            driver.close()
        except Exception:
            pass
        print('Data extracted: ', product_name_price)
        return product_name_price
    except TimeoutException:
        logging.error('Error in "crawl_price_name.get_price_name": the url took to long to load and timeout')
        logging.warning(exception_line())
        error_message = 'webpage took to long to load and timeout'
        return error_message
    except WebDriverException:
        logging.error('Error in "crawl_price_name.get_price_name": the url does not exist or error in loading the page')
        logging.warning(exception_line())
        error_message = 'the url does not exist or error in loading the page'
        return error_message
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.general.get_price_name": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return e.__str__()
