import requests
from bs4 import BeautifulSoup
import csv
import re
import logging
import logging.handlers
import json
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


"""

This script is developed to scrape the license information of Pharmacist whole last name begins with L.
The script performs following steps to scrape the data.
1. Simulate interaction with the webpage to fill form with parameters.
2. Iterate over pages returned and get the result ids using beautifulsoup from the href's in anchor tags.
3. Use the id and send another request to get to the details page.
4. Parse and return the interested data e.g. First name, last name, etc. as dictionary from details page.
5. Save the json data to a json file.

Libraries used: 
1. Selenium - This library is used to:
    * To open the url in chrome browswer.
    * Fill the form with and click on search.
    * Get the browser cookie - the cookie is later used in the program to navigate to details pages using requests library.
    * Get the search result source page.

2. BeautifulSoup - This library is used to:
    * Load and parse the HTML data returned by selenium and requests.
    * Extract result ids from the page source table e.g. datagrid_results
    * Extract the attributes from details page.

3. re - the regex library is used to:
    * Generate and match expression with page (r"__doPostBack\('([^']+)") to create the logic to navigate pages and scrape data
    * E.g. the search result for this use case returned 6 pages, and the regrex helped in looping through all pages.
    * Match the string in Details pages anchor tags and get the result id that will be used in sending the request to get license detail.

4. Requests - This library is used to:
    * send request to url including the relevant header, cookie, viewstate information.

5. JSON - The json library is used to save the data to file.

"""

# Define the url of the website.
baseUrl = "https://idbop.mylicense.com/verification/" 
searchResultPageUrlSuffix = "SearchResults.aspx"

# Initiate a request session object
session = requests.session()


def get_logger(appname):
    """Function to create a logger object which can be used to log processes with verbosity
       during script execution."""

    logger = logging.getLogger(appname)
    # datetime object containing current date and time
    if not logger.handlers:
        # Prevent logging from propagating to the root logger
        logger.propagate = 0
        console = logging.StreamHandler()
        logger.addHandler(console)
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
    return logger


# Initiate the logger object and set the log level to debug.
logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


# Set the chrome driver executable file path.
# Note: In order to use this script, make sure that the crome driver is in the project directory in chromedriver_win32 folder.
chromedriverpath = 'chromedriver_win32/chromedriver.exe'


class Browser:
    """
    Blueprint to define a browser object using selenium library.
    """
    def __init__(self, url, licenseType, licenseNo, licenseStatus, firstName, lastName,
                 city, state, county, zipcode):

        option = webdriver.ChromeOptions()
        option.add_argument("--incognito")
        self.url = url
        self.licenseType = licenseType
        self.licenseNo = licenseNo
        self.licenseStatus = licenseStatus
        self.firstName = firstName
        self.lastName = lastName
        self.city = city
        self.state = state
        self.county = county
        self.zipcode = zipcode
        self.browser = webdriver.Chrome(executable_path=chromedriverpath, chrome_options=option)
        self.browser.get(url)
        

    def get_browser_cookie(self):
        """Function to get the cookie from the web browser which be later used in the header for making requests. """
        request_cookies_browser = self.browser.get_cookies()[0]
        cookieName = request_cookies_browser.get('name')
        cookieValue = request_cookies_browser.get('value')
        cookie = f'{cookieName}={cookieValue}'
        return cookie

    def get_page_source(self):
        """Funtion to fill the form, search the page and return the page source."""
        
        if self.licenseType:
            licenseType = self.browser.find_element_by_id("t_web_lookup__license_type_name") 
            licenseType.send_keys(self.licenseType.lower())

        if self.licenseNo:
            licenseNo = self.browser.find_element_by_id("t_web_lookup__license_no")
            licenseNo.send_keys(self.licenseNo)

        if self.licenseStatus:
            licenseStatus = self.browser.find_element_by_id("t_web_lookup__license_status_name")
            licenseStatus.send_keys(self.licenseStatus.lower())

        if self.firstName:
            firstName = self.browser.find_element_by_id("t_web_lookup__first_name")
            firstName.send_keys(self.firstName.lower())

        if self.lastName:
            lastName = self.browser.find_element_by_id("t_web_lookup__last_name") 
            lastName.send_keys(self.lastName.lower())

        if self.city:
            city = self.browser.find_element_by_id("t_web_lookup__addr_city")
            city.send_keys(self.city.lower())

        if self.state:
            state = self.browser.find_element_by_id("t_web_lookup__addr_state")
            state.send_keys(self.state.lower())

        if self.county:
            county = self.browser.find_element_by_id("t_web_lookup__addr_county")
            county.send_keys(self.county.lower())

        if self.zipcode:
            zipcode = self.browser.find_element_by_id("t_web_lookup__addr_zipcode")
            zipcode.send_keys(self.zipcode)

        self.browser.find_element_by_name("sch_button").click()

        seleniumHtml = self.browser.page_source
        seleniumHtmlsoup = BeautifulSoup(seleniumHtml)
        return seleniumHtmlsoup


def extract_result_ids(soup):
    """This function takes the Details page data parsed by beautifoul soup.
       Extracts the result ids from the anchor tags.
       Return a list of result ids.
    """
    try:
        table = soup.find('table', id="datagrid_results")
        aTags = table.findAll('a')
        aTagsList = []
        for aTag in aTags:
            if aTag:
                tagId = aTag.get('href')
                r = re.compile(r"Details\'?([^']+)")
                m = r.search(tagId)
                if m:
                    match = m.group()
                    aTagsList.append(match)
        return aTagsList
    except Exception as err:
        raise err


def parse_license_detail(resultid, url):
    """
    This function takes the list of result ids extracted from anchor tags.
    Sends the request to get the details for that id.
    Extracts the attributes using beautifulsoup.
    Return the dictionary of the extracted information.
    """
    querystring = {
                "result": resultid
        }
    detailsUrl = url + resultid
    
    response = session.get(detailsUrl, data=querystring, headers=headers)

    soup = BeautifulSoup(response.text, "lxml")
    firstNameSpan = soup.find("span", id="_ctl27__ctl1_first_name").text
    middleNameSpan = soup.find("span", id="_ctl27__ctl1_m_name").text
    lastNameSpan = soup.find("span", id="_ctl27__ctl1_last_name").text
    licenseNoSpan = soup.find("span", id="_ctl36__ctl1_license_no").text
    licenseTypeSpan = soup.find("span", id="_ctl36__ctl1_license_type").text
    statusSpan = soup.find("span", id="_ctl36__ctl1_status").text
    originalIssuedDateSpan = soup.find("span", id="_ctl36__ctl1_issue_date").text
    expiryDateSpan = soup.find("span", id="_ctl36__ctl1_expiry").text
    renewedDateSpan = soup.find("span", id="_ctl36__ctl1_last_ren").text

    licenseResult = {"First Name": firstNameSpan, "Middle Name": middleNameSpan, "Last Name": lastNameSpan, 
            "License #": licenseNoSpan, "License Type": licenseTypeSpan, "Status": statusSpan,
            "Original Issued Date": originalIssuedDateSpan, "Expiry": expiryDateSpan, "Renewed": renewedDateSpan}
    return licenseResult
   

def get_license_details(url, urlSuffix, seleniumpagesoup, headers):
    """
    Note: This webpage return multiple pages depending on the amount of data returned by the search.
          By default it returns the data for first page. 
          For the rest of the pages it uses javascript post back to fetch and display the data i.e. Paginates data.

    Considering the notes above, this function:
        * First extracts the data from the first page.
        * Then sequentially iterates over the rest of the pages and extracts the data.
        * If there are no pages left, the execution terminates.
    """
    searchResultUrl = url + urlSuffix

    first_page_licence_detail_list = []
    next_pages_license_detail_list = []

    # This block is responsible to fetch, process the first page on search result and store the data in a list.
    try:
        first_page_result_ids = extract_result_ids(seleniumpagesoup)
        for resultid in first_page_result_ids:
            first_page_licence_detail_list.append(parse_license_detail(resultid=resultid, url=url))

        logger.info(f'Finished processing page 1.')
    except Exception as err:
        message = f'Failed while processing page 1. Error: {err}'
        logger.error(message)
        raise Exception(message)
    
    # This block is responsible to iterate over rest of the pages, extract data, and store it in the list.
    pageno = 2
    pageIndex = 1
    while True:
        try:
            pageAnchorTag = seleniumpagesoup.find('a', text='%d' % pageno)
            if not pageAnchorTag:
                break

            reMatchPostback = re.compile(r"__doPostBack\('([^']+)")
            reMatchHref = re.search(reMatchPostback, pageAnchorTag['href'])

            EVENTTARGET = reMatchHref.group(1)
            VIEWSTATE = seleniumpagesoup.select_one("#__VIEWSTATE")['value']
            EVENTVALIDATION = seleniumpagesoup.select_one("#__EVENTVALIDATION")['value']
            VIEWSTATEGENERATOR = seleniumpagesoup.select_one("#__VIEWSTATEGENERATOR")['value']

            formPagedata = {
                    "CurrentPageIndex": pageIndex,
                    "__EVENTTARGET": EVENTTARGET,
                    "__EVENTARGUMENT": "",
                    "__LASTFOCUS": "",
                    "__VIEWSTATE": VIEWSTATE,
                    "__VIEWSTATEGENERATOR": VIEWSTATEGENERATOR,
                    "__EVENTVALIDATION": EVENTVALIDATION
            }

            response = session.get(searchResultUrl, data=formPagedata, headers=headers)
            soup = BeautifulSoup(response.text, "lxml")

            # Get result ids from each page
            next_pages_result_id_ids = extract_result_ids(soup)
            for resultid in next_pages_result_id_ids:
                next_pages_license_detail_list.append(parse_license_detail(resultid=resultid, url=url))

            logger.info(f'Finished processing page {pageno}.')
            pageno += 1
            pageIndex += 1
        except Exception as err:
            message = f'Failed while processing page {pageno}. Error: {err}'
            logger.error(message)
            raise Exception(message)
    
    license_details_list = first_page_licence_detail_list + next_pages_license_detail_list
    return license_details_list

# Initiate the browser object with search parameters.
"""
Following search parameters can be supplied to intiate search object:

Example: 

licenseType = "Pharmacist"
licenseNo = "P4904"
licenseStatus = "Active"
firstName = "B"  # to search details of individual first name starting with B
lastName = "L" # to search details of individual last name starting with B
city = "Eden Prairie"
state = "MN"
county = "Hennepin"
zipcode = 55347

"""
licenseType  = 'Pharmacist'
licenseNo = None
licenseStatus = None
firstName = None
lastName = "L"
city = None
state = None
county = None
zipcode = None

browser = Browser(url=baseUrl, licenseType=licenseType, licenseNo=licenseNo, firstName=firstName, lastName=lastName,
licenseStatus=licenseStatus, city=city, state=state, county=county, zipcode=zipcode
)
cookies = browser.get_browser_cookie()

# Define header defination with cookie.
headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" 
            ,"Accept-Language": "en-US,en;q=0.5"
            ,"Content-Type": "application/x-www-form-urlencoded" 
            ,"Origin": "https://idbop.mylicense.com" 
            ,"Connection": "keep-alive" 
            ,"Referer": "https://idbop.mylicense.com/verification/" 
            ,"Cookie": cookies
            ,"Upgrade-Insecure-Requests": "1" 
        }


# Get the page source from selenium interaction with web page.
seleniumPageSoup = browser.get_page_source()


# Get the license details. This returns the array of dictionary containing the license details.
licenseDetails = get_license_details(
                                     url=baseUrl, urlSuffix=searchResultPageUrlSuffix, 
                                      seleniumpagesoup=seleniumPageSoup, headers=headers
                                   )


# Define the name of the file to save the data. The file will be generated in the project root directory if not already exists.
licence_detail_data_dump_file = 'license_details_using_selenium.json'


# Saves the data as json to the file.
with open(licence_detail_data_dump_file, 'w', encoding='utf-8') as f:
    json.dump(licenseDetails, f, ensure_ascii=False, indent=4)


