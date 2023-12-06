from extractor_schedule.helper_functions import _get_timestamp
from logs.exception_logs import exception_line
import logging



def insert_price_logs(cursor:object, link_id:int, price:int=-1) -> str|None:
    """Everytime price is updated, a new price_logs row inserted into this table. Return new price_logs_id if successful otherwise return None"""
    try:
        # cursor = connection.cursor()
        ts = _get_timestamp()
        sql = f"""INSERT INTO price_logs (link_id, price, created_at, updated_at)
        VALUES ({link_id}, {price}, '{ts}', '{ts}')"""
        cursor.execute(sql)
        price_logs_id = cursor.lastrowid
        return price_logs_id
    except Exception as e:
        logging.error(f'Error in "logs.extractor_logs.insert_price_logs": {e.__str__()}')
        logging.warn(exception_line())
        return None
