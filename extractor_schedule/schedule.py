import settings
from extractor_schedule import extractors
from extractor_schedule.del_temp import clean_temp_folder
from flask_server.functions import connect_mysql, chunker
from logs.exception_logs import exception_line
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import concurrent.futures
import uuid
import logging



# * Initialize scheduler and threadpool executor worker
scheduler = BackgroundScheduler()
EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
if settings.RUN_SCHEDULE:
    scheduler.start()



if settings.IS_SCHEDULE_READ_SITEMAP_CRON:
    def find_sitemap_hrefs_all_periodic(executor:object=EXECUTOR):
        """At the start of every day execute 'find_all_sites_sitemap_products_href'"""
        # extractors.find_all_sites_sitemap_products_href()
        # ** START
        _array_size = 50
        _timeout = 40
        try:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            # if not driver:
            #     driver = call_selenium_driver()
            # sql = """Select id FROM sites WHERE site_status = 'complete'"""
            # To apschedule be able to control thread flow, we need to use play with Executor
            # Clean Temp folder to not let server crash
            clean_temp_folder()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            sql = """Select id FROM sites"""
            cursor.execute(sql)
            while True:
                rows = cursor.fetchmany(_array_size)
                if rows:
                    logging.info(f'site_id\'s to process: {rows}')
                # If read all the ids from table break the reading process
                if not rows:
                    logging.info('No more site_id left')
                    break
                # Method 1
                # with concurrent.futures.ThreadPoolExecutor as executor:
                #     futures = [executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=row[0]) for row in rows]
                #     # To forcefully stop the thread (NOTE: could be very dangerous)
                #     executor.shutdown(wait=False)
                #     # ! Above line does everything we want. Following block does not neccessary but tells us about the status of thread. So it's a good practice to have these
                #     for future in concurrent.futures.as_completed(futures):
                #         logging.info(f'>got {future.result()}')
                #     # issue one task for each call to the function
                #     # for result in executor.map(find_sitemap_products_href, rows):
                #     #     print(f'>got {result}')
                # METHOD 2
                # executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
                futures = []
                # i = 0
                # for link_id in rows:
                for chunk_id in chunker(rows, 10):
                    for site_tuple in chunk_id:
                        try:
                            # future = executor.submit(extractors.find_sitemap_products_href, save_image=save_image, timeout=timeout, site_id=site_tuple[0])
                            # print("i ==========>   ", i)
                            # future = executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=site_tuple[0])
                            # future = executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=site_tuple[0])
                            future = executor.submit(extractors.find_sitemap_products_href, site_id=site_tuple[0], api_agent='requests')
                            futures.append(future)
                            # ! This is how we can stop the executor
                            # i += 1
                            # if i == 10000:
                            #     executor.shutdown(wait=False, cancel_futures=True)
                            # time.sleep(.1)
                        except (KeyboardInterrupt, SystemError):
                            logging.error('PROGRAM INTERRUPTED')
                            cursor.close()
                            connection.close()
                            executor.shutdown(wait=False, cancel_futures=True)
                            exit()
                    for f in concurrent.futures.as_completed(futures):
                        print(f'>RESULT: {f.result()}')
                        logging.info('Tasks done')
                        logging.info('Every sitemaps in the sites read and their links extracted')
                        # cursor.close()
                        # connection.close()
                        # return {'status': 'success', 'message': 'operation completed', 'data': 1}
            # Clean Temp folder to not let server crash
            clean_temp_folder()
        except Exception as e:
            logging.error(f'Error in "extractor_schedule.schedule.find_sitemap_hrefs_all_periodic": {e.__str__()}')
            logging.warning(exception_line())
            # return {'status': 'error', 'message': 'error in operation', 'data': -1}        
        # ** END
    # ? Following command add above job to apschedule
    if not settings.APS_FIND_PRODUCTS:
        scheduler.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='cron', hour=settings.SCHEDULE_READ_SITEMAP_HOUR_DAY, minute=settings.SCHEDULE_READ_SITEMAP_MINUTE_DAY, second=settings.SCHEDULE_READ_SITEMAP_SECOND_DAY)
        # scheduler.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='cron', hour=23, minute=57, second=2)
else:
    # @scheduler.task('date', id='find_sitemap_hrefs_all_periodic', run_date=datetime.now() + timedelta(minutes=45))
    def find_sitemap_hrefs_all_periodic(executor:object=EXECUTOR):
        """At the start of every day execute 'find_all_sites_sitemap_products_href'"""
        # extractors.find_all_sites_sitemap_products_href()
        # ** START
        _array_size = 50
        _timeout = 40
        try:
            connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
            connection = connect_mysql(**connection_data)
            cursor = connection.cursor(buffered=True)
            # if not driver:
            #     driver = call_selenium_driver()
            # sql = """Select id FROM sites WHERE site_status = 'complete'"""
            # To apschedule be able to control thread flow, we need to use play with Executor
            # global EXECUTOR
            # if not executor:
            #     executor = EXECUTOR
            # else:
            #     # executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
            #     EXECUTOR = executor
            # Clean Temp folder to not let server crash
            clean_temp_folder()
            sql = """Select id FROM sites"""
            cursor.execute(sql)
            while True:
                rows = cursor.fetchmany(_array_size)
                if rows:
                    logging.info(f'site_id\'s to process: {rows}')
                # If read all the ids from table break the reading process
                if not rows:
                    logging.info('No more site_id left')
                    break
                # Method 1
                # with concurrent.futures.ThreadPoolExecutor as executor:
                #     futures = [executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=row[0]) for row in rows]
                #     # To forcefully stop the thread (NOTE: could be very dangerous)
                #     executor.shutdown(wait=False)
                #     # ! Above line does everything we want. Following block does not neccessary but tells us about the status of thread. So it's a good practice to have these
                #     for future in concurrent.futures.as_completed(futures):
                #         logging.info(f'>got {future.result()}')
                #     # issue one task for each call to the function
                #     # for result in executor.map(find_sitemap_products_href, rows):
                #     #     print(f'>got {result}')
                # METHOD 2
                # executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
                futures = []
                # i = 0
                # for link_id in rows:
                for chunk_id in chunker(rows, 10):
                    for site_tuple in chunk_id:
                        try:
                            # future = executor.submit(extractors.find_sitemap_products_href, save_image=save_image, timeout=timeout, site_id=site_tuple[0])
                            # print("i ==========>   ", i)
                            # future = executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=site_tuple[0])
                            # future = executor.submit(extractors.find_sitemap_products_href, timeout=_timeout, site_id=site_tuple[0])
                            future = executor.submit(extractors.find_sitemap_products_href, site_id=site_tuple[0], api_agent='requests')
                            futures.append(future)
                            # ! This is how we can stop the executor
                            # i += 1
                            # if i == 10000:
                            #     executor.shutdown(wait=False, cancel_futures=True)
                            # time.sleep(.1)
                        except KeyboardInterrupt:
                            logging.error('PROGRAM INTERRUPTED')
                            cursor.close()
                            connection.close()
                            executor.shutdown(wait=False, cancel_futures=True)
                            exit()
                    for f in concurrent.futures.as_completed(futures):
                        print(f'>RESULT: {f.result()}')
                        logging.info('Tasks done')
                        logging.info('Every sitemaps in the sites read and their links extracted')
                        # cursor.close()
                        # connection.close()
                        # return {'status': 'success', 'message': 'operation completed', 'data': 1}
            # Clean Temp folder to not let server crash
            clean_temp_folder()
        except Exception as e:
            logging.error(f'Error in "extractor_schedule.schedule.find_sitemap_hrefs_all_periodic": {e.__str__()}')
            logging.warning(exception_line())
            # return {'status': 'error', 'message': 'error in operation', 'data': -1}
        # ** END
        # The scheduler wait for the task to executed completely then wait for 720 minutes by default to execute the task again. 
        next_run_time = datetime.now() + timedelta(minutes=settings.SCHEDULE_READ_SITEMAP_EVERY_MINUTES)
        scheduler.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='date', run_date=next_run_time)
    # ? Following command add above job to apschedule
    if not settings.APS_FIND_PRODUCTS:
        scheduler.add_job(id='find_sitemap_hrefs_all_periodic', func=find_sitemap_hrefs_all_periodic, trigger='date', run_date=datetime.now() + timedelta(seconds=10))


# @scheduler.task('date', id='find_all_links_price_title_non_block_periodically', run_date=datetime.now() + timedelta(minutes=1))
def find_price_title_all_non_block_periodic(executor:object=EXECUTOR):
    """One minute after server started, our task (find_price_title_all_non_block_periodic) executed. After the execution finished, scheduler wait for 10 minutes by default and execute the task again. This is a cycle."""
    # extractors.find_all_links_price_title_non_block()
    # ** START
    _timeout = 40
    try:
        connection_data = {'user': settings.DB_USER, 'password': settings.DB_PASSWORD, 'db_name': settings.DB_NAME, 'hostname': settings.DB_HOST, 'port':settings.DB_PORT}
        connection = connect_mysql(**connection_data)
        cursor = connection.cursor(buffered=True)
        # if not driver:
        #     driver = call_selenium_driver()
        _site_id_list = []
        _site_link_len = []
        site_dict = {}
        process_now = []
        # executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
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
                    process_now.append(link_id_list[i])
                except IndexError:
                    continue
            i += 1
        del site_dict
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        print('APSCHEDULER GONNA START THREADPOOL')
        # METHOD 1
        # with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
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
        # executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        futures = []
        # i = 0
        # for link_id in process_now:
        for chunk_id in chunker(process_now, 10):
            for link_id in chunk_id:
                try:
                    # future = executor.submit(extractors.find_price_title, save_image=save_image, timeout=timeout, link_id=link_id)
                    # print("i ==========>   ", i)
                    # future = executor.submit(extractors.find_price_title, timeout=_timeout, link_id=link_id)
                    # future = executor.submit(extractors.find_price_title, timeout=_timeout, link_id=link_id, save_image=True, _ONLY_FIND_TITLE=settings.ONLY_FILL_EMPTY)
                    future = executor.submit(extractors.find_price_title, api_agent='requests', timeout=settings.REQUESTS_TIMEOUT, link_id=link_id, save_image=settings.SAVE_IMAGE, force_save_image=settings.SAVE_IMAGE, _ONLY_FIND_TITLE=settings.ONLY_FILL_EMPTY)
                    futures.append(future)
                    # ! This is how we can stop the executor
                    # i += 1
                    # if i == 10000:
                    #     executor.shutdown(wait=False, cancel_futures=True)
                    # time.sleep(.1)
                except KeyboardInterrupt:
                    logging.error('PROGRAM INTERRUPTED')
                    cursor.close()
                    connection.close()
                    executor.shutdown(wait=False, cancel_futures=True)
                    exit()
        for f in concurrent.futures.as_completed(futures):
            print(f'>RESULT: {f.result()}')
        # Clean Temp folder to not let server crash
        clean_temp_folder()
        # END OF METHODS
        logging.info('Tasks done')
        del process_now
        logging.info('Every href in the links read updated their price and title')
        cursor.close()
        connection.close()
        # return {'status': 'success', 'message': 'operation completed', 'data': 1}
    except Exception as e:
        logging.error(f'Error in "extractor_schedule.schedule.find_price_title_all_non_block_periodic": {e.__str__()}')
        logging.warning(exception_line())
        # return {'status': 'error', 'message': 'error in operation', 'data': -1}
    # ** END
    # The scheduler wait for the task to executed completely then wait for 10 minutes by default to execute the task again. 
    next_run_time = datetime.now() + timedelta(minutes=settings.SCHEDULE_FIND_PRICE_TITLE_EVERY_MINUTES)
    scheduler.add_job(id=str(uuid.uuid4()), func=find_price_title_all_non_block_periodic, trigger='date', run_date=next_run_time)
if settings.APS_FIND_PRODUCTS:
    # ? Following command add above job to apschedule
    scheduler.add_job(id='find_all_links_price_title_non_block_periodically', func=find_price_title_all_non_block_periodic, trigger='date', run_date=datetime.now() + timedelta(seconds=10))
