import settings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, SessionNotCreatedException, WebDriverException
from seleniumwire import webdriver as sww
from seleniumwire import undetected_chromedriver as swuc
import undetected_chromedriver as uc
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service
from logs.exception_logs import exception_line
import logging
import random
import pathlib
import os
import validators
from urllib import parse
from settings import PROXY_LIST, CHROME_BROWSER_VERSION




def call_selenium_driver(site_url:str='', headless:bool=settings.USE_HEADLESS_SELENIUM, timeout:int=settings.CHROME_DRIVER_TIMEOUT,
                        no_image:bool=True, implicit_wait:float=None,
                        use_proxy:bool=True, random_proxy:bool=True,
                        disable_css:bool=settings.DISABLE_CSS_JS_SELENIUM, silent_mode=False,
                        is_url_sitemap:bool=False, is_test:bool=False) -> WebDriver|int|None:
    """Call selenium driver with many options. To use proxy server, provide proxy server ip address and port. With 'site_url' decide if proxy should used to call the website.
    NOTE: seleniumwire driver is slower than standard selenium webdriver. So this code only use it if there are proxies provided in the 'settings.PROXY_LIST'"""
    try:
        driver = None
        seleniumwire_options = None
        selenium_driver_path = os.path.join(pathlib.Path().resolve(), "drivers", "chromedriver-win64-119")
        selenium_driver_executable_path = os.path.join(pathlib.Path().resolve(), "drivers", "chromedriver-win64-119", 'chromedriver.exe')
        # Set undetected or standard driver option for selenium
        if settings.USE_SELENIUM_UNDETECTED:
            options = swuc.ChromeOptions()
        else:
            options = webdriver.ChromeOptions()
        # options.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2})
        if headless:
            options.add_argument('headless')
        if no_image:
            # 2 following line both can disable image loading but first one is more common
            options.add_argument('--blink-settings=imagesEnabled=false')
            options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        # options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument('--disable-gpu')
        # Following 4 options are used to test if performance can get better
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-features=NetworkService")
        options.add_argument("--disable-features=VizDisplayCompositor")
        # Selenium log level
        # options.add_argument("--log-level=1")
        # Selenium silent mode
        if silent_mode:
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # Following 'prefs' dictionary used for disable css (supposly) and optimize the code
        # Pass the argument 1 to allow and 2 to block (We need javascript to be loaded so we set it to 1)
        if disable_css:
            prefs = {'profile.default_content_setting_values': {'cookies': 2, 'images': 2, 'javascript': 2,
                                'plugins': 2, 'popups': 2, 'geolocation': 2,
                                'notifications': 2, 'auto_select_certificate': 2, 'fullscreen': 2,
                                'mouselock': 2, 'mixed_script': 2, 'media_stream': 2,
                                'media_stream_mic': 2, 'media_stream_camera': 2, 'protocol_handlers': 2,
                                'ppapi_broker': 2, 'automatic_downloads': 2, 'midi_sysex': 2,
                                'push_messaging': 2, 'ssl_cert_decisions': 2, 'metro_switch_to_desktop': 2,
                                'protected_media_identifier': 2, 'app_banner': 2, 'site_engagement': 2,
                                'durable_storage': 2}}
            options.add_experimental_option(
                "prefs", prefs
            )
        else:
            # Atleast disable notifications
            options.add_experimental_option(
                "prefs", {"profile.default_content_setting_values.notifications": 2}
            )
        # Provide proxy server
        if use_proxy:
            if PROXY_LIST:
                if validators.url(site_url):
                    domain = parse.urlparse(site_url).netloc
                    site_url = domain.replace('www.', '')
                # Check if site_url is in the list of 'PROXY_WEBSITES'
                if ('*' in settings.PROXY_WEBSITES or site_url in settings.PROXY_WEBSITES) or (settings.USE_PROXY_SITEMAP and is_url_sitemap):
                    print(f'USE PROXY FOR \'{site_url}\'')
                    # Pick a proxy connection randomly
                    if random_proxy:
                        proxy = random.choice(PROXY_LIST)
                    # Or pick the first proxy
                    else:
                        proxy = PROXY_LIST[0]
                    seleniumwire_options = {
                        'proxy': {
                            'http': f'http://{proxy["username"]}:{proxy["password"]}@{proxy["address"]}:{proxy["port"]}',
                            'verify_ssl': False,
                        },
                    }
        # ! Check if current selenium webdriver is compatible with chrome browser. If not compatible use other chromedrivers in current directory
        # ! (Switching following try-exception is very slow. We must find another way to get right driver) NOTE: See 'The other way'
        # try:
        #     # ? If seleniumwire_options dictionary is not null, we must use seleniumwire to create chrome driver. Otherwise use standard chrome webdriver
        #     if seleniumwire_options:
        #         driver = sww.Chrome(options=options, seleniumwire_options=seleniumwire_options)
        #     else:
        #         driver = webdriver.Chrome(options=options)
        # except (SessionNotCreatedException, NoSuchDriverException) as e:
        # ! The other way:
        if CHROME_BROWSER_VERSION != 119:
            if seleniumwire_options:
                if settings.USE_SELENIUM_UNDETECTED:
                    driver = swuc.Chrome(driver_executable_path=selenium_driver_executable_path, options=options, seleniumwire_options=seleniumwire_options, use_subprocess=True)
                else:
                    driver = sww.Chrome(options=options, seleniumwire_options=seleniumwire_options)
            else:
                if settings.USE_SELENIUM_UNDETECTED:
                    driver = uc.Chrome(driver_executable_path=selenium_driver_executable_path, options=options, use_subprocess=True)
                else:
                    driver = webdriver.Chrome(options=options)
        # ! From Chrome 116 onward selenium does not locate chrome driver automatically. So we must locate the downloaded driver with absolute path and feed it to selenium
        else:
            service = Service(f'{selenium_driver_path}\chromedriver.exe')
            # ? If seleniumwire_options dictionary is not null, we must use seleniumwire to create chrome driver. Otherwise use standard chrome webdriver
            if seleniumwire_options:
                if settings.USE_SELENIUM_UNDETECTED:
                    driver = swuc.Chrome(driver_executable_path=selenium_driver_executable_path, options=options, seleniumwire_options=seleniumwire_options, use_subprocess=True)
                else:
                    driver = sww.Chrome(options=options, service=service, seleniumwire_options=seleniumwire_options)
            else:
                if settings.USE_SELENIUM_UNDETECTED:
                    driver = uc.Chrome(driver_executable_path=selenium_driver_executable_path, options=options, use_subprocess=True)
                else:
                    driver = webdriver.Chrome(options=options, service=service)
        # logging.info(f'Chrome driver version: {driver.capabilities["browserVersion"]}')
        driver.set_page_load_timeout(timeout)
        # Set windows size
        driver.set_window_size(1600, 1000)
        if implicit_wait is not None:
            driver.implicitly_wait(implicit_wait)
        return driver
    except TimeoutException:
        logging.error('Error in "driver.selenium_driver.call_selenium_driver": Chrome driver timeout')
        logging.warning(exception_line())
        return -1
    except (WebDriverException, SessionNotCreatedException):
        logging.error('Error in "driver.selenium_driver.call_selenium_driver": Chrome driver did not created')
        logging.warning(exception_line())
        return 0
    except Exception as e:
        logging.error(f'Error in "driver.selenium_driver.call_selenium_driver": {e.__str__()}')
        logging.error('driver has not been created')
        logging.warning(exception_line())
        return None
