"""Google Web Cache cannot be used if there is javascript in the page needed to be handled. Search bars, buttons, clickables, and everything else needed to be dynamically handled cannot be extracted with Google Web Cached"""
import settings
from .functions import  _torob_extract_price, _emalls_extract_price, _digikala_extract_price,\
    convert_to_english
from .general import general_match, find_image_url
from drivers.selenium_driver import call_selenium_driver
from logs.exception_logs import exception_line
from drivers.requests_setup import requests_init
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSelectorException
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging




def gc_get_title_price_image(parent:str, url:str, api_agent:str='selenium', driver:object=None, site_name:str=None, save_image:bool=False, force_save_image:bool=False, image_parent_selector:str=None, title_selector:str=None, button_selector:str=None, site_id:int=None, link_id:int=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, is_test:bool=False) -> list|str:
    """parent argumenet is a 'CSS_SELECTOR' with given url in Google Web Cache. If successful returns a 4-element list as [title, price, is_available, product_img_url] but if failed, return str"""
    try:
        base_url = url
        gc_base_url = f'https://webcache.googleusercontent.com/search?q=cache:'
        url = gc_base_url + url
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
            error_message = f"In Google Web Cache no element with css selector '{parent}' found or maybe the url is not a valid product link in {url}"
            logging.warning(error_message)
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
            if not image_url.startswith('http') and not urlparse(base_url).netloc.replace('www.', '') in image_url:
                image_url = f'{urlparse(base_url).scheme}://{urlparse(base_url).netloc.replace("www.", "")}{image_url}'
        product_name_price.append(image_url)
        try:
            driver.close()
        except Exception:
            pass
        print('Data extracted: ', product_name_price)
        return product_name_price
    except TimeoutException:
        logging.error(f'Error in "crawl_price_name.google_cache.gc_get_title_price_image": the url took to long to load and timeout')
        logging.warning(exception_line())
        error_message = f'webpage took to long to load and timeout'
        return error_message
    except WebDriverException:
        logging.error(f'Error in "crawl_price_name.google_cache.gc_get_title_price_image": the url does not exist or error in loading the page')
        logging.warning(exception_line())
        error_message = f'the url does not exist or error in loading the page'
        return error_message
    except Exception as e:
        logging.error(f'crawl_price_name.google_cache.gc_get_title_price_image": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return e.__str__()
