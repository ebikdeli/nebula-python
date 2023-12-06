import os
import sys



def exception_line(description:str=None) -> str:
    """Show exception line. Receive arbitrary argument to describe error"""
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    if description:
        message = f'Error description:{description}\nerror line: {exc_type}, {fname}, {exc_tb.tb_lineno}'
    else:
        message = f'error line: {exc_type}, {fname}, {exc_tb.tb_lineno}'
    return message
