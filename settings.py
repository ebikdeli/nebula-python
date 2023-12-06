import _env



# ! database connection variables
DB_USER = _env.DB_USER
DB_PASSWORD = _env.DB_PASSWORD
DB_NAME = _env.DB_NAME
DB_HOST = _env.DB_HOST
DB_PORT = _env.DB_PORT



# ! Server ports
REQUEST_SERVER_PORT = _env.REQUEST_SERVER_PORT
APS_SERVER_PORT = _env.APS_SERVER_PORT


# ! Scheduler settings
RUN_SCHEDULE = _env.RUN_SCHEDULE    # RUN_SCHEDULE controls which flask server to be run
APS_FIND_PRODUCTS = _env.APS_FIND_PRODUCTS    # APS_FIND_PRODUCTS controls which job in scheduler run
SCHEDULE_FIND_PRICE_TITLE_EVERY_MINUTES = _env.SCHEDULE_FIND_PRICE_TITLE_EVERY_MINUTES
IS_SCHEDULE_READ_SITEMAP_CRON = _env.IS_SCHEDULE_READ_SITEMAP_CRON
SCHEDULE_READ_SITEMAP_HOUR_DAY = _env.SCHEDULE_READ_SITEMAP_HOUR_DAY
SCHEDULE_READ_SITEMAP_MINUTE_DAY = _env.SCHEDULE_READ_SITEMAP_MINUTE_DAY
SCHEDULE_READ_SITEMAP_SECOND_DAY = _env.SCHEDULE_READ_SITEMAP_SECOND_DAY
SCHEDULE_READ_SITEMAP_EVERY_MINUTES = _env.SCHEDULE_READ_SITEMAP_EVERY_MINUTES
MAX_INSTANCE = _env.MAX_INSTANCE


# ! Extract all links from sites with 'bad' or 'none' as value for sitemap_field in 'sites' table (In apscheduler it only works if APS_FIND_PRODUCTS is NOT active)
SITEMAP_ONLY_EXTRACT_ALL_LINKS = _env.SITEMAP_ONLY_EXTRACT_ALL_LINKS


# ! ThreadPool settings
MAX_WORKERS = _env.MAX_WORKERS



# ! Igonre These site_urls
IGNORE_SITE_URL_LIST = _env.IGNORE_SITE_URL_LIST


# ! Selenium settings and Chrome Version (To be used in drivers and initialize chrome webdriver)
CHROME_BROWSER_VERSION = _env.CHROME_BROWSER_VERSION
CHROME_DRIVER_TIMEOUT = _env.CHROME_DRIVER_TIMEOUT
GENERAL_IMPLICIT_WAIT = _env.GENERAL_IMPLICIT_WAIT
DIGIKALA_IMPLICIT_WAIT = _env.DIGIKALA_IMPLICIT_WAIT
TOROB_IMPLICIT_WAIT = _env.TOROB_IMPLICIT_WAIT
EMALLS_IMPLICIT_WAIT = _env.EMALLS_IMPLICIT_WAIT



# ! Requests settings
REQUESTS_TIMEOUT = _env.REQUESTS_TIMEOUT
REQUESTS_CHROME_USER_AGENT = _env.REQUESTS_CHROME_USER_AGENT



# * Proxy settings
PROXY_LIST = _env.PROXY_LIST
PROXY_WEBSITES = _env.PROXY_WEBSITES
USE_PROXY_SITEMAP = _env.USE_PROXY_SITEMAP



# Only crawl products with empty product title
ONLY_FILL_EMPTY = _env.ONLY_FILL_EMPTY



# A controller to save image or not
SAVE_IMAGE = _env.SAVE_IMAGE



# Use Undetected selenium to bypass anti-bot processes (eg: cloudflare anti-bot plugin)
USE_SELENIUM_UNDETECTED = _env.USE_SELENIUM_UNDETECTED



# Priorities
PRIORITY_FULL = _env.PRIORITY_FULL
PRIORITY_HALF = _env.PRIORITY_HALF
PRIORITY_ONE = _env.PRIORITY_ONE
PRIORITY_ZERO = _env.PRIORITY_ZERO

# Save priority read_errors
SAVE_PRIORITY_ERROR = _env.SAVE_PRIORITY_ERROR



# Google Web Cache configs
USE_TOROB_GOOGLE_WEB_CACHE = _env.USE_TOROB_GOOGLE_WEB_CACHE



# Using headless mode for selenium
USE_HEADLESS_SELENIUM = _env.USE_HEADLESS_SELENIUM
DISABLE_CSS_JS_SELENIUM = _env.DISABLE_CSS_JS_SELENIUM



# Search for category_link
SITEMAP_SEARCH_CATEGORY_PRODUCTS_ANYWAY = _env.SITEMAP_SEARCH_CATEGORY_PRODUCTS_ANYWAY      # When extracting product links from sitemap, always try to read product category links
SITEMAP_SEARCH_CATEGORY_ONLY_WITHOUT_PRODUCT = _env.SITEMAP_SEARCH_CATEGORY_ONLY_WITHOUT_PRODUCT    # When extracting product links from sitemap, Only extract products from category links if there is no product link found in the sitemap links
# If a site is in SITE_NOT_READ_CATEGORY_LIST, should not look for it's category links
SITES_NOT_READ_CATEGORY_LIST = _env.SITES_NOT_READ_CATEGORY_LIST



# CONFIGS TO USE GOOGLE WEB CACHE TO EXTRACT DATA INSTEAD OF EXTRACTING WEBSITES DIRECTLY
USE_GOOGLE_WEB_CACHE_PRICE_TITLE = _env.USE_GOOGLE_WEB_CACHE_PRICE_TITLE    # Use google web cache to find product title-price-image instead of getting them directly
USE_REQUESTS_GOOGLE_WEB_CHACHE = _env.USE_REQUESTS_GOOGLE_WEB_CHACHE      # Use 'requests' library to extract data from google web cache instead of 'selenium'
# Only use google web cache for these websites
GOOGLE_WEB_CACH_SITES = _env.GOOGLE_WEB_CACH_SITES



# By default the bot uses 'selenium' to search for all links from a website. But we can use 'requests' to do this by activate following flag
USE_REQUESTS_FIND_ALL_LINKS = _env.USE_REQUESTS_FIND_ALL_LINKS
