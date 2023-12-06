import settings
import logging
import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ? Main setting to run the the bot as two separated applications
# Run 'servere_request' if 'RUN_SCHEDULE' is down
if not settings.RUN_SCHEDULE:
    logging.warning('Apscheduler is disabled')
    from flask_server.server_request import app
    if __name__ == '__main__':
        # flask_apscheduler interrupted if "use_reloader=True" when "debug=True" in flask
        app.run(host='0.0.0.0', port=settings.REQUEST_SERVER_PORT, debug=True, use_reloader=False)
# Run 'server_aps' if 'RUN_SCHEDULE' flag is up
elif settings.RUN_SCHEDULE:
    logging.warning(f'Apscheduler is enabled. Make a request to \'http(s)://yourdomain.com/start\' url to start the apscheduler')
    from flask_server.server_aps import app
    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=settings.APS_SERVER_PORT, debug=True, use_reloader=False)



# ? To test 'sitemap_reader'
# from sitemap_reader import sm_reader


# ? To test 'product_match
# from product_match import match


# ? To test 'get_price_name'
# from crawl_price_name import general

# ? To test 'external_call' in crawl_price_name
# from crawl_price_name import external_call


# ? To test threads in extractors
# from extractor_schedule import extractors


# ? To test custom 'get_price_name'
# from crawl_price_name import custom
