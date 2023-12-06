"""
NOTE: This module only works when user choose to NOT run the apscheduler
In these flask apis, returned response is a python dictionary to be converted to JSON object.
response is a 3-key dictionary:
*
first key is 'status' that accept only 2 answers: "ok" and "error"
first key --> 'status': "ok" or "error"
*
second key is 'message' to send consumer any messages needed to hear
second key --> 'message': "any string"
*
third key is '<data name>' that is the data must be send to consumer. It can be empty or any other JSONable data structure
third key --> '<data name>': "any JSONable data structure"
"""
from flask import Flask, request, jsonify
import settings
import logging
from extractor_schedule import extractors
from logs.exception_logs import exception_line


try:
    app = Flask(__name__)
except Exception as e:
    logging.critical('ERROR IN CONNECTING TO DATABASE IN FLASK SERVER: ', e.__str__())
    logging.warning('STOP ALL THE FURTHER PROCESS!')
    logging.warn(exception_line())
    exit()



# * To test if server is working

@app.route('/', methods=['GET', 'POST'])
def index():
    """Index page to show server is working"""
    if request.method == 'GET':
        return '<h1 style="text-align: center;">Welcome. Server work just fine!</h1>'
    elif request.method == 'POST':
        return jsonify({'status': 'ok', 'message': 'server is working!'})



# ***************************************************************************************************************
# ***************************************************************************************************************
# ************************************************  ALL THE FOLLOWING APIs WRITTEN TO EXECUTED BY SELENIUM *****************************



# * (START) Base flask operations to get sitemap product links and crawl title and price from every links found in the sitemap

@app.route('/find-sitemap-hrefs', methods=['POST'])
def find_sitemap_hrefs():
    """Receive a 'site_id' from 'sites' table then find its 'sitemap' and product 'href' then insert or update the data into tables"""
    if request.method == 'POST':
        site_id = request.form.get('site_id', None)
        if site_id:
            sp_result = extractors.find_sitemap_products_href(site_id=int(site_id))
        if not site_id:
            return jsonify({'status': 'error', 'message': 'No \'site_id\' received', 'data': None})
        return jsonify(sp_result)



@app.route('/find-price-title', methods=['POST'])
def find_price_title():
    """Receive a 'link_id' and returns its title and price. 'link_id' is a field from 'links' table"""
    if request.method == 'POST':
        link_id = request.form.get('link_id', None)
        if link_id:
            price_title_data = extractors.find_price_title(link_id=int(link_id), save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not link_id:
            return jsonify({'status': 'error', 'message': 'No \'link_id\' received', 'data': None})
        return jsonify(price_title_data)

# * (END) Base flask operations to get sitemap product links and crawl title and price from every links found in the sitemap



@app.route('/gc-find-price-title', methods=['POST'])
def gc_find_price_title():
    """Receive a 'link_id' and returns its title and price using Google web cache. 'link_id' is a field from 'links' table"""
    if request.method == 'POST':
        link_id = request.form.get('link_id', None)
        if link_id:
            price_title_data = extractors.gc_find_price_title(link_id=int(link_id), save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not link_id:
            return jsonify({'status': 'error', 'message': 'No \'link_id\' received', 'data': None})
        return jsonify(price_title_data)



# ! These routes don't be used in any other function. But it is useful to get price and title of all the products of a particular site
@app.route('/read_site_price_title', methods=['POST'])
def read_site_price_title():
    """Receive a site_id and find all product price and title of the site"""
    if request.method == 'POST':
        site_id = request.form.get('site_id', None)
        if site_id:
            price_title_data = extractors.read_site_price_title(site_id=int(site_id), save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not site_id:
            return jsonify({'status': 'error', 'message': 'No \'site_id\' received', 'data': None})
        return jsonify(price_title_data)





# ? (START) Using threads to get all sitemap product links and crawl title and price from every links found in the sitemap

@app.route('/find-sitemap-hrefs-all', methods=['POST'])
def find_sitemap_hrefs_all():
    """Try to read all the rows in 'sites' table and find all the product links in the siteamps"""
    if request.method == 'POST':
        sp_result = extractors.find_all_sites_sitemap_products_href()
        return jsonify(sp_result)


@app.route('/find-price-title-all', methods=['POST'])
def find_price_title_all():
    """Try to read all the rows in 'links' table and find price, title, and image of the product"""
    if request.method == 'POST':
        price_title_data = extractors.find_all_links_price_title(save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        return jsonify(price_title_data)


@app.route('/find-price-title-all-non-block', methods=['POST'])
def find_price_title_all_non_block():
    """Try to read all the rows in 'links' table and find price, title, and image of the product with non-blockable approach"""
    if request.method == 'POST':
        price_title_data = extractors.find_all_links_price_title_non_block(save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        return jsonify(price_title_data)

# ? (END) Using threads to get all sitemap product links and crawl title and price from every links found in the sitemap





# ????? (START) FIND DIGIKALA, TOROB, AND EMALLS FUNCTIONS ??????

@app.route('/find-<ted>-product-price', methods=['POST'])
def find_emalls_product_price(ted:str):
    """Receive a 'product_id' or 'product_name' -either one- and return its Torob, Emalls, Digikala (TED) url, price, and image"""
    if request.method == 'POST':
        if ted == 'digikala':
            ted = 'digikala.com'
        if ted == 'torob':
            ted = 'torob.com'
        if ted == 'emalls':
            ted = 'emalls.ir'
        product_id = request.form.get('product_id', None)
        product_name = request.form.get('product_name', None)
        if not product_id and not product_name:
            return jsonify({'status': 'error', 'message': 'atleast the api should receive either \'product_id\' or \'product_name\' '})
        if product_id or product_name:
            result = extractors.find_TED_url_price(ted=ted, product_id=product_id, product_name=product_name)
        return jsonify(result)



@app.route('/find-torob-seller-product-title', methods=['POST'])
def find_torob_seller_product_title():
    """Receive a product_title and return product titles by other sellers in torob. Must receive 'make' from client to insert-update received product name into database"""
    if request.method == 'POST':
        product_name = request.form.get('product_name', None)
        make = request.form.get('make', None)
        if make:
            if make is not False or make != 'null':
                make = True
        if product_name:
            result = extractors.find_torob_seller_product_title(product_name, make)
        if not product_name:
            return jsonify({'status': 'error', 'message': 'no \'product_name\' received', 'data': None})
        return jsonify(result)

# ????? (END) FIND DIGIKALA, TOROB, AND EMALLS FUNCTIONS ??????





@app.route('/extract_all_site_links', methods=['POST'])
def extract_all_site_links():
    """Extract all links from a site provided with site_id or site_url"""
    site_id = request.form.get('site_id', None)
    site_url = request.form.get('site_url', None)
    if not (site_id or site_url):
        return jsonify({'status': 'ok', 'message': 'No \'site_id\' or \'site_url\' received'})
    if site_id:
        site_id = int(site_id)
    result = extractors.extract_all_site_links(site_id=site_id, site_url=site_url)
    return jsonify(result)



@app.route('/product-url-pattern', methods=['POST'])
def find_product_pattern():
    """Find product url pattern provided by site_id"""
    site_id = request.form.get('site_id', None)
    if site_id:
        result = extractors.find_product_pattern(site_id=int(site_id))
    if not site_id:
        return jsonify({'status': 'error', 'message': 'No \'site_id\' received', 'data': None})
    return jsonify(result)



@app.route('/product-url-pattern-all', methods=['POST'])
def find_product_pattern_all():
    """Find product url pattern for all sites"""
    result = extractors.find_product_pattern_all()
    return jsonify(result)



@app.route('/check-general-pattern', methods=['POST'])
def check_general_pattern():
    """Check general pattern on a website with a parent selector. If received a 'product_id', use its 'site_id' foreign key. else it should accept a 'product_link' and a 'parent_selector' in a form"""
    product_id = request.form.get('product_id', None)
    product_link = request.form.get('product_link', None)
    parent_class = request.form.get('parent_class', None)
    button_selector = request.form.get('button_selector', None)
    image_selector = request.form.get('image_selector', None)
    title_selector = request.form.get('title_selector', None)
    if not (product_id or product_link or parent_class):
        return jsonify({'status': 'ok', 'message': 'not recieved \'product_id\', or \'product_link\' and \'parent_class\'', 'data': 0})
    result = extractors.check_general_pattern(product_id=product_id, product_link=product_link, parent_selector=parent_class, button_selector=button_selector, image_selector=image_selector, title_selector=title_selector)
    return jsonify(result)



@app.route('/check-custom-pattern', methods=['POST'])
def check_custom_pattern():
    """Check custom pattern on a website. If received a 'product_id', use its 'site_id' foreign key. else it should accept a 'product_link' and check if it's a custom link"""
    product_id = request.form.get('product_id', None)
    product_link = request.form.get('product_link', None)
    if not (product_id or product_link):
        return jsonify({'status': 'ok', 'message': 'not recieved \'product_id\', or \'product_link\'', 'data': 0})
    result = extractors.check_custom_pattern(product_id=product_id, product_link=product_link)
    return jsonify(result)





# *************************************************************************************************************************
# *************************************************************************************************************************
# *************************************************************************************************************************
# *************************************************************************************************************************
# *************************************************************************************************************************
# *************************************************************************************************************************




# *************************************************************************************************************************
# *************************************************************************************************************************
# ************************************************  ALL THE FOLLOWING APIs WRITTEN TO EXECUTED BY REQUESTS LIBRARY *****************************


@app.route('/rfind-sitemap-hrefs', methods=['POST'])
def rfind_sitemap_hrefs():
    """Receive a 'site_id' from 'sites' table then find its 'sitemap' and product 'href' then insert or update the data into tables USING REQUESTS"""
    if request.method == 'POST':
        site_id = request.form.get('site_id', None)
        if site_id:
            sp_result = extractors.find_sitemap_products_href(site_id=int(site_id), api_agent='requests')
        if not site_id:
            return jsonify({'status': 'error', 'message': 'No \'site_id\' received', 'data': None})
        return jsonify(sp_result)



@app.route('/rfind-price-title', methods=['POST'])
def rfind_price_title():
    """Receive a 'link_id' and returns its title and price USING REQUESTS. 'link_id' is a field from 'links' table"""
    if request.method == 'POST':
        link_id = request.form.get('link_id', None)
        if link_id:
            price_title_data = extractors.find_price_title(link_id=int(link_id), api_agent='requests', save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not link_id:
            return jsonify({'status': 'error', 'message': 'No \'link_id\' received', 'data': None})
        return jsonify(price_title_data)



@app.route('/rread_site_price_title', methods=['POST'])
def rread_site_price_title():
    """Receive a site_id and find all product price and title of the site USING REQUESTS"""
    if request.method == 'POST':
        site_id = request.form.get('site_id', None)
        if site_id:
            price_title_data = extractors.read_site_price_title(site_id=int(site_id), api_agent='requests', save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not site_id:
            return jsonify({'status': 'error', 'message': 'No \'site_id\' received', 'data': None})
        return jsonify(price_title_data)



@app.route('/rfind-sitemap-hrefs-all', methods=['POST'])
def rfind_sitemap_hrefs_all():
    """Try to read all the rows in 'sites' table and find all the product links in the siteamps USING REQUESTS"""
    if request.method == 'POST':
        sp_result = extractors.find_all_sites_sitemap_products_href(api_agent='requests')
        return jsonify(sp_result)



@app.route('/rfind-price-title-all', methods=['POST'])
def rfind_price_title_all():
    """Try to read all the rows in 'links' table and find price, title, and image of the product USING REQUESTS"""
    if request.method == 'POST':
        price_title_data = extractors.find_all_links_price_title(api_agent='requests', save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        return jsonify(price_title_data)



@app.route('/rfind-price-title-all-non-block', methods=['POST'])
def rfind_price_title_all_non_block():
    """Try to read all the rows in 'links' table and find price, title, and image of the product with non-blockable approach USING REQUESTS"""
    if request.method == 'POST':
        price_title_data = extractors.find_all_links_price_title_non_block(api_agent='requests', save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        return jsonify(price_title_data)



@app.route('/rgc-find-price-title', methods=['POST'])
def rgc_find_price_title():
    """Receive a 'link_id' and returns its title and price USING REQUESTS and Google web cache. 'link_id' is a field from 'links' table"""
    if request.method == 'POST':
        link_id = request.form.get('link_id', None)
        if link_id:
            price_title_data = extractors.gc_find_price_title(link_id=int(link_id), api_agent='requests', save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE)
        if not link_id:
            return jsonify({'status': 'error', 'message': 'No \'link_id\' received', 'data': None})
        return jsonify(price_title_data)



@app.route('/rcheck-general-pattern', methods=['POST'])
def rcheck_general_pattern():
    """Check general pattern on a website with a parent selector USING REQUESTS LIBRARY. If received a 'product_id', use its 'site_id' foreign key. else it should accept a 'product_link' and a 'parent_selector' in a form"""
    product_id = request.form.get('product_id', None)
    product_link = request.form.get('product_link', None)
    parent_class = request.form.get('parent_class', None)
    button_selector = request.form.get('button_selector', None)
    image_selector = request.form.get('image_selector', None)
    title_selector = request.form.get('title_selector', None)
    if not (product_id or product_link or parent_class):
        return jsonify({'status': 'ok', 'message': 'not recieved \'product_id\', or \'product_link\' and \'parent_class\'', 'data': 0})
    result = extractors.check_general_pattern(api_agent='requests', product_id=product_id, product_link=product_link, parent_selector=parent_class, button_selector=button_selector, image_selector=image_selector, title_selector=title_selector)
    return jsonify(result)
