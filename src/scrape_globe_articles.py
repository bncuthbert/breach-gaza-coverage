#!/usr/bin/env python
# coding: utf-8
"""
Uses BeautifulSoup and Selenium to scrape metadata for all articles on the Globe and Mail's "Israel-Hamas war" topic page. 
NOTE: The topic page now prevents scrolling to the beginning of the topic. Scraping was initially done on Nov. 27th, 2023 before this was an issue.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import datetime
import pandas as pd

GLOBE_URL = 'https://www.theglobeandmail.com'
TOPIC_URL = 'https://www.theglobeandmail.com/topics/israel-hamas-war/'

save_csv = False
filename = '../data/globe_article_list.csv'

if __name__ == "__main__":
    # set selenium options and launch webdriver
    options = Options()
    b = webdriver.Chrome(options=options)
    b.set_page_load_timeout(15)

    # load topic page and find "load more" button
    finished = 0
    while finished == 0:
        try:
            b.get(TOPIC_URL)
            finished = 1
        except:
            time.sleep(5)

    b.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    button = b.find_element(By.CLASS_NAME, 'c-article-feed-load-more__button')

    # click "load more" until we can't anymore
    count = 0
    while True:
        try:
            b.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            button.click()
            count += 1
            time.sleep(1)
        except:
            NoSuchElementException
            break

    # make soup
    full_page = b.page_source
    b.close()
    soup = BeautifulSoup(full_page, 'lxml')

    # loop through all articles and collect article name, url, date, and tag
    article_list = soup.find('div', class_='article-list-grid-wrap')
    articles = article_list.find_all('div', class_='c-card')

    date_list = []
    title_list = []
    url_list = []
    tag_list = []

    for article in articles: 
        date_string = article.find('time')['datetime']
        date_list.append(pd.Timestamp(datetime.datetime.fromisoformat(date_string[:-1])))
        title_list.append(article.find('div', class_='c-card__hed-text text-pb-9').text)
        url_list.append(GLOBE_URL + article.find('a')['href'])
        tag_list.append(article.find('span').text)

    # compile dataframe and save
    df = pd.DataFrame({'datetime': date_list, 'title': title_list, 'tag': tag_list, 'url': url_list})
    print(f'Scraped metadata for {len(df)} articles')

    if save_csv:
        df.to_csv(filename, index=False)
        print(f'Saved to {filename}')