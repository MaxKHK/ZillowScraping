# ZillowScraping

DISCLAIMER: Use this code at your own risk. Scraping violates Zillow's user agreement. Code is provided to illustrate web-scraping operations

Module which is capable of scraping property listings from zillow.com. Information scraped includes:

- Property parameters (like number of rooms, floors, materials)
- History of prices for each listing
- Posted photos for property

Search is performed by zip-code.

Requrements:
- Selenium
- MySQL database to store results, also pymysql and sqlalchemy
- Pandas
- BeautifulSoup


Code consists of two parts:
zillow_functions.py contains helper functions which perform processing of listing
zillow_runfile.py manages actual scraping. Run this file to perform scraping.

In zillow_runfile you need to update SQL connection string to match your setup as well as location of chrome web-driver for selenium (driver can be obtained from https://sites.google.com/a/chromium.org/chromedriver/downloads)

In zillow_functions you need to update the directory where you want to stored scraped images. Images will be stored in subfolders, with folder name representing zpid.

Notice, zillow continously changes its web-site so perfect work of this scraper is not guaranteed in future.
