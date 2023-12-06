import settings
from .db_functions import insert_products, update_products_check_title,\
    insert_links, update_links
from .extractors_helper import select_link_id_fields, db_close_log, insert_read_errors_procedure,\
    update_link_counter_aps, only_read_products_without_title, update_counter_not_turn_aps,\
    select_sites_fields_price_title_image, select_sites_fields_sitemap_href, check_crawl_type_parent_selector,\
    produce_title_price_message_out
from .helper_functions import _get_timestamp, _convert_persian_numbers
from .priority_check import check_if_its_turn, change_failed_priority, reset_priority
from .del_temp import clean_temp_folder
from crawl_price_name.external_call import digikala_url_price, torob_url_price, emalls_url_price,\
    torob_seller_product_title
from crawl_price_name.google_cache import gc_get_title_price_image
from crawl_price_name import general, custom
from sitemap_reader.sm_reader import auto_sitemap_reader
from sitemap_reader.url_parsers import _create_product_url_pattern, _normalize_domain
from sitemap_reader.functions import look_for_all_links
from logs.exception_logs import exception_line
from logs.extractor_logs import insert_price_logs
from flask_server.functions import connect_mysql
from urllib.parse import urlparse
import logging
import concurrent.futures
import csv
import pathlib
import validators




# * (START) Basic operations to get sitemap product links and crawl name and price from each link found in previous operation

def find_sitemap_products_href(site_id:int, connection:object=None, api_agent:str='selenium', driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, only_extract_all_links:int=settings.SITEMAP_ONLY_EXTRACT_ALL_LINKS) -> dict:
    """Query 'site_url' and extract data from its sitemaps\n
    NOTE: 'api_agent' argument tells if we should 'requests' or 'selenium' library
    NOTE: As a experimental effort, we delete the not needed variables after using them to free memory. It's not necessary free up memory but it might be useful"""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        result = dict()
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        # Find site_url, example_links, and sitemap based on site_id
        sites_fields_result = select_sites_fields_sitemap_href(site_id, is_inner_connection, connection, cursor)
        # If 'sites_fields_result' is a dict, it means getting sites row was not a success
        if isinstance(sites_fields_result, dict):
            return sites_fields_result
        site_url, example_links, site_sitemap = sites_fields_result
        # If 'site_url' is in 'IGNORE_SITE_URL_LIST' stop the operation:
        if site_url in settings.IGNORE_SITE_URL_LIST:
            message = f'\'{site_url}\' must be ignored'
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        # Check if should extract all links for 'bad' or 'none' sitemaps, or proceeds with read all the sitemaps
        if only_extract_all_links:
            if site_sitemap in ['none', 'bad']:
                # Extract product url pattern
                pattern = _create_product_url_pattern(example_links)
                if not pattern:
                    message = f'No product pattern found for \'{site_url}\''
                    logging.warning(message)
                links = set()
                links = look_for_all_links(url=f'http://{site_url}',
                                            seed_domain=site_url,
                                            product_url_pattern=pattern,
                                            show_links=True)
                # Insert links into tables
                i = 0
                for href in links:
                    # Check if current href has site_url in it. If not, don't insert-update that link into db
                    if site_url not in href:
                        continue
                    # First check if current links are in the 'links' table. If they are in the table, update the table otherwise insert new links into 'links' table
                    link_id = update_links(cursor=cursor, href=href, site_id=site_id, price=None)
                    # If there is no links to update, create new product then create new links
                    if not link_id:
                        product_id = insert_products(cursor=cursor, site_id=site_id)
                        link_id = insert_links(cursor, href, site_id, product_id)
                    # Commit every time a link is inserted or updated
                    connection.commit()
                    i += 1
                result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 1)
                return result
            # If sitemap field is not 'bad' or 'none' don't proceed the operation
            else:
                result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 1)
                return result
        # Proceeds with extracting product links from sitemaps
        logging.info('GOING TO READ SITEMAPS...')
        sitemap_reader_result = auto_sitemap_reader(url=site_url,
                                                    api_agent=api_agent,
                                                    example_links=example_links,
                                                    timeout=timeout)
        # If 'sitemap_reader_result' is str means there was an error in 'auto_sitemap_reader'
        if isinstance(sitemap_reader_result, str):
            message = f'sitemap reader for the {site_url} did not succeeded because: {sitemap_reader_result}'
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        logging.info('AFTER SITEMAP READ...')
        product_href_list = sitemap_reader_result[0]
        root_sitemap = sitemap_reader_result[1]
        # delete 'sitemap_reader_result_list' to release the memory
        del sitemap_reader_result
        # Update current 'site' row in the database with newly received 'root_sitemap'
        if root_sitemap and product_href_list:
            # ? Put root sitemap as sitemap field in the sites.sitemap field
            sql = f"""UPDATE sites SET 
            sitemap = '{root_sitemap}', updated_at = '{_get_timestamp()}' WHERE id = {int(site_id)}"""
            cursor.execute(sql)
            connection.commit()
        # ! Temporary: If sitemap found but there were no product in the 'product_href_list' insert 'bad' as sitemap field (If the last time sitemap worked fine, don't change the right value)
        if root_sitemap and not product_href_list:
            # Check current value of the sitemap field. If There is no value or value is 'none', update the sitemap field with 'bad'
            cursor.execute(f'SELECT sitemap FROM sites WHERE id = {site_id}')
            row = cursor.fetchone()
            sitemap_field = row[0]
            if not sitemap_field or sitemap_field == 'none':
                sql = f"""UPDATE sites SET 
                sitemap = 'bad', updated_at = '{_get_timestamp()}' WHERE id = {int(site_id)}"""
                cursor.execute(sql)
                connection.commit()
            message = f'No product link found in sitemaps for {site_url}'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 1)
            # If we decide to read all links in a website to get products, we should delete following line
            return result
        # ! Temporary: If no root_sitemap found, update sitemap with 'none' (If the last time sitemap worked fine, don't change the right value)
        if not root_sitemap:
            # Check current value of the sitemap field. If There is no value or value is 'bad', update the sitemap field with 'none'
            cursor.execute(f'SELECT sitemap FROM sites WHERE id = {site_id}')
            row = cursor.fetchone()
            sitemap_field = row[0]
            if not sitemap_field or sitemap_field == 'bad':
                sql = f"""UPDATE sites SET 
                sitemap = 'none', updated_at = '{_get_timestamp()}' WHERE id = {int(site_id)}"""
                cursor.execute(sql)
                connection.commit()
            message = f'No sitemap found for {site_url}'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            # If we decide to read all links in a website to get products, we should delete following line
            return result
        # Iterate over product links in the product_links_list and put them into 'prducts' and 'links' tables
        if product_href_list:
            product_links_list_len = len(product_href_list)
            logging.warning(f'Number of product links in {site_url}: {product_links_list_len}')
            for href in product_href_list:
                # Check if current href has site_url in it. If not, don't insert-update that link into db
                if site_url not in href:
                    continue
                # First check if current links are in the 'links' table. If they are in the table, update the table otherwise insert new links into 'links' table
                link_id = update_links(cursor=cursor, href=href, site_id=site_id, price=None)
                # If there is no links to update, create new product then create new links
                if not link_id:
                    product_id = insert_products(cursor=cursor, site_id=site_id)
                    link_id = insert_links(cursor, href, site_id, product_id)
                # Commit every time a link is inserted or updated
                connection.commit()
            # Close database connection after each request
            logging.info(f'OPERATION COMPLETED SUCCESSFULLY AND {len(product_href_list)} PRODUCT LINKS EXTRACTED FROM {site_url}')
            message = f'{product_links_list_len} links inserted-updated for {site_url} successfully'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 1)
            return result
        # If no products found in the sitemaps
        else:
            # Close database connection after each request
            message = f'no product found for this url: {site_url}'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            # close chrome web driver to keep ram and cpu under control (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
            # driver.close()
            return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_sitemap_products_href": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'error in getting data from server', 'data': -1})
        return result


def find_price_title(link_id:int, connection:object=None, api_agent:str='selenium', driver:object=None, save_image:bool=False, force_save_image:bool=False, timeout:int=settings.CHROME_DRIVER_TIMEOUT, _ONLY_FIND_TITLE:int=0) -> dict:
    """Get latest price based on 'links' table 'id' field. If 'get_title' is 'True' return both 'product title' and 'product price'\n
    NOTE: 'api_agent' argument tells if we should 'requests' or 'selenium' library
    NOTE: Price is either an available product value or -1."""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        result = dict()
        # Select 'links' table fields using 'link_id'
        link_fields_result = select_link_id_fields(cursor=cursor, link_id=link_id)
        # If link_fields_result is string it means there were errors in getting fields
        if isinstance(link_fields_result, str):
            result = db_close_log(is_inner_connection, connection, cursor, link_fields_result)
            return result
        href, site_id, product_id, priority, counter = link_fields_result
        # If _ONLY_FIND_TITLE is active, only read products without title
        if _ONLY_FIND_TITLE:
            result = only_read_products_without_title(is_inner_connection, connection, cursor, product_id)
            if result:
                return result
        # !!!!!!!!!!!!!! *** ONLY EXECUTED IN APSCHEDULER MODE - Formula to decide if we should proceed to get title and price from a webpage using "priority" and "counter" will be inserted here
        if settings.RUN_SCHEDULE:
            if not check_if_its_turn(counter=counter, priority=priority):
                # Update counter by 1 before cancel the program
                result = update_counter_not_turn_aps(is_inner_connection, connection, cursor, site_id, link_id, counter)
                return result
        # !!!!!!!!!!!!!!!!!!
        # Get 'crawler_type', 'parent_class', 'site_name', 'site_url', 'image_parent_selector', 'site_status', 'agent', 'title_selector', 'button_selector' from 'sites' table using 'site_id'
        site_fields_result = select_sites_fields_price_title_image(site_id, is_inner_connection, connection, cursor)
        # If site_fields_result is a dict, means no row found for the sites with provided site_id and should return the response to client
        if isinstance(site_fields_result, dict):
            return site_fields_result
        crawler_type, parent_class, site_name, site_url, image_parent_selector, site_status, agent, title_selector, button_selector = site_fields_result
        # Check crawler_type and parent_selector
        crawler_parent_problem = check_crawl_type_parent_selector(is_inner_connection, connection, cursor, site_id, link_id, site_url, crawler_type, parent_class, site_status)
        # If crawler_parent_problem is not None it means there is an error
        if crawler_parent_problem:
            return crawler_parent_problem
        product_data = ''
        # Crawl 'price' and 'title' from 'href'
        if crawler_type == 'general' and parent_class:
            if agent not in ['selenium', 'requests']:
                message = f'for {site_url} agent {agent} is not defined so ignore links with this site_id({site_id})'
                # Insert read_errors
                result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
                return result
            # Check if 'USE_GOOGLE_WEB_CACHE_PRICE_TITLE' flag is on, use google web cache to get product title and price to not get blocked by the site we are scraping
            if settings.USE_GOOGLE_WEB_CACHE_PRICE_TITLE and site_url in settings.GOOGLE_WEB_CACH_SITES:
                # Use 'requests' library to extract data product from google web cache
                if settings.USE_REQUESTS_GOOGLE_WEB_CHACHE:
                    agnt = 'requests'
                # Else use 'selenium' library to extract data product from google web cache
                else:
                    agnt = 'selenium'
                product_data = gc_get_title_price_image(parent=parent_class,
                                                        url=href,
                                                        api_agent=agnt,
                                                        site_name=site_name,
                                                        save_image=save_image,
                                                        force_save_image=force_save_image,
                                                        image_parent_selector=image_parent_selector,
                                                        title_selector=title_selector,
                                                        button_selector=button_selector,
                                                        site_id=site_id,
                                                        link_id=link_id,
                                                        timeout=timeout)
            # If product_data returned as str, it means there is no product data received yet and we must scrape the website directly and risk to get blocked
            if isinstance(product_data, str):
                product_data = general.get_title_price_image(parent=parent_class,
                                                            url=href,
                                                            # api_agent=api_agent,
                                                            api_agent=agent,
                                                            site_name=site_name,
                                                            save_image=save_image,
                                                            force_save_image=force_save_image,
                                                            image_parent_selector=image_parent_selector,
                                                            title_selector=title_selector,
                                                            button_selector=button_selector,
                                                            site_id=site_id,
                                                            link_id=link_id,
                                                            timeout=timeout)
        elif crawler_type == 'custom':
            product_data = custom.get_title_price_image(site_url=site_url,
                                                        href=href,
                                                        save_image=save_image,
                                                        force_save_image=force_save_image,
                                                        # driver=driver,
                                                        timeout=timeout)
        # Update links counter - *** ONLY EXECUTED IN APSCHEDULER MODE - 
        if settings.RUN_SCHEDULE:
            update_link_counter_aps(cursor, connection, counter, site_id, link_id)
        # If 'product_data' is 'None' execute following block (this won't happen but we should set it here for better practice)
        if not product_data:
            message = f'Cannot find the product in the url: {href}'
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        # If product_data is 'str' it means an error happened
        if isinstance(product_data, str):
            message = product_data
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        # If 'product_data' returned successfully, set variables for 'title', 'price', 'available', and 'product_image_url'
        product_title, product_price, product_is_available, product_image_url = product_data
        if not product_title:
            message = f'Cannot find product title for link_id({link_id}), because maybe the link is deleted, removed, is not a valid product link or for any reason the link will not open'
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        price = product_price if product_is_available else -1
        # Insert extracted data into database
        if price > -1:
            price = int(_convert_persian_numbers(str(price)))
        if product_title:
            product_title = _convert_persian_numbers(product_title)
        update_products_check_title(cursor=cursor,
                                    product_id=product_id,
                                    site_id=site_id,
                                    title=product_title,
                                    image_url=product_image_url)
        # Update 'links' table with new crawled 'price' and 'updated_at' fields (If current links row has 'product_id' empty, add product_id to the 'links' table row we want to update)
        update_links(cursor=cursor,
                    link_id=link_id,
                    href=href,
                    price=price,
                    site_id=site_id)
        # Insert new row into 'price_logs'
        insert_price_logs(cursor=cursor,
                        link_id=link_id,
                        price=price)
        # Update priority for links if price is -1 - *** ONLY EXECUTED IN APSCHEDULER MODE
        if settings.RUN_SCHEDULE:
            if price == -1:
                change_failed_priority(cursor=cursor, link_id=link_id, priority=priority)
        # Reset priority to 10 if price is not -1 (to have program faster, only reset priority if it currently is not 10)
        if price != -1:
            if priority != 10:
                reset_priority(cursor=cursor, link_id=link_id)
        # Produce result meassage before send the message as response
        result = produce_title_price_message_out(product_price, product_is_available, link_id, product_data)
        connection.commit()
        # close db connection to preserve resources
        if is_inner_connection:
            cursor.close()
            connection.close()
        # chrome webdriver to preserve resources (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
        # driver.close()
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_shcedule.extractors.find_price_title": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'server-side error', 'price': -1})
        return result

# * (START) Basic operations to get sitemap product links and crawl name and price from each link found in previous operation


def gc_find_price_title(link_id:int, connection:object=None, api_agent:str='selenium', driver:object=None, save_image:bool=False, force_save_image:bool=False, timeout:int=settings.CHROME_DRIVER_TIMEOUT, _ONLY_FIND_TITLE:int=0) -> dict:
    """Get latest price based on 'links' table 'id' field. If 'get_title' is 'True' return both 'product title' and 'product price' using google web cache\n
    NOTE: 'api_agent' argument tells if we should 'requests' or 'selenium' library
    NOTE: Price is either an available product value or -1."""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        result = dict()
        # Select 'links' table fields using 'link_id'
        link_fields_result = select_link_id_fields(cursor=cursor, link_id=link_id)
        # If link_fields_result is string it means there were errors in getting fields
        if isinstance(link_fields_result, str):
            result = db_close_log(is_inner_connection, connection, cursor, link_fields_result)
            return result
        href, site_id, product_id, priority, counter = link_fields_result
        # If _ONLY_FIND_TITLE is active, only read products without title
        if _ONLY_FIND_TITLE:
            result = only_read_products_without_title(is_inner_connection, connection, cursor, product_id)
            if result:
                return result
        # !!!!!!!!!!!!!! *** ONLY EXECUTED IN APSCHEDULER MODE - Formula to decide if we should proceed to get title and price from a webpage using "priority" and "counter" will be inserted here
        if settings.RUN_SCHEDULE:
            if not check_if_its_turn(counter=counter, priority=priority):
                # Update counter by 1 before cancel the program
                result = update_counter_not_turn_aps(is_inner_connection, connection, cursor, site_id, link_id, counter)
                return result
        # !!!!!!!!!!!!!!!!!!
        # Get 'crawler_type', 'parent_class', 'site_name', 'site_url', 'image_parent_selector', 'site_status', 'agent', 'title_selector', 'button_selector' from 'sites' table using 'site_id'
        site_fields_result = select_sites_fields_price_title_image(site_id, is_inner_connection, connection, cursor)
        # If site_fields_result is a dict, means no row found for the sites with provided site_id and should return the response to client
        if isinstance(site_fields_result, dict):
            return site_fields_result
        crawler_type, parent_class, site_name, site_url, image_parent_selector, site_status, agent, title_selector, button_selector = site_fields_result
        # Check crawler_type and parent_selector
        crawler_parent_problem = check_crawl_type_parent_selector(is_inner_connection, connection, cursor, site_id, link_id, site_url, crawler_type, parent_class, site_status)
        # If crawler_parent_problem is not None it means there is an error
        if crawler_parent_problem:
            return crawler_parent_problem
        # Crawl 'price' and 'title' from 'href'
        if crawler_type == 'general' and parent_class:
            product_data = ''
            product_data = gc_get_title_price_image(parent=parent_class,
                                                    url=href,
                                                    api_agent=api_agent,
                                                    site_name=site_name,
                                                    save_image=save_image,
                                                    force_save_image=force_save_image,
                                                    image_parent_selector=image_parent_selector,
                                                    title_selector=title_selector,
                                                    button_selector=button_selector,
                                                    site_id=site_id,
                                                    link_id=link_id,
                                                    timeout=timeout)
            # If product_data is 'str' it means an error happened
            if isinstance(product_data, str):
                message = product_data
                # Insert read_errors
                result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
                return result
        elif crawler_type == 'custom':
            product_data = custom.get_title_price_image(site_url=site_url,
                                                        href=href,
                                                        save_image=save_image,
                                                        force_save_image=force_save_image,
                                                        # driver=driver,
                                                        timeout=timeout)
        # Update links counter - *** ONLY EXECUTED IN APSCHEDULER MODE - 
        if settings.RUN_SCHEDULE:
            update_link_counter_aps(cursor, connection, counter, site_id, link_id)
        # If 'product_data' is 'None' execute following block (this won't happen but we should set it here for better practice)
        if not product_data:
            message = f'Cannot find the product in the url: {href}'
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        # If product_data is 'str' it means an error happened
        if isinstance(product_data, str):
            message = product_data
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        # If 'product_data' returns successfully, set variables for 'title', 'price', 'available', and 'product_image_url'
        product_title, product_price, product_is_available, product_image_url = product_data
        if not product_title:
            message = f'Cannot find product title for link_id({link_id}), because maybe the link is deleted, removed, is not a valid product link or for any reason the link will not open'
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
        price = product_price if product_is_available else -1
        # Insert extracted data into database
        if price > -1:
            price = int(_convert_persian_numbers(str(price)))
        if product_title:
            product_title = _convert_persian_numbers(product_title)
        update_products_check_title(cursor=cursor,
                                    product_id=product_id,
                                    site_id=site_id,
                                    title=product_title,
                                    image_url=product_image_url)
        # Update 'links' table with new crawled 'price' and 'updated_at' fields (If current links row has 'product_id' empty, add product_id to the 'links' table row we want to update)
        update_links(cursor=cursor,
                    link_id=link_id,
                    href=href,
                    price=price,
                    site_id=site_id)
        # Insert new row into 'price_logs'
        insert_price_logs(cursor=cursor,
                        link_id=link_id,
                        price=price)
        # Update priority for links if price is -1 - *** ONLY EXECUTED IN APSCHEDULER MODE
        if settings.RUN_SCHEDULE:
            if price == -1:
                change_failed_priority(cursor=cursor, link_id=link_id, priority=priority)
        # Reset priority to 10 if price is not -1 (to have program faster, only reset priority if it currently is not 10)
        if price != -1:
            if priority != 10:
                reset_priority(cursor=cursor, link_id=link_id)
        # Produce result meassage before send the message as response
        result = produce_title_price_message_out(product_price, product_is_available, link_id, product_data)
        connection.commit()
        # close db connection to preserve resources
        if is_inner_connection:
            cursor.close()
            connection.close()
        # chrome webdriver to preserve resources (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
        # driver.close()
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_shcedule.extractors.gc_find_price_title": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'server-side error', 'price': -1})
        return result





# ! Useful function to test if all product title and price and images for a particular site saved successfully
def read_site_price_title(site_id:int, connection:object=None, api_agent:str='selenium', driver:object=None, save_image:bool=False, force_save_image:bool=False, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Iterate throught all links and products for a particular site_id to get price, title and maybe image of all the products"""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        result = dict()
        sql = f"""SELECT id, href, product_id FROM links WHERE site_id = {site_id}"""
        cursor.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            if is_inner_connection:
                cursor.close()
                connection.close()
            message = f'could not find links with the site_id({site_id})'
            logging.warning(message)
            result.update({'status': 'error', 'message': message, 'data': -1})
            return result
        # Get 'crawler_type', 'parent_class', 'site_name', 'site_url', 'image_parent_selector', 'site_status', 'agent', 'title_selector', 'button_selector' from 'sites' table using 'site_id'
        site_fields_result = select_sites_fields_price_title_image(site_id, is_inner_connection, connection, cursor)
        # If site_fields_result is a dict, means no row found for the sites with provided site_id and should return the response to client
        if isinstance(site_fields_result, dict):
            return site_fields_result
        crawler_type, parent_class, site_name, site_url, image_parent_selector, site_status, agent, title_selector, button_selector = site_fields_result
        # Check crawler_type and parent_selector
        if crawler_type not in ['custom', 'general']:
            message = f'crawler_type \'{crawler_type}\' for site_url {site_url} is not defined'
            logging.warning(message)
            return result
        # Find if there are any error in 'crawler_type' or 'parent_class' fields
        if crawler_type == 'general' and not parent_class:
            message = f'\'parent_class\' not exist for the general crawler_type for a site with the site_id({site_id})'
            logging.warning(message)
            return result
        # Iterate every row 
        for row in rows:
            link_id, href, product_id = row[0], row[1], row[2]
            if not href or not link_id or not product_id:
                message = f'could not find \'href\' or \'link_id\' or \'product_id\' with this link_id({link_id})'
                result = db_close_log(message=message)
                continue
            # Crawl 'price' and 'title' from 'href'
            if crawler_type == 'general' and parent_class:
                product_data = general.get_title_price_image(parent=parent_class,
                                                            url=href,
                                                            # api_agent=api_agent,
                                                            api_agent=agent,
                                                            site_name=site_name,
                                                            save_image=save_image,
                                                            image_parent_selector=image_parent_selector,
                                                            title_selector=title_selector,
                                                            button_selector=button_selector,
                                                            site_id=site_id,
                                                            link_id=link_id,
                                                            force_save_image=force_save_image,
                                                            timeout=timeout)
                # If product_data is str then it means error happend in getting price and title of the product
                if isinstance(product_data, str):
                    message = product_data
                    # Insert read_errors
                    result = insert_read_errors_procedure(is_inner_connection=False, connection=connection, cursor=cursor, message=message, site_id=site_id, link_id=link_id)
                    continue
            elif crawler_type == 'custom':
                product_data = custom.get_title_price_image(site_url=site_url,
                                                            href=href,
                                                            site_id=site_id,
                                                            link_id=link_id,
                                                            save_image=save_image,
                                                            force_save_image=force_save_image,
                                                            # driver=driver,
                                                            timeout=timeout)
            if product_data is None:
                logging.info({'status': 'error', 'message': 'the url does not exist or it took to long for selenium or requests to load the product page', 'data': -1})
            else:
                # set variables for 'title', 'price', 'available', and 'product_image_url'
                product_title, product_price, product_is_available, product_image_url = product_data
                # print(product_data)
                if not product_title:
                    message = f'Cannot extract product, or cannot find product title, or the link is not a product link: {href}'
                    result.update({'status': 'error', 'message': f'could not find title for the link_id({link_id})', 'data': -1})
                    logging.warning(result)
                price = product_price if product_is_available else -1
                update_products_check_title(cursor=cursor,
                                            product_id=product_id,
                                            site_id=site_id,
                                            title=product_title,
                                            image_url=product_image_url)
                # Update 'links' table with new crawled 'price' and 'updated_at' fields (If current links row has 'product_id' empty, add product_id to the 'links' table row we want to update)
                update_links(cursor=cursor,
                            link_id=link_id,
                            href=href,
                            price=price,
                            site_id=site_id)
                # Insert new row into 'price_logs'
                insert_price_logs(cursor=cursor,
                                link_id=link_id,
                                price=price)
                connection.commit()
            # Produce result meassage before send the message as response
            result = produce_title_price_message_out(product_price, product_is_available, link_id, product_data)
            logging.info(f'result of single operation: {result}')
        # close db connection to preserve resources
        if is_inner_connection:
            cursor.close()
            connection.close()
        # chrome webdriver to preserve resources (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
        # driver.close()
        return {'status': 'ok', 'message': 'operation completed successfully', 'data': 1}
    except Exception as e:
        logging.error(f'Error in "extractor_shcedule.extractors.read_site_price_title": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'server-side error', 'price': -1})
        return result
# ! Useful function to test if all product title and price and images for a particular site saved successfully





# ! Useful function to test if general pattern useful to extract product price
def check_general_pattern(product_id:int=None, product_link:str=None, parent_selector:str=None, button_selector:str=None, image_selector:str=None, title_selector:str=None, save_image:bool=settings.SAVE_IMAGE, force_save_image:bool=settings.SAVE_IMAGE, connection:object=None, api_agent:str='selenium', timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Check if general pattern useful to extract price from a link"""
    try:
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        result = dict()
        crawler_type = 'general'
        # Check if 'product_id' is Not None
        if product_id:
            cursor.execute(f'SELECT id, site_id, href FROM links WHERE product_id = {int(product_id)}')
            row = cursor.fetchone()
            if not row:
                message = f'No link found in links table with product_id({product_id})'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            _link_id, site_id, href = row[0], row[1], row[2]
            cursor.execute(f'SELECT site_url, parent_class, crawler_type, image_parent_selector, button_selector, title_selector FROM sites WHERE id = {site_id}')
            row = cursor.fetchone()
            if not row:
                message = f'No site found with site_id({site_id})'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            site_url, parent_selector, crawler_type, image_parent_selector, button_selector, title_selector = row
            if site_url in settings.IGNORE_SITE_URL_LIST:
                message = f'\'{site_url}\' must be ignored'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            if crawler_type == 'general' and not parent_selector:
                message = f'\'{site_url}\' has no parent_selector'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            if crawler_type == 'custom':
                message = f'\'{site_url}\' crawler_type is custom'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
        # If no 'product_id' provided, use 'product_link' and 'parent_selector' provided by user
        else:
            if product_link and not parent_selector:
                message = 'no \'parent_selector\' provided'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            if not product_link:
                message = 'no \'product_link\' provided'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            href = product_link
            # Check if current href domain is already in the db
            site_url = _normalize_domain(href)
            cursor.execute(f"SELECT id, crawler_type FROM sites WHERE site_url = '{site_url}'")
            row = cursor.fetchone()
            if row:
                if row[1] == 'custom':
                    logging.warning(f'{site_url} is already registered in the sites as custom')
            image_parent_selector = image_selector
        # crawl href with general crawl function
        product_data = general.get_title_price_image(url=href,
                                                     api_agent=api_agent,
                                                    parent=parent_selector,
                                                    save_image=save_image,
                                                    force_save_image=force_save_image,
                                                    image_parent_selector=image_parent_selector,
                                                    title_selector=title_selector,
                                                    button_selector=button_selector,
                                                    # driver=driver,
                                                    timeout=timeout)
        # Check if there is an error in 'get_title_price_image'
        if isinstance(product_data, str):
            result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=product_data)
            return result
        # set variables for 'title', 'price', 'available', and 'product_image_url'
        product_title, product_price, product_is_available, product_image_url = product_data
        # print(product_data)
        if not product_title:
            message = f'Cannot extract product, or cannot find product title, or the link is not a product link: {href}'
            result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
            return result
        _price = product_price if product_is_available else -1
        # Every database has this problem with '"' and "'" and other special characters. Escape them to not raise any db error
        # ! FOR NOW IGNORE 'products_links' table
        if product_price > 0 and not product_is_available:
            result.update({'status': 'ok', 'message': f'price is found ({product_price}) but product is not available for the link: {href}', 'data': None})
        elif product_price == 0 and product_is_available:
            result.update({'status': 'ok', 'message': f'product is available but price not found for the link: {href}', 'data': None})
        elif product_price == -1 and not product_is_available:
            result.update({'status': 'ok', 'message': f'product is not available and price not found for the link: {href}', 'data': None})
        # If everything is ok, return following result
        else:
            result.update({'status': 'ok', 'message': f'successfully get product price and title for the link: {href}', 'data': product_data})
        # chrome webdriver to preserve resources (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
        # driver.close()
        if is_inner_connection:
            cursor.close()
            connection.close()
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_shcedule.extractors.check_general_pattern": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'server-side error', 'price': -1})
        return result
# ! Useful function to test if general pattern useful to extract product price


# ! Useful function to test if custom pattern for a product_id or a product_link
def check_custom_pattern(product_id:int=None, product_link:str=None, save_image:bool=settings.SAVE_IMAGE, force_save_image:bool=settings.SAVE_IMAGE, connection:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Check if custom pattern useful to extract price from a link"""
    try:
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        result = dict()
        crawler_type = 'custom'
        # Check if 'product_id' is Not None
        if product_id:
            cursor.execute(f'SELECT id, site_id, href FROM links WHERE product_id = {int(product_id)}')
            row = cursor.fetchone()
            if not row:
                message = f'No link found in links table with product_id({product_id})'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            _link_id, site_id, href = row[0], row[1], row[2]
            cursor.execute(f'SELECT site_url, crawler_type FROM sites WHERE id = {site_id}')
            row = cursor.fetchone()
            if not row:
                message = f'No site found with site_id({site_id})'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            site_url, crawler_type = row[0], row[1]
            if site_url in settings.IGNORE_SITE_URL_LIST:
                message = f'\'{site_url}\' must be ignored'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            if crawler_type == 'general':
                message = f'\'{site_url}\' crawler_type is general'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
        # If no product_id received, check if there is product with 'prodcut_link'
        else:
            if not product_link :
                message = 'no \'product_link\' provided'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            href = product_link
            site_url = _normalize_domain(href)
            # Check if site_url of current 'href' is already in the 'sites' table
            cursor.execute(f"SELECT id, crawler_type FROM sites WHERE site_url = '{site_url}'")
            row = cursor.fetchone()
            if not row:
                message = f'{site_url} is not registered in the sites table as a custom site'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
            site_id, crawler_type = row[0], row[1]
            if crawler_type == 'general':
                message = f'{site_url} is registered as a general site'
                result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
                return result
        # crawl href with custom crawl function
        product_data = custom.get_title_price_image(site_url=site_url,
                                                    href=href,
                                                    save_image=save_image,
                                                    force_save_image=force_save_image,
                                                    # driver=driver,
                                                    timeout=timeout)
        # If 'product_data' is str means we had a error
        if isinstance(product_data, str):
            result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=product_data)
            return result
        # set variables for 'title', 'price', 'available', and 'product_image_url'
        product_title, product_price, product_is_available, product_image_url = product_data
        # print(product_data)
        if not product_title:
            message = f'Cannot extract product, or cannot find product title, or the link is not a product link: {href}'
            result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=cursor, message=message)
            return result
        _price = product_price if product_is_available else -1
        # Every database has this problem with '"' and "'" and other special characters. Escape them to not raise any db error
        # ! FOR NOW IGNORE 'products_links' table
        if product_price > 0 and not product_is_available:
            result.update({'status': 'ok', 'message': f'price is found ({product_price}) but product is not available for the link: {href}', 'data': None})
        elif product_price == 0 and product_is_available:
            result.update({'status': 'ok', 'message': f'product is available but price not found for the link: {href}', 'data': None})
        elif product_price == -1 and not product_is_available:
            result.update({'status': 'ok', 'message': f'product is not available and price not found for the link: {href}', 'data': None})
        # If everything is ok, return following result
        else:
            result.update({'status': 'ok', 'message': f'successfully get product price and title for the link: {href}', 'data': product_data})
        # chrome webdriver to preserve resources (If we use 'driver.quit()' the program closes all drivers in other threads and it would be disastrous)
        # driver.close()
        if is_inner_connection:
            cursor.close()
            connection.close()
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_shcedule.extractors.check_custom_pattern": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'server-side error', 'price': -1})
        return result
# ! Useful function to test if custom pattern for a product_id or a product_link






# * (START) Using threads to get all sitemap product links and crawl title and price from every links found in the sitemap

# !!!! We have passed following function to apscheduler in 'extractor_schedule.schedule' module. So there is no reason to wake it anymore
def find_all_sites_sitemap_products_href(connection:object=None, api_agent:str='selenium', driver:object=None, arraysize:int=50, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Use threads to get all product links from all product related sitemaps in all sites"""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        # if not driver:
        #     driver = call_selenium_driver()
        # sql = """Select id FROM sites WHERE site_status = 'complete'"""
        sql = """Select id FROM sites"""
        cursor.execute(sql)
        while True:
            rows = cursor.fetchmany(arraysize)
            if rows:
                logging.info(f'site_id\'s to process: {rows}')
            # If read all the ids from table break the reading process
            if not rows:
                logging.info('No more site_id left')
                break
            # with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as EXECUTOR:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
                futures = [executor.submit(find_sitemap_products_href, api_agent=api_agent, timeout=timeout, site_id=row[0]) for row in rows]
                # To forcefully stop the thread (NOTE: could be very dangerous)
                # executor.shutdown(wait=False)
                # ! Above line does everything we want. Following block does not neccessary but tells us about the status of thread. So it's a good practice to have these
                for future in concurrent.futures.as_completed(futures):
                    try:
                        logging.info(f'>got {future.result()}')
                    except UnicodeEncodeError:
                        logging.info('EXECUTOR SUCCESSFULLY EXECUTED')
                # issue one task for each call to the function
                # for result in executor.map(find_sitemap_products_href, rows):
                #     print(f'>got {result}')
            logging.info('Tasks done')
        logging.info('Every sitemaps in the sites read and their links extracted')
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'success', 'message': 'operation completed', 'data': 1}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_all_sites_sitemap_products_href": {e.__str__()}')
        logging.warning(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in operation', 'data': -1}


# !!!! 'find_all_links_price_title_non_block' does following function but with more advanced method to limit the probability of getting block by other websites
def find_all_links_price_title(connection:object=None, api_agent:str='selenium', driver:object=None, save_image:bool=False, force_save_image:bool=False, arraysize:int=50, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Use threads to get price and title for all the links extracted from all completed sitemaps from all the sites"""
    # select_all_links_href(connection, arraysize)
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        sql = """Select id FROM links"""
        cursor.execute(sql)
        while True:
            rows = cursor.fetchmany(arraysize)
            if rows:
                logging.info(f'link_id\'s to process: {rows}')
            # If read all the ids from table break the reading process
            if not rows:
                logging.info('No more link_id left')
                break
            # ! Below block is the standard threadpoolexecutor we currently commented
            # with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
            with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
                futures = [executor.submit(find_price_title, api_agent=api_agent, save_image=save_image, force_save_image=force_save_image, timeout=timeout , link_id=row[0]) for row in rows]
                # ! Above line does everything we want. Following block does not neccessary but tells us about the status of thread. So it's a good practice to have is
                for future in concurrent.futures.as_completed(futures):
                    try:
                        logging.info(f'>got {future.result()}')
                    except UnicodeEncodeError:
                        logging.info('EXECUTOR SUCCESSFULLY EXECUTED')
                # issue one task for each call to the function
                # for result in executor.map(find_price_title, rows):
                #     print(f'>got {result}')
            # ! This block is used to test if we can forcefully stop the 
            # futures = []
            # executor = concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
            # for row in rows:
            #     future = executor.submit(find_price_title, save_image=save_image, timeout=timeout , link_id=row[0])
            #     futures.append(future)
                # executor.shutdown(wait=False)
            logging.info('Tasks done')
        logging.info('Every href in the links read updated their price and title')
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        if is_inner_connection:
            cursor.close()
            connection.close()
        return {'status': 'success', 'message': 'operation completed', 'data': 1}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_all_links_price_title": {e.__str__()}')
        logging.warning(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in operation', 'data': -1}



# ? Following function just do the same job as "find_all_links_price_title": read all the rows in 'links' table and try to
# ? to find price, title, and the main product image url but with a diffrent approach: it's try to read links without getting
# ? blocked by the target wesite. If 2 links have same 'site_id', this method read the second link later
# !!!! We have passed following function to apscheduler in 'extractor_schedule.schedule' module. So there is no reason to wake it anymore
def find_all_links_price_title_non_block(connection:object=None, api_agent:str='selenium', driver:object=None, library_agent:str='selenium', save_image:bool=False, force_save_image:bool=False, arraysize:int=50, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Use threads to get price and title for all the links extracted from all completed sitemaps from all the sites. It does this by
    not read 2 or more continous links by same 'site_id'"""
    try:
        if api_agent not in ['selenium', 'requests']:
            return {'status': 'error', 'message': f'api_agent must be \'selenium\' or \'requests\' but it is \'{api_agent}\''}
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        # if not driver:
        #     driver = call_selenium_driver()
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        print('Start ordering of link_ids...')
        _site_id_list = []
        _site_link_len = []
        site_dict = {}
        process_now = []
        cursor.execute('SELECT id FROM sites')
        rows = cursor.fetchall()
        for row in rows:
            _site_id_list.append(row[0])
            site_dict.update({row[0]: []})
        for site_id in _site_id_list:
            cursor.execute(f'SELECT id FROM links WHERE site_id = {site_id}')
            rows = cursor.fetchall()
            for row in rows:
                site_dict[site_id].append(row[0])
            _site_link_len.append(len(rows))
        i = 0
        while i < max(_site_link_len):
            for site_id, link_id_list in site_dict.items():
                try:
                    # with open('__file.txt', 'at') as f:
                    #     f.write(f"{site_id}: {link_id_list[i]}")
                    #     f.write('\n')
                    # print(site_id, ': ', link_id_list[i])
                    process_now.append(link_id_list[i])
                except IndexError:
                    continue
            i += 1
        del site_dict
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        print('GONNA START THREADPOOL')
        # METHOD 1
        # with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        #     futures = [executor.submit(find_price_title, save_image=save_image, timeout=timeout, link_id=link_id) for link_id in process_now]
        #     # ! Above line does everything we want. Following block does not neccessary but tells us about the status of thread. So it's a good practice to have is
        #     for future in concurrent.futures.as_completed(futures):
        #         logging.info(f'>got {future.result()}')
        # print('APSCHEDULER STARTED THREADPOOL')
        # issue one task for each call to the function
        # for result in executor.map(find_price_title, rows):
        #     print(f'>got {result}')
        # After processing all rows in 'process_now' list, empty this list and go the next 50 links
        # METHOD 2
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
        futures = []
        for link_id in process_now:
            # future = executor.submit(find_price_title, save_image=save_image, force_save_image=force_save_image, timeout=timeout, link_id=link_id, connection=connection)
            future = executor.submit(find_price_title, api_agent=api_agent, save_image=save_image, force_save_image=force_save_image, timeout=timeout, link_id=link_id)
            futures.append(future)
        for f in concurrent.futures.as_completed(futures):
            try:
                print(f'>RESULT: {f.result()}')
            except UnicodeEncodeError:
                print('EXECUTOR SUCCESSFULLY EXECUTED')
        # END OF METHODS
        logging.info('Tasks done')
        # del process_now
        logging.info('Every href in the links read updated their price and title')
        # if is_inner_connection:
        #     cursor.close()
        #     connection.close()
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        return {'status': 'success', 'message': 'operation completed', 'data': 1}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_all_links_price_title_non_block": {e.__str__()}')
        logging.warning(exception_line())
        # Check if connection is still intact
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in operation', 'data': -1}

# * (END) Using threads to get all sitemap product links and crawl title and price from every links found in the sitemap





# ???? (START) Torob, Emalls, and Digikala (TED) extractors

def find_TED_url_price(ted:str, product_id:int=None, product_name:str=None, connection:object=None, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.DIGIKALA_IMPLICIT_WAIT) -> dict:
    """Find Torob, Emalls, and Digikala (TED) url, price, and image for a product with id 'product_id' or product name 'product_name'. 'ted' must be one of these: ['digikala.com', 'torob.com', 'emalls.ir']. Returns a dict\n
    NOTE: if received 'product_id', first try to find its title from 'products' table and ignore product_name. But if no 'product_id' received, then use 'product_name' if received from client."""
    try:
        if ted not in ['digikala.com', 'torob.com', 'emalls.ir']:
            message = f'\'{ted}\' must be one of these: \'digikala\', \'torob\', \'emalls\' but \'{ted}\' is unacceptable'
            logging.warning(message)
            return {'status': 'error', 'message': message, 'data': -1}
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        # Check if 'product_id' sent by client, use it to extract product title from 'products' table
        _title = None
        if product_id:
            cursor.execute(f'SELECT title FROM products WHERE id = {product_id}')
            row = cursor.fetchone()
            if not row:
                message = f'No product found with the id({product_id})'
                result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
                return result
            _title = row[0]
        # If no title found with 'product_id', set title as 'product_name' if received
        if not _title and product_name:
            _title = product_name
        if not _title:
            message = f'No product found with the id({product_id}) or product_name({product_name})'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            return {'status': 'ok', 'message': message, 'data': 0}
        # Get ted site_id
        cursor.execute(f"SELECT id FROM sites WHERE site_url = '{ted}'")
        row = cursor.fetchone()
        if not row:
            message = f'{ted} is not registered in sites table'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            return result
        ted_site_id = row[0]
        ted_product_data = None
        # Get product data for TED based on 'ted' value
        if ted == 'digikala.com':
            ted_product_data = digikala_url_price(product_name=_title)
        elif ted == 'torob.com':
            ted_product_data = torob_url_price(product_name=_title)
        elif ted == 'emalls.ir':
            ted_product_data = emalls_url_price(product_name=_title)
        # If 'ted_product_data' is a list, means it found the data well
        if isinstance(ted_product_data, list):
            product_href = ted_product_data[0]
            product_title = ted_product_data[1]
            product_price = ted_product_data[2]
            product_image_url = ted_product_data[3]
            # Normalize title and price with converting number from persian to english
            product_title = _convert_persian_numbers(product_title)
            product_price = int(_convert_persian_numbers(str(product_price)))
            # Insert or update founded product in the database
            # Check if current product from ted is already registered in the 'links' table with founded href. Check href both with '/' and without '/' in the end of href
            _ted_link_id = None
            if product_href.endswith('/'):
                alternate_product_href = product_href[:-1]
            else:
                alternate_product_href = product_href + '/'
            # Update current links if it already exists in the database, try to update links and products
            cursor.execute(f"SELECT id, product_id FROM links WHERE site_id = {ted_site_id} AND href = '{product_href}'")
            row = cursor.fetchone()
            # If product href found in the 'links' table, update the product with extracted price
            if row:
                logging.info(f'{ted} link updated')
                _ted_link_id = row[0]
                update_links(cursor=cursor,
                             href=product_href,
                             link_id=_ted_link_id,
                             site_id=ted_site_id,
                             price=product_price)
            # If no product found with product_href, try alternate_href
            else:
                cursor.execute(f"SELECT id, product_id FROM links WHERE site_id = {ted_site_id} AND href = '{alternate_product_href}'")
                row = cursor.fetchone()
                if row:
                    logging.info(f'{ted} link updated')
                    _ted_link_id = update_links(cursor=cursor,
                                                href=alternate_product_href,
                                                link_id=_ted_link_id,
                                                site_id=ted_site_id,
                                                price=product_price)
            # Update 'products' if current_href exists in the 'links' table
            try:
                _ted_product_id = row[1]
                update_products_check_title(cursor=cursor,
                                            product_id=_ted_product_id,
                                            site_id=ted_site_id,
                                            title=product_title,
                                            image_url=product_image_url,
                                            )
            except (IndexError, TypeError):
                pass
            # If no product found with current href and alternate_href, insert new product and link into database
            if not _ted_link_id:
                logging.info(f'{ted} link created')
                _ted_product_id = insert_products(cursor=cursor,
                                                    site_id=ted_site_id,
                                                    title=product_title,
                                                    image_url=product_image_url
                )
                _ted_link_id = insert_links(cursor=cursor,
                                            href=product_href,
                                            site_id=ted_site_id,
                                            product_id=_ted_product_id,
                                            price=product_price)
            # Insert new row into 'price_logs'
            insert_price_logs(cursor=cursor,
                                link_id=_ted_link_id,
                                price=product_price)
            connection.commit()
            message = f'found product with price({product_price} Toman) in {ted} for {_title}'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', {'link_id': _ted_link_id})
            return result
        # If result equals to 0 it means we did not find needed data
        if ted_product_data == 0:
            message = f'data not found in \'{ted}_url_price\''
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        # If result equals to -1 it means there was a error in the "ted_url_price"
        if ted_product_data == -1:
            message = f'Error in \'{ted}_url_price\''
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_TED_url_price": {e.__str__()}')
        logging.warning(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in server', 'data': e.__str__()}



def find_torob_seller_product_title(product_name:str, make:bool=False, connection:object=None, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT, sleep_time:int=settings.TOROB_IMPLICIT_WAIT) -> dict:
    """Return other sellers product_title for the particular 'product_name' in torob. return dictionary\n
    NOTE: To insert-update a product, should receive 'make' as a true field."""
    try:
        data = None
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        sellers_product_result = torob_seller_product_title(product_name=product_name,
                                                            find_more_sellers=True,
                                                            timeout=timeout,
                                                            sleep_time=sleep_time)
        # print(sellers_product_result)
        # If 'sellers_product_result' is a list, it was succeeded to return wanted titles and other data about the product
        if isinstance(sellers_product_result, list):
            other_sellers_titles = sellers_product_result[0]
            href = sellers_product_result[1]
            title = sellers_product_result[2]
            price = sellers_product_result[3]
            image_url = sellers_product_result[4]
            if make:
                # Find torob site_id
                cursor.execute("SELECT id FROM sites WHERE site_url = 'torob.com'")
                row = cursor.fetchone()
                if row:
                    site_id = row[0]
                    cursor.execute(f"SELECT id, product_id FROM links WHERE site_id = {site_id} AND href = '{href}'")
                    row = cursor.fetchone()
                    # product already is in the database and must be updated 
                    if row:
                        link_id, product_id = row[0], row[1]
                        update_links(cursor=cursor,
                                     href=href,
                                     site_id=site_id,
                                     link_id=link_id,
                                     price=price)
                        update_products_check_title(cursor=cursor,
                                                    product_id=product_id,
                                                    site_id=site_id,
                                                    title=title,
                                                    image_url=image_url)
                        insert_price_logs(cursor=cursor,
                                          link_id=link_id,
                                          price=price)
                        message = f'successfully found other sellers title for \'{product_name}\' and product updated'
                    # Product is not in the database and must be inserted
                    else:
                        product_id = insert_products(cursor=cursor,
                                                    site_id=site_id,
                                                    title=title,
                                                    image_url=image_url)
                        link_id = insert_links(cursor=cursor,
                                               href=href,
                                               site_id=site_id,
                                               product_id=product_id,
                                               price=price)
                        insert_price_logs(cursor=cursor,
                                          link_id=link_id,
                                          price=price)
                        message = f'successfully found other sellers title for \'{product_name}\' and a new product inserted'
                    connection.commit()
                else:
                    message = f'successfully found other sellers title for \'{product_name}\' but did not found \'torob.com\' in \'sites\' table'
            else:
                message = f'successfully found other sellers title for \'{product_name}\' but database did not updated. To insert-update product, should send \'make\' as \'true\' in the form before send request to server'
            data = {'other-seller-titles': other_sellers_titles, 'number-of-sellers': len(other_sellers_titles), 'href': href, 'title': title, 'price': price}
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', data)
            return result
        if is_inner_connection:
            cursor.close()
            connection.close()
        if sellers_product_result is None:
            return {'status': 'ok', 'message': 'selenium did not created', 'data': None}
        if sellers_product_result == 0:
            return {'status': 'error', 'message': f'product with the name {product_name} not found', 'data': None}
        if sellers_product_result == -1:
            return {'status': 'error', 'message': 'error in the \'torob_seller_product_title\'', 'data': None}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.get_torob_seller_product_title": {e.__str__()}')
        logging.warning(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in the server', 'data': None}

# ???? (END) Torob, Emalls, and Digikala (TED) extractors





# * Function to extract all links from a website

def extract_all_site_links(site_id:int=None, site_url:str=None, connection:object=None, driver:object=None, timeout:int=settings.CHROME_DRIVER_TIMEOUT) -> dict:
    """Crawl through a website and extract all links from the website. Return dict"""
    try:
        is_inner_connection = False
        if not connection:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        else:
            cursor = connection.cursor()
        if site_id:
            # Find site_url, example_links, and sitemap based on site_id
            sites_fields_result = select_sites_fields_sitemap_href(site_id, is_inner_connection, connection, cursor)
            # If 'sites_fields_result' is a dict, it means getting sites row was not a success
            if isinstance(sites_fields_result, dict):
                return sites_fields_result
            site_url, example_links, site_sitemap = sites_fields_result
            # If 'site_url' is in 'IGNORE_SITE_URL_LIST' stop the operation:
            if site_url in settings.IGNORE_SITE_URL_LIST:
                message = f'\'{site_url}\' must be ignored'
                logging.warning(message)
            # Extract product url pattern
            pattern = _create_product_url_pattern(example_links)
            if not pattern:
                message = f'No product pattern found for \'{site_url}\''
                logging.warning(message)
            if not validators.domain(site_url):
                message = f'\'{site_url}\' is not a valid domain name'
                result = db_close_log(is_inner_connection, connection, cursor, message)
                return result
            url = 'http://' + site_url
            seed_domain = site_url
            product_url_pattern_scheme='http'
        # If no site_id provided, look for all links in site url
        elif not site_id and site_url:
            url = site_url
            if not site_url.startswith('http'):
                url = 'http://' + site_url
            seed_domain = urlparse(site_url).netloc.replace('www.', '')
            pattern = None
            product_url_pattern_scheme = None
        links = set()
        links = look_for_all_links(url=url,
                                    seed_domain=seed_domain,
                                    product_url_pattern=pattern,
                                    product_url_pattern_scheme=product_url_pattern_scheme)
        message = f'{len(links)} links crawled from "{site_url}"'
        result = db_close_log(is_inner_connection, connection, cursor, message)
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.extract_all_site_links": {e.__str__()}')
        logging.warning(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        return {'status': 'error', 'message': 'error in the server', 'data': None}




# * Functions to extract product link patterns from site_example in site_url

def find_product_pattern(site_id:int, connection:object=None) -> dict:
    """Find product pattern in any site using site_id and example_links"""
    result = dict()
    try:
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        # Find site_url, example_links, and sitemap based on site_id
        sites_fields_result = select_sites_fields_sitemap_href(site_id, is_inner_connection, connection, cursor)
        # If 'sites_fields_result' is a dict, it means getting sites row was not a success
        if isinstance(sites_fields_result, dict):
            return sites_fields_result
        site_url, example_links, site_sitemap = sites_fields_result
        # If 'site_url' is in 'IGNORE_SITE_URL_LIST' stop the operation:
        if site_url in settings.IGNORE_SITE_URL_LIST:
            message = f'\'{site_url}\' must be ignored'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            return result
        # Extract product url pattern
        pattern = _create_product_url_pattern(example_links)
        if not pattern:
            message = f'No product pattern found for \'{site_url}\''
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            return result
        message = f'pattern for \'{site_url}\': \'{pattern}\''
        result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', {'pattern': pattern})
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_product_pattern": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'error in getting data from server', 'data': -1})
        return result


def find_product_pattern_all(connection:object=None) -> dict:
    try:
        result = {}
        is_inner_connection = False
        if not connection:
            connection = connect_mysql(**{'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT})
            cursor = connection.cursor(buffered=True)
            is_inner_connection = True
        # ! flask_mysqldb connector cursor does not have 'buffered' argumenet. So if flask made the db connector, don't set this argument
        else:
            cursor = connection.cursor()
        # Find site_url and example_links for all sites
        cursor.execute('SELECT id, site_url, example_links FROM sites')
        rows = cursor.fetchall()
        if not rows:
            # Close database connection after each request
            message = 'Did not found any site'
            result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
            return result
        # Write received pattern into a csv file
        with open('url_patterns.csv', 'w', newline='') as file:
            pattern_list = []
            writer = csv.writer(file)
            fields = ['site_id', 'site_url', 'product_pattern']
            writer.writerow(fields)
            for row in rows:
                # If site_url is in ignore_url_list hop into the next iterable
                if row[1] in settings.IGNORE_SITE_URL_LIST:
                    logging.info(f'Ignore {row[1]}')
                    continue
                # Some sites may not have example_links then we replace 'N/A' for the product_pattern
                if row[2]:
                    writer.writerow([row[0], row[1], _create_product_url_pattern(row[2])])
                    pattern_list.append({'site_id': row[0], 'site_url': row[1], 'pattern': _create_product_url_pattern(row[2])})
                else:
                    writer.writerow([row[0], row[1], 'N/A'])
                    pattern_list.append({'site_id': row[0], 'site_url': row[1], 'pattern': 'N/A'})
        message = 'operation done successfully'
        url_pattern_path = str(pathlib.Path().resolve())
        src = f'{url_pattern_path}/url_patterns.csv'
        if is_inner_connection:
            cursor.close()
            connection.close()
        result.update({'status': 'ok', 'message': message, 'data': pattern_list, 'file': src})
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractors.find_product_pattern_all": {e.__str__()}')
        logging.warn(exception_line())
        try:
            if is_inner_connection:
                cursor.close()
                connection.close()
        except Exception:
            pass
        result.update({'status': 'error', 'message': 'error in getting data from server', 'data': -1})
        return result
