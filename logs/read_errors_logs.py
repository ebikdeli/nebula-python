from .exception_logs import exception_line
from extractor_schedule.helper_functions import _get_timestamp, _escape_field
import logging
import mysql.connector



def insert_read_errors(cursor:object, site_id:int, link_id:int, title:str) -> str|None:
    """Everytime we encounter an error, insert the error into the read_errors table.
    NOTE: in 'find_price_title' for both 'custom' and 'general', None means any undetected error"""
    try:
        cursor.execute(f"""INSERT INTO read_errors (site_id, link_id, title, created_at, updated_at)
                       VALUES ({site_id}, {link_id}, '{_escape_field(title)}', '{_get_timestamp()}', '{_get_timestamp()}')""")
        read_errors_id = cursor.lastrowid
        return read_errors_id
    except Exception as e:
        logging.error(f'Error in "logs.read_errors_logs.insert_read_errors": {e.__str__()}')
        logging.warn(exception_line())
        return None
