import settings
import requests
from requests import Request, Session, Response
from requests.exceptions import Timeout, RequestException, TooManyRedirects,\
    ConnectionError, MissingSchema
import logging
from urllib import parse
from logs.exception_logs import exception_line


def requests_init(url:str, method:str='GET', data:dict=None, params:dict=None, headers:dict=None,
                  user_agent:str='chrome', use_proxy:bool=True, use_session:bool=False, is_url_sitemap:bool=False,
                  timeout:int=settings.REQUESTS_TIMEOUT) -> Response|None:
    """Use 'requests' to crawl webpages"""
    try:
        response = None
        proxies = dict()
        s = Session()
        if user_agent == 'chrome':
            user_agent = settings.REQUESTS_CHROME_USER_AGENT
            s.headers.update({'User-agent': user_agent})
        if use_proxy and settings.PROXY_LIST:
            site_url = parse.urlparse(url).netloc
            if 'www.' in site_url:
                site_url = site_url.replace('www.', '')
            if (site_url in settings.PROXY_WEBSITES or '*' in settings.PROXY_WEBSITES) or (settings.USE_PROXY_SITEMAP and is_url_sitemap):
                for proxy in settings.PROXY_LIST:
                    proxies.update({
                        'http': f'http://{proxy["username"]}:{proxy["password"]}@{proxy["address"]}:{proxy["port"]}'
                    })
        if method == 'GET':
            response = s.get(url=url, timeout=timeout, proxies=proxies)
        if method == 'POST':
            response = s.post(url=url, timeout=timeout, proxies=proxies)
        return response
    except Timeout:
        logging.error('request timeout')
        return None
    except MissingSchema as e:
        logging.error(e.__str__())
        return None
    except TooManyRedirects:
        logging.error('too many redirects and error in getting results')
        return None
    except ConnectionError as e:
        logging.error(f'connection error: {e.__str__()}')
        return None
    except RequestException:
        logging.error('error occured in requests library')
        return None
    except Exception as e:
        logging.error(f'Error in "drivers.requests_setup.requests_init": {e.__str__()}')
        logging.warning(exception_line())
        return None
