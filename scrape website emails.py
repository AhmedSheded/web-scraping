from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import pandas as pd
import time
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.exceptions import ConnectionError

chrome_options = Options()
chrome_options.add_argument('--headless')
prefs = {'profile.managed_default_content_settings.javascript': 2, "profile.managed_default_content_settings.images": 2}
chrome_options.add_experimental_option("prefs", prefs)

url = str(input('Enter your URL: '))
url = url.split('?')[0]
StartPage = int(input("Enter your start page: "))
EndPage = int(input('Enter your end page: '))

driver_path = "/usr/bin/chromedriver"
email_regex = '''(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])'''


def GetDomains(url, StartPage, EndPage):
    print("Getting Domains ... ... ...")
    StartPage = StartPage - 1
    EndPage = EndPage - 1
    page = StartPage
    domains = []

    def FilterUrls(urls):
        urllist = []
        for url in urls:
            domain = urlparse(url).netloc
            urllist.append(domain)
        return urllist

    for i in range(StartPage, EndPage):
        site = url + "?page=" + str(page)
        driver = webdriver.Chrome(driver_path, options=chrome_options)
        driver.get(site)
        sites = driver.find_elements_by_xpath('//a[@class="website-link__item"]')

        urls = []
        for site in sites:
            urls.append(site.get_attribute('href'))

        for i in FilterUrls(urls):
            domains.append("https://" + i)

        driver.close();
        page = page + 1

    return domains


def validate_existence(domains):
    print('Clear invalid domains')
    new_domains = []
    for domain in domains:
        try:
            response = requests.get(f'{domain}', timeout=50)
        except ConnectionError:
            print(f'Domain {domain} [---]')
        else:
            new_domains.append(domain)
    return new_domains


domains = GetDomains(url, StartPage, EndPage)

domains = validate_existence(domains)

print('length of domains: ', len(domains))


def get_dom_sub_page(domain):
    reqs = requests.get(domain)
    soup = BeautifulSoup(reqs.text, 'html.parser')
   
    domain_sub_pages = []
    for link in soup.find_all('a'):
        domain_sub_pages.append(link.get('href'))

    #     filter output
    domain_sub_pages = list(filter(None, domain_sub_pages))
    domain_sub_pages = list(dict.fromkeys(domain_sub_pages))

    pages = [domain]
    for dom in domain_sub_pages:
        if dom[:len(domain)] != domain:
            dom = domain+dom	
        if 'contact' in dom or 'connect' in dom:
            pages.append(dom)

    pages = pages[:4]
    return pages


def get_emails(email):
    sub_domains = get_dom_sub_page(email)
    list_of_emails = []
    for i in range(len(sub_domains)):
        driver = webdriver.Chrome(driver_path, options=chrome_options)
        driver.set_page_load_timeout(10)
        try:
            driver.get('view-source:'+sub_domains[i])
        except:
            pass
        page_source = driver.page_source
        driver.close()
        for re_match in re.finditer(email_regex, page_source):
            list_of_emails.append(re_match.group())

        #         filter the list
        list_of_emails = list(dict.fromkeys(list_of_emails))
        delete = ['/', 'username', 'png', 'jpg', '=', 'example', '@gmail', '@mail']
        for de in delete:
            list_of_emails = [x for x in list_of_emails if de not in x]


        not_wanted = ['support', 'employee', 'media',
                  'finance', 'news', 'update', 'labs', 'bills',
                  'dispute', 'complain','press', 'policy', 'career', 'sale', 'hr']

        for i in not_wanted:
            if len(list_of_emails) > 2:
                list_of_emails = [x for x in list_of_emails if i not in x]

        contact = [x for x in list_of_emails if 'contact' in x]
        if len(contact) > 0:
            list_of_emails = contact

    return list_of_emails


emails = []
for i in range(len(domains)):
    print("get emails for site: ", i+1, domains[i])
    email = get_emails(domains[i])
    emails.append(email)
    print(email)

list_of_domains = []
list_of_emails = []
list_of_not_found = []

for i in range(len(emails)):
    if len(emails[i]) > 0:
        for l in range(len(emails[i])):
            list_of_domains.append(domains[i])
            list_of_emails.append(emails[i][l])
    else:
        list_of_not_found.append(domains[i])

found = len(domains)-len(list_of_not_found)
not_found = len(list_of_not_found)
percent = found/len(domains)*100
percent=round(percent)
print("found: ", found, " of Domains")
print('Not found: ', not_found,'of Domains')
print("Accuracy= ", percent,"%")
print("All Domains is: ", len(domains))

df = pd.DataFrame({'emails': list_of_emails, 'domains': list_of_domains})
df_lost = pd.DataFrame({'domains': list_of_not_found})
df.to_csv('from- '+str(StartPage)+' -to- '+str(EndPage)+' -emails.csv', index=False)
df_lost.to_csv('from- '+str(StartPage)+' -to- '+str(EndPage)+' -domains_not_found.csv', index=False)

