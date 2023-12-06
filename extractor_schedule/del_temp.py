from logs.exception_logs import exception_line
import os
import subprocess
import platform
import logging



def clean_temp_folder() -> bool:
    """browsers take lots of resources and remain some of their footprints in Temp folder in os and need to clean them up. If successful return True otherwise return False"""
    try:
        # * FOR WINDOWS MACHINES
        if 'windows' in platform.system().lower():
            try:
                current_user = os.environ["HOMEPATH"][os.environ["HOMEPATH"].rfind("\\")+1:]
            except KeyError:
                current_user = os.getlogin()
            del_dir = f"{os.environ['HOMEDRIVE']}{os.environ['HOMEPATH']}\\AppData\\Local\\Temp"
            print('Start to cleanup the Windows Temp folder...')
            pObj = subprocess.Popen(f'del /S /Q /F {del_dir}\\*.*', shell=True, stdout = subprocess.PIPE, stderr= subprocess.PIPE)
            _rTup = pObj.communicate()
            rCod = pObj.returncode
            if rCod == 0:
                print (f'Success: Cleaned User({current_user}) Windows Temp Folder')
                return True
            else:
                print (f'Fail: Unable to Clean User({current_user}) Windows Temp Folder')
                return False
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.del_temp.clean_temp_folder": {e.__str__()}')
        logging.warn(exception_line())
    return False
