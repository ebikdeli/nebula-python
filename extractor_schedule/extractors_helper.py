"""This module holds functions that made up extractors module and make the module more consise"""
import settings
from logs.exception_logs import exception_line
from logs.read_errors_logs import insert_read_errors
from .helper_functions import _get_timestamp
import logging




def db_close_log(is_inner_connection:bool=False, connection:object=None, cursor:object=None, message:str='', status:str='error', data:dict=-1, show_logging:int=True) -> dict:
    """Close database and log the message"""
    try:
        if is_inner_connection:
            cursor.close()
            connection.close()
        if show_logging:
            logging.warning(message)
        return {'status': status, 'message': message, 'data': data}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.quit_function_db": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def insert_read_errors_procedure(is_inner_connection:bool=False, connection:object=None, cursor:object=None, message:str='', status:str='error', data:dict=-1, site_id:int=None, link_id:int=None) -> dict:
    """Execute insert_read_errors and db_close_log in one line"""
    try:
        insert_read_errors(cursor=cursor, site_id=site_id, link_id=link_id, title=message)
        connection.commit()
        result = db_close_log(is_inner_connection=is_inner_connection, connection=connection, cursor=connection, message=message, status=status, data=data)
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.insert_read_errors_procedure": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def select_link_id_fields(cursor:object, link_id:int) -> list|str:
    """Receive link_id in input and if successful return a list contains of 'links' table field. If failed returns a string represents the error"""
    try:
        sql = f"""SELECT href, site_id, product_id, priority, counter FROM links WHERE id = {link_id}"""
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row:
            message = f'could not find a link with the link_id({link_id})'
            return message
        href, site_id, product_id, priority, counter = row[0], row[1], row[2], row[3], row[4]
        if not href or not site_id or not product_id:
            message = f'could not find \'href\' or \'site_id\' or \'product_id\' with this link_id({link_id})'
            return message
        return [href, site_id, product_id, priority, counter]
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.select_link_id_fields": {e.__str__()}')
        logging.warning(exception_line())
        return e.__str__()



def select_sites_fields_price_title_image(site_id:int, is_inner_connection:bool, connection:object, cursor:object) -> tuple|dict:
    """When getting price_title_image, we want to get 'sites' field for a particular site_id. If successfully found site with the provided site_id, return the tuple contains sites field for the row. If row not found return a dict"""
    try:
        sql = f"""SELECT crawler_type, parent_class, site_name, site_url, image_parent_selector, site_status, agent, title_selector, button_selector FROM sites WHERE id = {int(site_id)}"""
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row:
            message = f'no site found with site_id({site_id})'
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        return row
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.select_sites_fields_price_title_image": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def select_sites_fields_sitemap_href(site_id:int, is_inner_connection:bool, connection:object, cursor:object) -> tuple|dict:
    """When getting sitemap hrefs, we want to get 'sites' field for a particular site_id. If successfully found site with the provided site_id, return the tuple contains sites field for the row. If row not found return a dict"""
    try:
        cursor.execute(f'SELECT site_url, example_links, sitemap FROM sites WHERE id = {int(site_id)}')
        row = cursor.fetchone()
        # If no site_url found with 'site_url' stop executing the program
        if not row:
            # Close database connection after each request
            message = f'Did not found site_url on id({site_id})'
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        return row
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.select_sites_fields_sitemap_href": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def update_link_counter_aps(cursor:object, connection:object, counter:int, site_id:int, link_id:int) -> bool:
    """Update priority link by 1 in APSCHEDULER"""
    try:
        counter = counter + 1 if counter < 10 else 0
        cursor.execute(f'UPDATE links SET counter = {counter}, updated_at = "{_get_timestamp()}" WHERE site_id = {site_id} AND id = {link_id}')
        connection.commit()
        return True
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.update_link_counter_by_1": {e.__str__()}')
        logging.warning(exception_line())
        return False



def only_read_products_without_title(is_inner_connection:bool=False, connection:object=None, cursor:object=None, product_id:int=None) -> None|dict:
    """If _ONLY_FIND_TITLE is active, only read products without value for their title field. If title not found return None but if title found Return a dict to end the process"""
    try:
        cursor.execute(f"SELECT title FROM products WHERE id = {product_id}")
        row = cursor.fetchone()
        title = row[0]
        if title:
            message = f'Title is already exist for product_id({product_id})'
            result = db_close_log(is_inner_connection, connection, cursor, message)
            return result
        return None
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.only_read_products_without_title": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def update_counter_not_turn_aps(is_inner_connection:bool, connection:object, cursor:object, site_id:int, link_id:int, counter:int) -> dict:
    """In APS, if it's not product turn to be extracted based on priority and counter, its counter field most get updated before end the program. Return dict"""
    try:
        counter = counter + 1 if counter < 10 else 0
        cursor.execute(f'UPDATE links SET counter = {counter}, updated_at = "{_get_timestamp()}" WHERE site_id = {site_id} AND id = {link_id}')
        message = f'link_id({link_id}) is not in priority so ignore it for now'
        if settings.SAVE_PRIORITY_ERROR:
            # Insert read_errors
            insert_read_errors(cursor=cursor, site_id=site_id, link_id=link_id, title=message)
            connection.commit()
        result = db_close_log(is_inner_connection, connection, cursor, message, 'ok', 0)
        return result
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.extractor_helper.should_product_proceed_counter_priority_aps": {e.__str__()}')
        logging.warning(exception_line())
        return {'status': 'error', 'message': e.__str__(), 'data': -1}



def check_crawl_type_parent_selector(is_inner_connection:bool, connection:object, cursor:object, site_id:int, link_id:int, site_url:str, crawler_type:str, parent_class:str, site_status:str) -> None|dict:
    """Check crawler_type and parent_class of the site for the link we want to crawl. If there is a problem with it, return a dict. If successful return None"""
    if crawler_type not in ['custom', 'general']:
        message = f'crawler_type \'{crawler_type}\' for site_url {site_url} is not defined'
        # Insert read_errors
        result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
        return result
    # ! When apscheduler is active, only crawl products for sites with the field 'site_status=complete'
    if settings.RUN_SCHEDULE:
        if site_status != 'complete':
            message = f'{site_url} status is not \'complete\' for link_id({link_id}) and must be ignored'
            # Insert read_errors
            result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
            return result
    # Find if there are any error in 'crawler_type' or 'parent_class' fields
    if crawler_type == 'general' and not parent_class:
        message = f'\'parent_class\' not exist for the general crawler_type for a site with the site_id({site_id})'
        # Insert read_errors
        result = insert_read_errors_procedure(is_inner_connection, connection, cursor, message, site_id=site_id, link_id=link_id)
        return result
    return None



def produce_title_price_message_out(product_price:int, product_is_available:bool, link_id:int, product_data:list) -> dict:
    """After getting product title price, produce result message and return the message as response to the client"""
    result = dict()
    if product_price > 0 and not product_is_available:
        result.update({'status': 'ok', 'message': f'price is found ({product_price}) but product is not available for link_id({link_id}) so price set to -1 in db', 'data': None})
    elif product_price == 0 and product_is_available:
        result.update({'status': 'ok', 'message': f'product is available for link_id({link_id}) but price not found so price set to -1 in db', 'data': None})
    elif product_price == -1 and not product_is_available:
        result.update({'status': 'ok', 'message': f'product is not available and price not found for link_id({link_id}) so price set to -1 in db', 'data': None})
    # If everything is ok, return following result
    else:
        result.update({'status': 'ok', 'message': f'successfully get product price and title for the link_id({link_id})', 'data': product_data})
    return result
