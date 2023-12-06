import settings
from .functions import  _torob_extract_price, _emalls_extract_price, _digikala_extract_price,\
    convert_to_english
from drivers.selenium_driver import call_selenium_driver
from logs.exception_logs import exception_line
from crawl_price_name import customs
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common import exceptions
from crawl_price_name.random_generator import get_random_string
import logging
import time
import os
import ssl
import datetime
from urllib.request import urlretrieve
from PIL import Image



# * (START) find price of a product by its name in digikala, torob, and emalls

def digikala_url_price(product_name:str, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.DIGIKALA_IMPLICIT_WAIT) -> list|int:
    """Get digikala product url. If successful return a 4-element list [product_link, product_title, product_price, image_url]. If no product found return 0. If any error happend return -1"""
    try:
        url = f'https://digikala.com/search/?q={product_name}'
        # ~~~~~~~~~~~~
        product_link = None
        product_title = None
        product_price = -1
        image_url = ''
        if not driver:
            try:
                driver = call_selenium_driver(timeout=timeout, implicit_wait=sleep_time)
                if not driver:
                    raise Exception('Driver did not created')
            except Exception as e:
                logging.error(f'Error in "crawl_price_name.external_call.get_digikala_url": {e.__str__()}')
                logging.warning(exception_line())
                return None
        driver.get(url)
        # We must wait for some time to fully load the search result page
        time.sleep(sleep_time)
        # Now we are in the product page resulted after enter the 'product_name'
        # driver.save_screenshot("screenshot-2.png")
        digikala = driver.find_element(By.CLASS_NAME, 'product-list_ProductList__pagesContainer__zAhrX')
        try:
            first_product = digikala.find_element(By.CLASS_NAME, 'product-list_ProductList__item__LiiNI')
        except exceptions.NoSuchElementException:
            # REMEMBER: If no product found for the name, digikala return a div tag with this class: "product-list_ProductList__emptyWrapper__Hh8Ij"
            logging.warning(f'No product found with this title: "{product_name}"')
            return 0
        # We just need first element to get its price and title and then return the data
        links = first_product.find_elements(By.TAG_NAME, 'a')
        if links:
            for a_tag in links:
                # print(a_tag.get_attribute('href'))
                # Go to the product page in torob and get it
                product_link = a_tag.get_attribute('href')
                driver.get(a_tag.get_attribute('href'))
                # Sleep a couple of seconds to ensure the page fully loaded
                time.sleep(1)
                product_title = driver.find_element(By.TAG_NAME, 'h1').text
                # Need some process to get product_price
                # ! Potential error in getting price from element with selector '.color-800.ml-1.text-h4'
                # price_tags = driver.find_elements(By.CSS_SELECTOR, '.jc-start .color-800.ml-1.text-h4')
                price_tags = driver.find_elements(By.CSS_SELECTOR, '.styles_BuyBoxFooter__actionWrapper__Hl4e7 .color-800.ml-1.text-h4')
                if not price_tags:
                    price_tags = driver.find_elements(By.CSS_SELECTOR, '.styles_BuyBoxFooter__actionWrapper__Hl4e7 .text-neutral-800.ml-1.text-h4')
                prices = set()
                if price_tags:
                    prices = _digikala_extract_price(price_tags, prices)
                if prices:
                    product_price = min(prices)
                # Get image url
                try:
                    # _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.styles_GalleryMobile__imageContainer__tIXDC')
                    _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.styles_InfoSection__rightSection__PiYpa')
                    if _main_product_content:
                        _content_images = _main_product_content[0].find_elements(By.TAG_NAME, 'img')
                        if _content_images:
                            image_url = _content_images[0].get_attribute('src')
                except Exception:
                    image_url = ''
                try:
                    driver.close()
                except Exception:
                    pass
                logging.info([product_link, product_title, product_price, image_url])
                return [product_link, product_title, product_price, image_url]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.external_call.get_digikala_url": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return -1



def torob_url_price(product_name:str, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.TOROB_IMPLICIT_WAIT) -> list|int:
    """Get torob product url. If successful return a 4-element list [product_link, product_title, product_price, image_url. If no product found return 0. If any error happend return -1"""
    try:
        url = f'https://torob.com/search/?query={product_name}'
        product_link = None
        product_title = None
        product_price = -1
        img_url = ''
        if not driver:
            try:
                driver = call_selenium_driver(timeout=timeout, implicit_wait=sleep_time)
                if not driver:
                    raise Exception('Driver did not created')
            except Exception as e:
                logging.error(f'Error in "crawl_price_name.external_call.torob_url_price": {e.__str__()}')
                logging.warning(exception_line())
                return None
        driver.get(url)
        # We must wait for some time to fully load the search result page
        time.sleep(sleep_time)
        # Now we are in the product page resulted after enter the 'product_name'
        # driver.save_screenshot("screenshot-2.png")
        try:
            torob_items = driver.find_element(By.CLASS_NAME, 'cards')
        except exceptions.NoSuchElementException:
            # REMEMBER: If no product found for the name, torob return a div tag with this class: "no-results"
            logging.warning(f'No product found with this title: "{product_name}"')
            return 0
        # We just need first element to get its price and title and then return the data
        links = torob_items.find_elements(By.TAG_NAME, 'a')
        if links:
            for a_tag in links:
                # print(a_tag.get_attribute('href'))
                # Go to the product page in torob and get it
                product_link = a_tag.get_attribute('href')
                driver.get(a_tag.get_attribute('href'))
                # Sleep a couple of seconds to ensure the page fully loaded
                # ! time.sleep(sleep_time)
                product_title = driver.find_element(By.TAG_NAME, 'h1').text
                # Need some process to get product_price
                # ! Potential error in getting price from element with selector '.price_text .jsx-63b317fab2efbae'
                price_tags = driver.find_elements(By.CSS_SELECTOR, '.price_text .jsx-63b317fab2efbae')
                prices = set()
                if price_tags:
                    prices = _torob_extract_price(price_tags, prices)
                # ! Potential error in getting price from element with selector '.buy_box_text'
                if not prices:
                    price_tags = driver.find_elements(By.CSS_SELECTOR, '.buy_box_text')
                    if price_tags:
                        prices = _torob_extract_price(price_tags, prices)
                if prices:
                    product_price = min(prices)
                # Get image url
                try:
                    # _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.styles_PdpProductContent__sectionBorder--mobile__J7liJ')
                    _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.product-info')
                    if _main_product_content:
                        _content_images = _main_product_content[0].find_elements(By.TAG_NAME, 'img')
                        if _content_images:
                            img_url = _content_images[0].get_attribute('src')
                except Exception:
                    img_url = ''
                # ! Later save image into file system...
                try:
                    driver.close()
                except Exception:
                    pass
                logging.info([product_link, product_title, product_price, img_url])
                return [product_link, product_title, product_price, img_url]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.external_call.get_torob_url": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return -1



def emalls_url_price(product_name:str, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.EMALLS_IMPLICIT_WAIT) -> list|int:
    """Get emalls product url. If successful return a 4-element list [product_link, product_title, product_price, image_url]. If no product found return 0. If any error happend return -1"""
    try:
        url = 'https://emalls.ir/'
        product_link = None
        product_title = None
        product_price = -1
        image_url = ''
        if not driver:
            try:
                driver = call_selenium_driver(timeout=timeout, implicit_wait=sleep_time)
                if not driver:
                    raise Exception('Driver did not created')
            except Exception as e:
                logging.error(f'Error in "crawl_price_name.external_call.emalls_url_price": {e.__str__()}')
                logging.warning(exception_line())
                return None
        driver.get(url)
        search_field = driver.find_element(By.ID, 'SearchInBottom_txtSearch')
        search_field.send_keys(product_name)
        # Submit the search elem
        search_field.send_keys(Keys.ENTER)
        # ! 'submit' method does not work good! we use 'Keys.ENTER' instead
        # search_field.submit()
        # Wait for new link to open up
        time.sleep(sleep_time)
        try:
            emalls_items = driver.find_element(By.ID, 'listdiv')
        except exceptions.NoSuchElementException:
            # REMEMBER: If no product found for the name, emalls return a div tag with this id: "DivNoItem"
            logging.warning(f'No product found with this title: "{product_name}"')
            return 0
        # We just need first element to get its price and title and then return the data
        products_list = emalls_items.find_elements(By.CLASS_NAME, 'product-block')
        if products_list:
            first_product_element = products_list[0]
            link_elem = first_product_element.find_element(By.TAG_NAME, 'a')
            link = link_elem.get_attribute('href')
            if link:
                # Current link is the product_link we want
                product_link = link
                # Move to the next page that is the product_link
                driver.get(link)
                # Wait a couple of seconds to page fully loaded
                # ! time.sleep(sleep_time)
                # In emalls, title of the product is a 2-part section. First section is english name and second section is in persian. In this function the english part taken as product name
                product_title = driver.find_element(By.ID, 'ContentPlaceHolder1_H1TitleDesktop').text.split('\n')[0]
                # Get product price
                # ! class 'itemprice' is unique in the product page in 'emalls' so its the best element to find the product_price
                price_tags = driver.find_elements(By.CLASS_NAME, 'itemprice')
                prices = set()
                if price_tags:
                    prices = _emalls_extract_price(price_tags, prices)
                if prices:
                    product_price = min(prices)
                # Get image url
                try:
                    _main_product_content = driver.find_elements(By.CSS_SELECTOR, '.img-pics')
                    if _main_product_content:
                        _content_images = _main_product_content[0].find_elements(By.TAG_NAME, 'img')
                        if _content_images:
                            image_url = _content_images[0].get_attribute('src')
                except Exception as e:
                    image_url = ''
                try:
                    driver.close()
                except Exception:
                    pass
                logging.info([product_link, product_title, product_price, image_url])
                return [product_link, product_title, product_price, image_url]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.external_call.get_emalls_url": {e.__str__()}')
        logging.warning(exception_line())
        try:
            driver.close()
        except Exception:
            pass
        return -1

# * (END) find price of a product by its name in digikala, torob, and emalls



# * Find product titles for other sellers in torob

def torob_seller_product_title(product_name:str, find_more_sellers:bool=False, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.TOROB_IMPLICIT_WAIT) -> list|int|None:
    """Get all titles from diffrent sellers for a product_name. If succeesful return a 5-element list as this: [seller_titles_list(list), href(str), main_seller_title(str), main_seller_price(int), main_image_url(str)]"""
    try:
        url = f'https://torob.com/search/?query={product_name}'
        product_titles = []
        product_link = None
        product_title = None
        product_price = -1
        img_url = ''
        if not driver:
            try:
                driver = call_selenium_driver(timeout=timeout, implicit_wait=sleep_time, disable_css=False)
            except (exceptions.WebDriverException, exceptions.NoSuchDriverException):
                logging.error('Selenium did not created for torob_seller_product_title')
                return None
        driver.get(url)
        # ? Selenium can take pictures from current time. COOL feature!
        # driver.save_screenshot("screenshot-1.png")
        # Submit the search elem (Torob has no submit button so we must submit the form by 'ENTER' key)
        # We must wait for some time to fully load the search result page
        time.sleep(sleep_time)
        # Now we are in the product page resulted after enter the 'product_name'
        # driver.save_screenshot("screenshot-2.png")
        try:
            torob_items = driver.find_element(By.CLASS_NAME, 'cards')
        except exceptions.NoSuchElementException:
            # REMEMBER: If no product found for the name, torob return a div tag with this class: "no-results"
            logging.warning(f'No product found with this title: "{product_name}"')
            return 0
        # We just need first element to get its price and title and then return the data
        links = torob_items.find_elements(By.TAG_NAME, 'a')
        if links:
            for a_tag in links:
                # Go to the product page in torob and get it
                product_link = a_tag.get_attribute('href')
                driver.get(a_tag.get_attribute('href'))
                # Sleep a couple of seconds to ensure the page fully loaded
                # ! time.sleep(sleep_time)
                time.sleep(sleep_time)
                # * Get current title and price for the current product
                product_title = driver.find_element(By.TAG_NAME, 'h1').text
                # Need some process to get product_price
                # ! Potential error in getting price from element with selector '.price_text .jsx-63b317fab2efbae'
                price_tags = driver.find_elements(By.CSS_SELECTOR, '.price_text .jsx-63b317fab2efbae')
                prices = set()
                if price_tags:
                    prices = _torob_extract_price(price_tags, prices)
                # ! Potential error in getting price from element with selector '.buy_box_text'
                if not prices:
                    price_tags = driver.find_elements(By.CSS_SELECTOR, '.buy_box_text')
                    if price_tags:
                        prices = _torob_extract_price(price_tags, prices)
                if prices:
                    product_price = min(prices)
                # Get image url
                img_tags = driver.find_elements(By.CSS_SELECTOR, '.jsx-63b317fab2efbae.gallery')
                if img_tags:
                    try:
                        img_tag = img_tags[0].find_element(By.TAG_NAME, 'img')
                        img_url = img_tag.get_attribute('src')
                    except Exception:
                        img_url = ''
                # ! Later save image into file system...
                # * Get other sellers title for the current product
                # ? If there are more than 4 sellers, we need to click on a button with this class name "show-more-btn"
                if find_more_sellers:
                    try:
                        show_more_button = driver.find_element(By.CLASS_NAME, 'show-more-btn')
                        show_more_button.click()
                    except exceptions.NoSuchElementException as e:
                        logging.info('No more button!')
                try:
                    time.sleep(sleep_time)
                    # ! In torob, sellers have their product title in a div with these classes: "product-name seller-element" so we are using this selector: ".product-name.seller-element"
                    # seller_title_tags = driver.find_elements(By.CSS_SELECTOR, '.jsx-528815776.product-name.seller-element')
                    seller_title_tags = driver.find_elements(By.CSS_SELECTOR, '.shop-card.seller-element')
                    # print('Number of sellers: ', len(seller_title_tags))
                    for seller_title_tag in seller_title_tags:
                        try:
                            pn = seller_title_tag.find_element(By.CSS_SELECTOR, '.product-name').text
                            if pn:
                                product_titles.append(seller_title_tag.find_element(By.CSS_SELECTOR, '.product-name').text)
                        except Exception:
                            continue
                except exceptions.NoSuchElementException as e:
                    logging.warning(f'No other selller sell a product with this title: {product_name}')
                    seller_title_tags = None
                if not seller_title_tags:
                    product_titles = None
                else:
                    # product_titles = product_titles[:10]
                    product_titles = product_titles
                # driver.close()
                # print(product_titles)
                return [product_titles, product_link, product_title, product_price, img_url]
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.external_call.torob_seller_product_title": {e.__str__()}')
        logging.warning(exception_line())
        return None
# torob_seller_product_title('لپ تاپ', True)
