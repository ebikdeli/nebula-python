"""This module only works when user choose to run the apscheduler
NOTE: modules only run one time in python even if we call the modules for several times in a function
"""
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers import SchedulerAlreadyRunningError, SchedulerNotRunningError
from flask_server.functions import connect_flask_mysql
from logs.exception_logs import exception_line
import settings
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta



# SET GLOBAL VARIABLES
IS_SCHEDULER_RUNNING = False
THREADPOOLEXECUTOR = None
SCHEDULER = None


try:
    app = Flask(__name__)
except Exception as e:
    logging.critical('ERROR IN CONNECTING TO DATABASE IN FLASK SERVER: ', e.__str__())
    logging.warning('STOP ALL THE FURTHER PROCESS!')
    logging.warn(exception_line())
    exit()



@app.route('/start', methods=['GET', 'POST'])
def start():
    """Start the apscheduler"""
    try:
        global IS_SCHEDULER_RUNNING
        global SCHEDULER
        global THREADPOOLEXECUTOR
        if IS_SCHEDULER_RUNNING:
            return jsonify({'status': 'ok', 'message': 'scheduler already running', 'data': 0})
        from extractor_schedule import schedule
        IS_SCHEDULER_RUNNING = True
        if not THREADPOOLEXECUTOR:
            THREADPOOLEXECUTOR = schedule.EXECUTOR
        if not SCHEDULER:
            SCHEDULER = schedule.scheduler
        # If no jobs found in the scheduler, add jobs to it
        if not SCHEDULER.get_jobs():
            from extractor_schedule.schedule import find_sitemap_hrefs_all_periodic, find_price_title_all_non_block_periodic
            # Decide which job to executed by apscheduler
            if settings.APS_FIND_PRODUCTS:
                SCHEDULER.add_job(id='find_all_links_price_title_non_block_periodically', func=find_price_title_all_non_block_periodic, trigger='date', kwargs={'executor': THREADPOOLEXECUTOR}, run_date=datetime.now() + timedelta(seconds=60))
            else:
                if settings.IS_SCHEDULE_READ_SITEMAP_CRON:
                    SCHEDULER.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='cron', hour=settings.SCHEDULE_READ_SITEMAP_HOUR_DAY, minute=settings.SCHEDULE_READ_SITEMAP_MINUTE_DAY, second=settings.SCHEDULE_READ_SITEMAP_SECOND_DAY)
                else:
                    SCHEDULER.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='date', run_date=datetime.now() + timedelta(minutes=120))
        # print(SCHEDULER.get_jobs())
        if settings.APS_FIND_PRODUCTS:
            message = 'scheduler starts \'find_price_title_all_non_block_periodic\''
        else:
            message = 'scheduler starts \'find_sitemap_hrefs_all_periodic\''
        return jsonify({'status': 'ok', 'message': message, 'data': 1})
    except SchedulerAlreadyRunningError:
        return jsonify({'status': 'ok', 'message': 'scheduler already running', 'data': 0})



@app.route('/stop', methods=['GET', 'POST'])
def stop():
    """Force stop apscheduler"""
    global IS_SCHEDULER_RUNNING
    global SCHEDULER
    global THREADPOOLEXECUTOR
    if not IS_SCHEDULER_RUNNING:
        return jsonify({'status': 'ok', 'message': 'scheduler is not started', 'data': 0})
    THREADPOOLEXECUTOR.shutdown(wait=False, cancel_futures=True)
    SCHEDULER.remove_all_jobs()
    SCHEDULER.shutdown(wait=False)
    IS_SCHEDULER_RUNNING = False
    del SCHEDULER
    del THREADPOOLEXECUTOR
    THREADPOOLEXECUTOR = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
    SCHEDULER = BackgroundScheduler()
    SCHEDULER.start()
    return jsonify({'status': 'ok', 'message': 'scheduler stopped but it might takes some time to totally stopped', 'data': 1})











# @app.route('/start', methods=['GET', 'POST'])
# def start():
#     """Start the apscheduler"""
#     try:
#         global IS_SCHEDULER_RUNNING
#         global SCHEDULER
#         global THREADPOOLEXECUTOR
#         if IS_SCHEDULER_RUNNING:
#             return jsonify({'status': 'ok', 'message': 'scheduler already running', 'data': 0})
#         from extractor_schedule import schedule
#         IS_SCHEDULER_RUNNING = True
#         if not THREADPOOLEXECUTOR:
#             THREADPOOLEXECUTOR = schedule.EXECUTOR
#         if not SCHEDULER:
#             SCHEDULER = schedule.scheduler
#         # If no jobs found in the scheduler, add jobs to it
#         if not SCHEDULER.get_jobs():
#             from extractor_schedule.schedule import find_sitemap_hrefs_all_periodic, find_price_title_all_non_block_periodic
#             SCHEDULER.add_job(id='find_all_links_price_title_non_block_periodically', func=find_price_title_all_non_block_periodic, trigger='date', kwargs={'executor': THREADPOOLEXECUTOR}, run_date=datetime.now() + timedelta(seconds=60))
#             if settings.IS_SCHEDULE_READ_SITEMAP_CRON:
#                 SCHEDULER.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='cron', hour=settings.SCHEDULE_READ_SITEMAP_HOUR_DAY, minute=settings.SCHEDULE_READ_SITEMAP_MINUTE_DAY, second=settings.SCHEDULE_READ_SITEMAP_SECOND_DAY)
#             else:
#                 SCHEDULER.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='date', run_date=datetime.now() + timedelta(minutes=120))
#         # print(SCHEDULER.get_jobs())
#         return jsonify({'status': 'ok', 'message': 'scheduler began', 'data': 1})
#     except SchedulerAlreadyRunningError:
#         return jsonify({'status': 'ok', 'message': 'scheduler already running', 'data': 0})
