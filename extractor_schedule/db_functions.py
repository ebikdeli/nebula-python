"""
We do not use this module directly in flask api functions. They are being used mainly in 'extractors' in this module.
All of the functions in this module interact with database

All CHAR fields would be escaped before being set in database
"""
from .helper_functions import _get_timestamp, _escape_field
from logs.exception_logs import exception_line
import logging



# * Insert or update 'products' table

def insert_products(cursor:object, site_id:int, title:str='', image_url:str='') -> int|None:
    """Insert new product in the database. If successful return 'product_id' otherwise return None"""
    try:
        product_id = None
        # cursor = connection.cursor()
        cursor.execute(f"""INSERT INTO products (title, site_id, image, created_at, updated_at) 
                            VALUES ('{_escape_field(title)}', {site_id}, '{_escape_field(image_url)}', '{_get_timestamp()}', '{_get_timestamp()}')""")
        product_id = cursor.lastrowid
        # cursor.close()
    except Exception as e:
        logging.error(f'Error in the "extractor_schedule.functions.insert_products": {e.__str__()}')
        logging.warning(exception_line())
    finally:
        return product_id


def update_products(cursor:object, product_id:int, site_id:int, title:str, image_url:str='') -> int|None:
    """Update the products table. If successful return 'product_id' otherwise return None"""
    try:
        # cursor = connection.cursor()
        cursor.execute(f"""UPDATE products SET title = '{_escape_field(title)}', image = '{_escape_field(image_url)}', updated_at = '{_get_timestamp()}'
                       WHERE site_id = {site_id} AND id = {product_id}""")
        # cursor.close()
    except Exception as e:
        logging.error(f'Error in the "extractor_schedule.functions.update_products": {e.__str__()}')
        logging.warning(exception_line())
    finally:
        return product_id


def update_products_check_title(cursor:object, product_id:int, site_id:int, title:str, image_url:str='') -> int|None:
    """Update the products table but after check title field if filled. If successful return 'product_id' otherwise return None"""
    try:
        # cursor = connection.cursor()
        # Check if title is alredy filled, don't update it
        cursor.execute(f"SELECT title FROM products WHERE site_id = {site_id} AND id = {product_id}")
        row = cursor.fetchone()
        if row:
            title_before = row[0]
            if title_before:
                # print('title is ', title_before)
                cursor.execute(f"""UPDATE products SET image = '{_escape_field(image_url)}', updated_at = '{_get_timestamp()}'
                            WHERE site_id = {site_id} AND id = {product_id}""")
            # elif not title_before and (title or image_url):
            else:
                # print('new title is ', title)
                cursor.execute(f"""UPDATE products SET title = '{_escape_field(title)}', image = '{_escape_field(image_url)}', updated_at = '{_get_timestamp()}'
                            WHERE site_id = {site_id} AND id = {product_id}""")
        # cursor.close()
    except Exception as e:
        logging.error(f'Error in the "extractor_schedule.functions.update_products": {e.__str__()}')
        logging.warning(exception_line())
    finally:
        return product_id



# * 'insert or update 'links' table

def insert_links(cursor:object, href:str, site_id:int, product_id:int, price:int=-1) -> int|None:
    """Insert it into 'links' table. If successful return 'link_id' otherwise return None."""
    try:
        # cursor = connection.cursor()
        cursor.execute(f"""INSERT INTO links (href, site_id, price, product_id, created_at, updated_at)
                        VALUES ('{_escape_field(href)}', {site_id}, {price}, {product_id}, '{_get_timestamp()}', '{_get_timestamp()}')""")
        link_id = cursor.lastrowid
        return link_id
        # cursor.close()
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.functions.insert_links": {e.__str__()}')
        logging.warning(exception_line())
        return None


def update_links(cursor:object, href:str, site_id:int, link_id:int=None, price:int|None=-1) -> int|None:
    """Insert into 'links' table. If successful return 'link_id' otherwise return None."""
    try:
        # cursor = connection.cursor()
        if link_id:
            cursor.execute(f"""SELECT id FROM links WHERE site_id = {site_id} AND id = {link_id}""")
        else:
            cursor.execute(f"""SELECT id FROM links WHERE site_id = {site_id} AND href = '{_escape_field(href)}'""")
        row = cursor.fetchone()
        if row:
            link_id = row[0]
            if price is not None:
                cursor.execute(f"""UPDATE links 
                            SET price = {price}, updated_at = '{_get_timestamp()}'
                            WHERE site_id = {site_id} AND id = {link_id}""")
        return link_id
        # cursor.close()
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.functions.insert_links": {e.__str__()}')
        logging.warning(exception_line())
        return None




# * Select site_id by site_url or reverse

def select_site_id_by_site_url(cursor:object, site_url:str) -> int|None:
    """return site_id by looking at the site_url in 'sites' table. If not successful return None"""
    try:
        site_id = None
        # cursor = connection.cursor(buffered=True)
        sql = f"""SELECT id FROM sites WHERE site_url = {_escape_field(site_url)}"""
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row:
            return None
        else:
            site_id = row[0]
    except Exception as e:
        logging.error(f'Error in "_get_site_id_by_site_url": {e.__str__()}')
        logging.warning(exception_line())
    finally:
        # cursor.close()
        return site_id


def select_site_url_by_site_id(cursor:object, site_id:int) -> str|None:
    """Receive 'site_id' and return the 'site_url' from the 'sites' table. if any error happend return None"""
    try:    
        site_url = None
        # cursor = connection.cursor(buffered=True)
        sql = f"""SELECT site_url FROM sites WHERE id = {site_id}"""
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row:
            message = f'Did not found site_url on id({site_id})'
            logging.warning(message)
        else:
            site_url = row[0]
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.functions.select_site_url_by_site_id": {e.__str__()}')
        logging.warning(exception_line())
    finally:
        # cursor.close()
        return site_url
