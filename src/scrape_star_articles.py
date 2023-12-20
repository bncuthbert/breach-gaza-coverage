#!/usr/bin/env python
# coding: utf-8
"""
Uses BeautifulSoup to scrape metadata for Toronto Star articles relevant to the war on Gaza. 
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

STAR_URL = 'https://www.thestar.com'

save_csv = False
filename = '../data/star_article_list.csv'

keywords = ['israel', 'hamas', 'gaza', 'palestinian', 'palestine']
date_start = '2023-10-07'
date_end = '2023-11-27'
keep_tags = ['Canada',
             'Middle East', 
             'World',
             'Politics',
             'Contributors',
             'News', 
             'Opinion']

if __name__ == "__main__":
    # loop through search results for every keyword
    results_per_page = 100
    start_result = 0
    date_list = []
    title_list = []
    url_list = []
    tag_list = []

    for keyword in keywords:
        search_url = f'https://www.thestar.com/search/?f=html&q={keyword}&d1={date_start}&d2={date_end}&t=article&s=start_time&sd=desc&l={results_per_page}&nsa=eedition&app%5B0%5D=editorial&o={start_result}'
        
        # make soup for first page
        html_text = requests.get(search_url).text
        soup = BeautifulSoup(html_text, 'lxml')

        # get number of search results
        n_results_str = soup.find('label', class_='search-revamp').text
        n_results = int(n_results_str.split(' ')[0])
        n_pages = int(math.ceil(n_results / results_per_page))

        # loop through all results pages to get article metadata
        description = f'Scraping {n_results} search results for keyword: "{keyword}"...'
        pbar = tqdm(range(n_pages), desc=description)
        
        for i in pbar:
            start_result = i * results_per_page
            result_url = f'https://www.thestar.com/search/?f=html&q={keyword}&d1={date_start}&d2={date_end}&t=article&s=start_time&sd=desc&l={results_per_page}&nsa=eedition&app%5B0%5D=editorial&o={start_result}'

            # make soup
            html_text = requests.get(result_url).text
            soup = BeautifulSoup(html_text, 'lxml')
            
            # get all article info
            articles = soup.find_all('article')

            for article in articles:
                article_info = article.find('a', class_='tnt-asset-link')
                url_list.append(STAR_URL + article_info['href'])
                title_list.append(article_info['aria-label'])
                date_string = article.find('time')['datetime']
                date_list.append(pd.Timestamp(datetime.datetime.fromisoformat(date_string[:-6])))

                try:
                    tag_list.append(article.find('span', class_='tnt-flag').text.replace('\n', ''))
                except: # some articles have weird tags
                    tag_list.append(article.find('span').text)

        description = f'Scraped {n_results} search results for keyword: "{keyword}"'
        pbar.set_description(description)

    df = pd.DataFrame({'datetime': date_list, 'title': title_list, 'tag': tag_list, 'url': url_list}).drop_duplicates().reset_index(drop=True)

    # try filtering based on relevant metadata keywords (these are an inconsistent mess)
    relevant_keywords = ['gaza', 'gaza_strip', 'gazaisrael_conflict', 'hamas', 'israel', 'israeli', 'israelipalestinian_conflict', 
                         'jerusalem', 'palestine', 'palestinian', 'palestinian_territory', 'palestinians', 'tel_aviv', 'west_bank', 
                         'war', 'antisemitism', 'jew', 'jewish']
    all_keywords = []
    match_list = [] 

    pbar = tqdm(range(len(df)), desc=f'Checking keywords for {len(df)} articles')
    for i in pbar:
        url = df.iloc[i]['url']
        html_text = requests.get(url).text
        soup = BeautifulSoup(html_text, 'lxml')

        # fix article tags while we're here
        df.loc[i, 'tag'] = soup.find_all('span', {'itemprop': 'name'})[-1].text

        # extract keywords
        article_keywords_string = soup.find('meta', attrs={'name': 'keywords'})['content']
        article_keywords = article_keywords_string.replace(',', '').split(' ')

        # check for relevant meta keywords
        match = (any(map(lambda v: v in article_keywords, relevant_keywords)))
        
        # if no kw match, check article title
        if not match:
            title = df.iloc[i]['title'].lower()
            title_split = re.split("[" + string.punctuation + " ]+", title)
            match = (any(map(lambda v: v in title_split, relevant_keywords)))

        for keyword in article_keywords:
            all_keywords.append(keyword)

        match_list.append(match)

    df['kw_match'] = match_list
    df = df[df['kw_match']]
    df.drop(columns='kw_match', inplace=True)
    df = df[df['tag'].isin(keep_tags)]
    df = df.sort_values('datetime').reset_index(drop=True)
    print(f'Scraped metadata for {len(df)} articles')
    
    if save_csv:
        df.to_csv(filename, index=False)
        print(f'Saved to {filename}')