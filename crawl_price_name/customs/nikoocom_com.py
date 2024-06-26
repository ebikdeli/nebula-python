import settings
from selenium.webdriver.common.by import By
from drivers.selenium_driver import call_selenium_driver
from logs.exception_logs import exception_line
from crawl_price_name.random_generator import get_random_string
from crawl_price_name.functions import convert_to_english, combine_parse_convert_tag
import logging
import os
import ssl
import datetime
from urllib.request import urlretrieve
from PIL import Image



def price_title_image(href:str, site_id:int=None, link_id:int=None, save_image:bool=False, force_save_image:bool=False, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> list|None:
    """Crawl nikoocom to get price, title, and image of a product. If selenium driver could not get launched return None"""
    try:
        if not driver:
            driver = call_selenium_driver(site_url=href, timeout=timeout, implicit_wait=settings.GENERAL_IMPLICIT_WAIT)
            if not driver:
                logging.error('Driver did not created')
                return None
        print('Nikoocom function')
        # Get href title and price
        product_title = None
        product_price = -1
        is_available = False
        main_image = ''
        driver.get(href)
        # Product_title
        _h2_tags = driver.find_elements(By.TAG_NAME, 'h1')
        if _h2_tags:
            product_title = _h2_tags[0].text
        # print('product title: ', product_title)
        # Product_price
        _price_tags = driver.find_elements(By.CSS_SELECTOR, '.entry-summary .price .woocommerce-Price-amount bdi')
        if _price_tags:
            try:
                # product_price = int(convert_to_english(_price_tags[0].text))
                product_price = int(combine_parse_convert_tag(_price_tags[0]))
            except Exception:
                product_price = -1
        # print('product price: ', product_price)
        # If product is_available
        add_to_carts = driver.find_elements(By.CSS_SELECTOR, '.single_add_to_cart_button')
        for add_to_cart in add_to_carts:
            if 'افزودن به سبد خرید' in add_to_cart.text:
                is_available = True
        # print('is_available: ', is_available)
        # Find and save product_image
        import time
        time.sleep(2)
        main_image = find_image(driver=driver, site_id=site_id, link_id=link_id, force_save_image=force_save_image)
        try:
            driver.close()
        except Exception:
            pass
        logging.info(f'Crawled data from {href}:\n, {product_title}, {product_price}, {is_available}, {main_image}')
        return [product_title, product_price, is_available, main_image]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.customs.nikoocom_com": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return [None, -1, False, '']



def find_image(driver:object, site_id:int, link_id:int, force_save_image:bool=False) -> str|None:
    """Find product image in the nikoocom"""
    try:
        if force_save_image:
            try:
                site_id = str(site_id)
                link_id = str(link_id)
            except Exception:
                return ''
        main_image_url = ''
        # _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.styles_PdpProductContent__sectionBorder--mobile__J7liJ')
        # ! Has problem with crawling image
        _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.owl-item.active .img-thumbnail')
        if _main_product_content:
            _content_images = _main_product_content[0].find_elements(By.TAG_NAME, 'img')
            if _content_images:
                main_image_url = _content_images[0].get_attribute('src')
                print(main_image_url)
                # Save image
                if force_save_image:
                    # Disable SSL certificate verification for urllib (Below line is enough maybe by itself only, but to be more certain we add the 'ctx' or context the the urllib object)
                    ssl._create_default_https_context = ssl._create_unverified_context
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    # Download image and put it here temporary
                    _temprary_image_name = f'{get_random_string(6)}.webp'
                    urlretrieve(main_image_url, _temprary_image_name)                
                    # urlretrieve(main_image_url, _temprary_image_name)
                    # Open and resize (800 * 600) recently downloaded image
                    _original_image = Image.open(_temprary_image_name)
                    _new_image = _original_image.resize((800, 600))
                    # Save newly created image in a folder as 'images/site_id/link_id.webp'
                    # Following path finder-creater is a little messy but it works on every OS!
                    root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
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
        return main_image_url
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.customs.nikoocom_com": {e.__str__()}')
        logging.warning(exception_line())
        return ''
