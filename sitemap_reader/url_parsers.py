import urllib
from urllib.parse import urlparse
from difflib import SequenceMatcher
import logging



def _normalize_domain(url:str) -> str:
    """If received domain is a url, change it to a normal domain without www."""
    domain = urllib.parse.urlparse(url).netloc
    if 'www.' in domain:
        domain = domain.replace('www.', '')
    return domain


def _parse_url_title_sitemaps(url:str) -> bool:
    """Check the url and tell if this link related to product sitemap or not"""
    # filter_list = ['blog', 'Blog', 'article', 'Article',
    #                'post', 'Post', 'login', 'account',
    #                'signup', 'news', 'News', 'compare',
    #                'brand', 'category', 'tag']
    filter_list = ['blog', 'Blog', 'article', 'Article',
                   'login', 'account', 'about-us', 'contact-us',
                   'signup', 'news', 'News', 'compare', 'discount',
                   'whatsapp', 'telegram', 'api', 'instagram', 'image',
                   '.jpg', '.png', '.webp', 'image', '.org']
    result = [elem for elem in filter_list if (elem in url)]
    if bool(result):
        return False
    return True


def _parse_url_title_product(url:str) -> bool:
    """Check the url and tell if this link related to product or not"""
    # ! If any word of the below list is in the url, assume it's a product
    # filter_list = ['product', 'Product', 'products', 'Products']
    # result = [elem for elem in filter_list if (elem in url)]
    # if bool(result):
    #     return True
    # ! If any word of the below list is in the url, assume is's not a product
    filter_list = ['blog', 'article', 'order',
                'login', 'account', 'signup', 'news',
                'News', 'sitemap', 'brand', 'contact', 'cart',
                'refund', 'yoast', 'yoa.st', '.xsl', 'verify',
                'taxonomy', 'taxonomies', 'telegram', 'whatsapp',
                'instagram', 'product-tag', 'product_tag', 'product-category',
                'product-cat', 'tel', 'about-us', 'shipping'
                'category', '.png', '.jpg', '.webp', '.org']
    res2 = [elem for elem in filter_list if (elem in url)]
    if not res2:
        filter_list_2 = ['/product/', '/Product/']
        res2 = [elem for elem in filter_list_2 if (elem in url)]
        if res2:
            return True
    return False


def _parse_url_title_category(url:str) -> bool:
    """Parse link url and check if the link is a 'category' link"""
    filter_list = ['category', 'cat', 'mobile',
                   'phone', 'tablet', 'laptop',
                   'accessory', 'samsung', 'apple',
                   'xiaomi', 'redmi', 'lg',]
    res2 = [elem for elem in filter_list if (elem in url)]
    if res2:
        return True
    return False


def _parse_generic_title(url:str, filter_list) -> bool:
    """Parse the 'url' based on the filter_list and if any element in the filter_list is in the url return False"""
    result = [elem for elem in filter_list if (elem in url)]
    if bool(result):
        return False
    return True



def _create_product_url_pattern(example_links:str) -> str|None:
    """process example_links and create a pattern to identify product url pattern. If example_links only has one link, return None"""
    if ',' in example_links:
        example_links_list = [link.strip().lower() for link in example_links.split(',') if len(link.strip()) > 0 and link.strip().startswith('http')]
        # Make sure in the elements of 'example_links_list' are valid urls because some urls have ',' in them!
        if len(example_links_list) > 1:
            # match = SequenceMatcher(None, example_links_list[0], example_links_list[1]).find_longest_match()
            match = SequenceMatcher(None, example_links_list[0], example_links_list[1]).get_matching_blocks()[0]
            common_pattern = example_links_list[0][match.a:match.a + match.size]
            print("COMMON PATTERN: ", common_pattern)
            domain = _normalize_domain(example_links_list[0])
            # Following block very unlikely to happen. But we implemented it anyway!
            if not domain in common_pattern:
                if 'product/' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('product/')[:2])
                    return pattern
                if 'products/' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('products/')[:2])
                    return pattern
                if 'product-' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('product-')[:2])
                    return pattern
                if 'product' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('product')[:2])
                    return pattern
                if 'p-' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('p-')[:2])
                    return pattern
                if 'pm-' in example_links_list[0]:
                    pattern = ''.join(example_links_list[0].partition('pm-')[:2])
                    return pattern
            if not common_pattern.endswith('/'):
                # if not (common_pattern.endswith('product-') or common_pattern.endswith('product_') or common_pattern.endswith('p') or common_pattern.endswith('p-') or common_pattern.endswith('pm-')):
                if 'product/' in common_pattern:
                    common_pattern = ''.join(common_pattern.partition('product/')[:2])
                    return common_pattern
                if 'products/' in common_pattern:
                    common_pattern = ''.join(common_pattern.partition('products/')[:2])
                    return common_pattern
                if 'product-' in common_pattern:
                    common_pattern = ''.join(common_pattern.partition('product-')[:2])
                    return common_pattern
                if 'products-' in common_pattern:
                    common_pattern = ''.join(common_pattern.partition('products-')[:2])
                    return common_pattern
                if 'product' in common_pattern:
                    common_pattern = ''.join(common_pattern.partition('product')[:2])
                elif not (common_pattern.endswith('p') or common_pattern.endswith('p-') or common_pattern.endswith('pm-')):
                    last_slash_index = common_pattern.rfind('/')
                    common_pattern = common_pattern[:last_slash_index+1]
            return common_pattern
        else:
            logging.warning('Only 1 link provided in the \'example_link\' field and ignored')
    return None


def _is_product_url(url:str, pattern:str|None, pattern_scheme:str=None) -> bool:
    """Parse url based on received patter and tell if url is related to product or not. Pattern must be checked with either 'http' and 'https'"""
    if pattern is None:
        return False
    # print('IS PRODUCT URL')
    if pattern_scheme is None:
        pattern_scheme = urlparse(url).scheme
    # Check if 'www' is in product pattern and product url and normalize pattern to be equall to url
    if 'www.' in url and not 'www.' in pattern:
        pattern = pattern.replace(urlparse(pattern).netloc, f'www.{urlparse(pattern).netloc}')
    if 'www.' not in url and 'www.' in pattern:
        pattern = pattern.replace('www.', '')
    if pattern_scheme == 'https':
        if pattern in url:
            # print('OK1111111111')
            return True
        pattern = pattern.replace('https', 'http')
        if pattern in url:
            return True
    elif pattern_scheme == 'http':
        if pattern in url:
            # print('OK2222222222222222')
            return True
        pattern = pattern.replace('http', 'https')
        if pattern in url:
            return True
    return False



def _second_layer_product_url_filter(url:str) -> bool:
    """If _is_product_url is True, get through this layer"""
    filter_list = ['login', 'signup', 'account', 'about-us', 
                   'about', 'contact-us', 'contact', 'faq',
                   'discount', 'privacy' , 'payment', 'policy',
                   'w3.org', '.jpg', '.png', '.webp', '.org']
    result = [elem for elem in filter_list if (elem in url)]
    if bool(result):
        return False
    return True
