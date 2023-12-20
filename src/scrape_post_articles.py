#!/usr/bin/env python
# coding: utf-8
"""
Uses BeautifulSoup to scrape metadata for National Post articles relevant to the war on Gaza. 
NOTE: The "start_results" were manually specified on Dec 14th, 2023. If running later, this will require adjustment.
"""

import requests
import time
import re
import string
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from newspaper import Article
import nltk
from nltk.stem import WordNetLemmatizer 
import math
import datetime

POST_URL = 'https://nationalpost.com'

save_csv = False
filename = '../data/post_article_list.csv'

keywords = ['israel', 'hamas', 'gaza', 'palestine', 'palestinian']
date_start = '2023-10-07'
date_end = '2023-11-27'
keep_tags = ['News', 
             'Canada', 
             'NP Comment',
             'Israel & Middle East', 
             'World',
             'Canadian Politics', 
             'Toronto']

# the post only allows searching for fixed intervals (1 month, 1 year, etc) so I manually specified a result count that includes Oct 7th
# could just start at 0 but that would search the entire post archive and take ages
start_results = [1930, 340, 510, 280, 960]

# the post needs user-agent for requests
user_agent_header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en"
    }

if __name__ == "__main__":
    with requests.Session() as se:
        se.headers = user_agent_header

    date_list = []
    title_list = []
    url_list = []
    tag_list = []

    for keyword, start_result in zip(keywords, start_results):
            search_url = f'https://nationalpost.com/search/?search_text={keyword}&date_range=-365d&sort=asc&from={start_result}'

            # make soup for first page
            html_text = se.get(search_url).text
            soup = BeautifulSoup(html_text, 'lxml')

            # get number of search results
            n_results_str = soup.find('span', class_='search-heading').text
            n_results = int(n_results_str.split(' ')[2])
            results_per_page = 10 # post always displays 10 / page
            n_pages = int(soup.find('span', {'aria-current': 'true'}).text.split()[2])
            start_page = int(soup.find('span', {'aria-current': 'true'}).text.split()[0])


            # loop through all results pages to get article metadata
            description = f'Scraping {n_results - start_result} search results for keyword: "{keyword}"...'
            pbar = tqdm(range(n_pages - start_page + 1), desc=description)

            for i in pbar:
                    result_url = f'https://nationalpost.com/search/?search_text={keyword}&date_range=-365d&sort=asc&from={start_result + (i * results_per_page)}'

                    # make soup
                    html_text = se.get(result_url).text
                    soup = BeautifulSoup(html_text, 'lxml')
                    
                    # get all article info
                    articles = soup.find_all('div', class_='article-card__details')

                    for article in articles:
                            title_list.append(article.find('span', class_='article-card__headline-clamp').text)
                            url_list.append(POST_URL + article.find('a')['href'])
                            tag_list.append(article.find('span', {'data-evt-skip-click': 'true'}).text)

                            # dates are in recency-dependent strings
                            date_string = article.find('span', class_='article-card__time-clamp').text.replace(',', '')
                            if date_string.find('day') != -1:
                                    days_ago = int(re.search(r'\d+', date_string).group())
                                    date = pd.Timestamp(datetime.datetime.now() - datetime.timedelta(days=days_ago + 1))
                            elif date_string.find('hour') != -1:
                                    hours_ago = int(re.search(r'\d+', date_string).group())
                                    date = pd.Timestamp(datetime.datetime.now() - datetime.timedelta(hours=hours_ago + 1))
                            elif date_string.find('minute') != -1:
                                    mins_ago = int(re.search(r'\d+', date_string).group())
                                    date = pd.Timestamp(datetime.datetime.now() - datetime.timedelta(minutes=mins_ago + 1))
                            else:
                                    date = pd.Timestamp(datetime.datetime.strptime(date_string, ' %B %d %Y '))
                            date_list.append(date)

            description = f'Scraped {n_results - start_result} search results for keyword: "{keyword}"'
            pbar.set_description(description)

    df = pd.DataFrame({'datetime': date_list, 'title': title_list, 'tag': tag_list, 'url': url_list}).drop_duplicates()
    df = df[df['datetime'] >= date_start]
    df = df[df['datetime'] <= date_end]
    df.sort_values(by='datetime', inplace=True)
    df = df[df['tag'].isin(keep_tags)]

    # filter out financial post urls
    df['bad_url'] = False
    for i in range(len(df)):
        if df.iloc[i]['url'].find('financialpost') != -1:
            df.loc[i, 'bad_url'] = True 

    df = df[df['bad_url'] == False]
    df.drop(columns='bad_url', inplace=True)

    df.reset_index(drop=True, inplace=True)
    print(f'Scraped metadata for {len(df)} articles')

    if save_csv:
        df.to_csv(filename)
        print(f'Saved to {filename}')