* This script is developed to scrape the license information of Pharmacist whole last name begins with L.
* The script performs following steps to scrape the data.

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
