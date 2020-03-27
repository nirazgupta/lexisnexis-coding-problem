import requests
from bs4 import BeautifulSoup
import csv
import re
import logging
import logging.handlers
import json

# license verification urls
# search page url : "https://idbop.mylicense.com/verification/Search.aspx"
# search result page url : "https://idbop.mylicense.com/verification/SearchResults.aspx"
# license details page url : "https://idbop.mylicense.com/verification"

baseUrl = "https://idbop.mylicense.com/verification/"
searchPageUrlSuffix = "Search.aspx"
searchResultPageUrlSuffix = "SearchResults.aspx"

# Initiate a request session object
session = requests.session()

# Header definition to 
headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0" 
            ,"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8" 
            ,"Accept-Language": "en-US,en;q=0.5"
            ,"Content-Type": "application/x-www-form-urlencoded" 
            ,"Origin": "https://idbop.mylicense.com" 
            ,"Connection": "keep-alive" 
            ,"Referer": "https://idbop.mylicense.com/verification/" 
            ,"Cookie": "ASP.NET_SessionId=ye1eq3z5zvd01drkn4tkmasa" 
            ,"Upgrade-Insecure-Requests": "1" 
        }


def get_logger(appname):
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


logger = get_logger(__name__)
logger.setLevel(logging.DEBUG)


def extract_result_ids(soup):
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


def get_license_detail(resultid, url):
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


def get_initial_search_params(url, urlSuffix):
    searchUrl = url + urlSuffix

    response = session.get(searchUrl)
    
    if response.status_code == 200:
        try:
            soup = BeautifulSoup(response.text, "lxml")

            VIEWSTATE = soup.select_one("#__VIEWSTATE")['value']
            EVENTVALIDATION = soup.select_one("#__EVENTVALIDATION")['value']
            VIEWSTATEGENERATOR = soup.select_one("#__VIEWSTATEGENERATOR")['value']

            searchresult_params = {
                "VIEWSTATE": VIEWSTATE,
                "EVENTVALIDATION": EVENTVALIDATION,
                "VIEWSTATEGENERATOR": VIEWSTATEGENERATOR
            }
            return searchresult_params
        except Exception as err:
            raise err
    else:
        raise Exception(f'Error while calling search.aspx. {response.status_code} ')


def get_searchresult_initialpage(url, urlSuffix, stateParams, searchParams, headers):
    searchResultUrl = url + urlSuffix

    viewstate = stateParams.get('VIEWSTATE')
    viewstategenerator = stateParams.get('VIEWSTATEGENERATOR')
    eventvalidation = stateParams.get('EVENTVALIDATION')

    first_name = searchParams.get('first_name')
    last_name = searchParams.get('last_name')
    license_type = searchParams.get('license_type')
    license_no = searchParams.get('license_no')
    city = searchParams.get('addr_city')
    state = searchParams.get('state')
    license_status = searchParams.get('license_status')
    country = searchParams.get('addr_country')
    zipcode = searchParams.get('addr_zipcode')


    formdata = {
                "__EVENTTARGET": "t_web_lookup__license_type_name",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": viewstategenerator,
                "__EVENTVALIDATION": eventvalidation,
                "t_web_lookup__first_name": first_name,
                "t_web_lookup__license_type_name": license_type,
                "t_web_lookup__last_name": last_name,
                "t_web_lookup__addr_city": city,
                "t_web_lookup__license_no": license_no,
                "t_web_lookup__addr_state": state,
                "t_web_lookup__license_status_name": license_status,
                "t_web_lookup__addr_county": country,
                "t_web_lookup__addr_zipcode": zipcode,
                "sch_button": "Search"
        }

    logger.info(f'Search arguments: {formdata}')

    searchResultResponse = session.get(searchResultUrl, data=formdata, headers=headers)

    if searchResultResponse.status_code == 200:
        try:
            soup = BeautifulSoup(searchResultResponse.text, "lxml")
            return soup
        except Exception as err:
            message = f'Failed while searching data with parameters. Error: {err}'
            logger.error(message)
            raise Exception(message)
    else:
        raise Exception(f'Error while calling searchResult.aspx. {searchResultResponse.status_code}')
    

def get_license_details(url, urlSuffix, firstpagesoup, headers):
    searchResultUrl = url + urlSuffix

    first_page_licence_detail_list = []
    next_pages_license_detail_list = []

    try:
        first_page_result_ids = extract_result_ids(firstpagesoup)
        for resultid in first_page_result_ids:
            first_page_licence_detail_list.append(get_license_detail(resultid=resultid, url=url))

        logger.info(f'Finished processing page 1.')
    except Exception as err:
        message = f'Failed while processing page 1. Error: {err}'
        logger.error(message)
        raise Exception(message)
    
    pageno = 2
    pageIndex = 1
    while True:
        try:
            pageAnchorTag = firstpagesoup.find('a', text='%d' % pageno)
            if not pageAnchorTag:
                break

            reMatchPostback = re.compile(r"__doPostBack\('([^']+)")
            reMatchHref = re.search(reMatchPostback, pageAnchorTag['href'])

            EVENTTARGET = reMatchHref.group(1)
            VIEWSTATE = firstpagesoup.select_one("#__VIEWSTATE")['value']
            EVENTVALIDATION = firstpagesoup.select_one("#__EVENTVALIDATION")['value']
            VIEWSTATEGENERATOR = firstpagesoup.select_one("#__VIEWSTATEGENERATOR")['value']

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
                next_pages_license_detail_list.append(get_license_detail(resultid=resultid, url=url))

            logger.info(f'Finished processing page {pageno}.')
            pageno += 1
            pageIndex += 1
        except Exception as err:
            message = f'Failed while processing page {pageno}. Error: {err}'
            logger.error(message)
            raise Exception(message)
    
    license_details_list = first_page_licence_detail_list + next_pages_license_detail_list
    return license_details_list

searchPageUrlSuffix = "Search.aspx"
searchResultPageUrlSuffix = "SearchResults.aspx"

# Configure inputs for search.
import json
import argparse
from urllib.parse import unquote

# Set up search arguments
searchParams = {
                "first_name": "",
                "license_type_name": "Pharmacist",
                "last_name": "L",
                "addr_city": "",
                "license_no": "",
                "addr_state": "",
                "license_status_name": "",
                "addr_county": "",
                "addr_zipcode": ""
                }

# Get parameters to begin search
searchresult_params = get_initial_search_params(url=baseUrl, urlSuffix=searchPageUrlSuffix)

searchResultInitialPageData = get_searchresult_initialpage(
                                                            url=baseUrl, stateParams=searchresult_params, searchParams=searchParams,
                                                            urlSuffix=searchResultPageUrlSuffix, headers=headers
                                                          )

licenseDetails = get_license_details(
                                        url=baseUrl, urlSuffix=searchResultPageUrlSuffix, 
                                        firstpagesoup=searchResultInitialPageData, headers=headers
                                    )

licence_detail_data_dump_file = 'license_details.json'
with open(licence_detail_data_dump_file, 'w', encoding='utf-8') as f:
    json.dump(licenseDetails, f, ensure_ascii=False, indent=4)


