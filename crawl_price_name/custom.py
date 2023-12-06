import settings
from drivers.selenium_driver import call_selenium_driver
from logs.exception_logs import exception_line
import importlib
import logging
from urllib.parse import urlparse



def get_title_price_image(site_url:str, href:str, site_id:int=None, link_id:int=None, save_image:bool=False, force_save_image:bool=False, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> list|str:
    """Get the name, price and image of the product using custom crawl. If successful, return 4-element list contains [product_title, pruct using custom crawl. If successful, return 4-element list contains [product_title, product_price, is_available, image_url] If error happened return str
    NOTE: To save image, we must pass value to 'site_id' and 'link_id'"""
    try:
        # digikala_module = importlib.import_module('.digikala_com', 'crawl_price_name.customs')
        _module_name = f'.{site_url.replace(".", "_")}'
        _image_url = None
        # print(_module_name)
        try:
            _related_module = importlib.import_module(_module_name, 'crawl_price_name.customs')
        except ModuleNotFoundError as e:
            return f'custom site \'{site_url}\' has no custom module named \'{_module_name.replace(".", "")}\''
        result = _related_module.price_title_image(href=href,
                                                    site_id=site_id,
                                                    link_id=link_id,
                                                    save_image=save_image,
                                                    force_save_image=force_save_image,
                                                    timeout=timeout
                                                    )
        if result:
            _image_url = result[-1]
            if _image_url is None:
                _image_url = ''
        # Check if image_url is relative, change it to absolute_url
        if _image_url:
            if not _image_url.startswith('http') and not urlparse(href).netloc.replace('www.', '') in _image_url:
                _image_url = f'{urlparse(href).scheme}://{urlparse(href).netloc.replace("www.", "")}{_image_url}'
                result[-1] = _image_url
        return result
    except Exception as e:
        logging.error(f'Error in "crawl_price_name.custom.get_name_price": {e.__str__()}')
        logging.warning(exception_line())
        return e.__str__()
        # return None
