import settings
from .helper_functions import _get_timestamp
from logs.exception_logs import exception_line
import logging



def check_if_its_turn(counter:int, priority:int) -> bool:
    """Check if it's ok to let a link continue to be be crawled"""
    if priority == 0:
        return False  # PRODUCT IGNORED FOR EVER!
    if counter == 0:
        return True  # Initial point
    elif counter / priority > 1:
        return False
    else:
        return True



def change_failed_priority(cursor:object, link_id:int, priority:int) -> bool|None:
    """Change the priority if price is -1 for number of consecutive times. If change occured return True, If no change occured return False. If any error happens return None"""
    try:
        sql = f"SELECT id, price FROM price_logs WHERE link_id = {link_id} ORDER BY updated_at DESC LIMIT 15"
        cursor.execute(sql)
        rows = cursor.fetchall()
        if not rows:
            logging.warning(f'link_id({link_id}) has no price_logs registered for it')
            return False
        _no_price_counter = 0
        priority_level = priority
        for row in rows:
            _price_log_id, price = row[0], row[1]
            if price == -1:
                _no_price_counter += 1
            else:
                break
        if 3 <= _no_price_counter < 10:
            priority_level = settings.PRIORITY_HALF
        if _no_price_counter == 10:
            priority_level = settings.PRIORITY_ONE
        if _no_price_counter > 10:
            priority_level = settings.PRIORITY_ZERO
        # Only update 'priority' field if priority_level is not equall to priority
        if priority_level != priority:
            sql = f"UPDATE links SET priority = {priority_level}, updated_at = '{_get_timestamp()}' WHERE id = {link_id}"
            cursor.execute(sql)
            logging.warning(f'priority updated to {priority_level} for link({link_id})')
            return True
        logging.warning(f'priority did not changed for link({link_id})')
        return False
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.priority_check.lower_failed_priority": {e.__str__()}')
        logging.warning(exception_line())
        return None



def reset_priority(cursor:object, link_id:int) -> bool|None:
    """Reset links priority to 10. If successful return True"""
    try:
        cursor.execute(f"UPDATE links SET priority = 10, counter = 0, updated_at = '{_get_timestamp()}' WHERE id = {link_id}")
        return True
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.priority_check.reset_priority": {e.__str__()}')
        logging.warning(exception_line())
        return None
