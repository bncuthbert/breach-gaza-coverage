#!/usr/bin/env python
# coding: utf-8
"""
Tokenizes and lemmatizes every sentence in article lists, and checks for matches to fatal verbs and nouns.
NOTE: This was run on Dec 14th, 2023
"""

import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from newspaper import Article
import requests
import nltk
from nltk.stem import WordNetLemmatizer 
from scrape_post_articles import user_agent_header

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

# nltk token tags
VERBS = ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']
NOUNS = ['NN', 'NNS']

# verbs and nouns to check sentences for
FATAL_VERBS_PASSIVE = ['die', 'decease']
FATAL_VERBS_ACTIVE = ['kill', 'murder', 'shoot', 'assassinate', 'stab']
FATAL_VERBS_ACTIVE_SPECIFIC = ['behead', 'slaughter', 'execute', 'hang']
ALL_FATAL_VERBS = FATAL_VERBS_PASSIVE + FATAL_VERBS_ACTIVE + FATAL_VERBS_ACTIVE_SPECIFIC
FATAL_NOUNS = ['death', 'dead', 'deceased', 'fatality', 'murder', 'homicide', 'assassination', 'massacre', 'slaughter', 'corpse']

save_csv = True
globe_articles_path = '../data/globe_article_list.csv'
star_articles_path = '../data/star_article_list.csv'
post_articles_path = '../data/post_article_list.csv'
globe_sentences_path = '../data/globe_sentences_raw.csv'
star_sentences_path = '../data/star_sentences_raw.csv'
post_sentences_path = '../data/post_sentences_raw.csv'

def get_globe_sentences(url):
    """takes a globe article url and returns list of sentences"""
    article = Article(url)
    article.download()
    article.parse()

    text = article.text

    # deal with html formatting
    text = text.replace('.\n\n', '. ')
    text = text.replace('\n\n', '. ')
    
    return nltk.sent_tokenize(text)

def get_star_sentences(url):
    """takes a star article url and returns list of sentences"""
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'lxml')
    article_body = soup.find('div', attrs={'id': 'article-body'})
    text = ''

    for div in article_body.find_all('div', {'class': ['subscriber-preview', 'subscriber-only']}):
        if 'hidden-print' not in div['class']:
            try:
                text += ' ' + div.find('p').text
            except:
                pass
    
    return nltk.sent_tokenize(text)

def get_post_sentences(url):
    """takes a post article url and returns list of sentences"""
    html_text = se.get(url).text
    soup = BeautifulSoup(html_text, 'lxml')
    text = ''

    paragraphs = soup.find_all('p', class_='', attrs='')
    for paragraph in paragraphs:
        text += ' ' + paragraph.text
    
    return nltk.sent_tokenize(text)

def fatal_sentence_check(sentence, lemmatizer=WordNetLemmatizer(), verbs=VERBS, fatal_verbs=ALL_FATAL_VERBS, nouns=NOUNS, fatal_nouns=FATAL_NOUNS):
    """"tokenizes sentence into words, tags word position, lemmatizes verbs, and returns True if any verb matches `fatal_verbs` or `fatal_nouns`"""
    fatal = False
    words = nltk.word_tokenize(sentence)
    tagged = nltk.pos_tag(words)

    for tag in tagged:
        word = tag[0]
        pos = tag[1]

        if pos in verbs:
            lemma = lemmatizer.lemmatize(word, 'v')
            if lemma in fatal_verbs:
                fatal = True
        elif pos in nouns:
            lemma = lemmatizer.lemmatize(word, 'n')
            if lemma in fatal_nouns:
                fatal = True

    return fatal

if __name__ == "__main__":
    # Globe and Mail
    df = pd.read_csv(globe_articles_path)
    date_list, url_list, title_list, sentence_list, tag_list = [], [], [], [], []
    description = f'Extracting sentences from {len(df)} Globe and Mail articles...'
    pbar = tqdm(range(len(df)), desc=description)
    for i in pbar:
        try:
            sentences = get_globe_sentences(df.loc[i, 'url'])
            for sentence in sentences:
                if fatal_sentence_check(sentence):
                    date_list.append(df.loc[i, 'datetime'])
                    url_list.append(df.loc[i, 'url'])
                    title_list.append(df.loc[i, 'title'])
                    sentence_list.append(sentence)
                    tag_list.append(df.loc[i, 'tag'])
        except:
            print(f"Could not find {df.loc[i, 'url']}. Article may have moved.")

    description = f'Extracted sentences from {len(df)} Globe and Mail articles.'
    pbar.set_description(description)

    df_sentences = pd.DataFrame({'date': date_list, 'title': title_list, 'category': tag_list, 'url': url_list, 'sentence': sentence_list})
    df_sentences = df_sentences.drop_duplicates(('sentence')).reset_index(drop=True)
    print(f'{len(df_sentences)} extracted')

    if save_csv:
        df_sentences.to_csv(globe_sentences_path)
        print(f'Saved to {globe_sentences_path}')
    
    # Toronto Star
    df = pd.read_csv(star_articles_path)
    date_list, url_list, title_list, sentence_list, tag_list = [], [], [], [], []
    description = f'Extracting sentences from {len(df)} Toronto Star articles...'
    pbar = tqdm(range(len(df)), desc=description)
    for i in pbar:
        try:
            sentences = get_star_sentences(df.loc[i, 'url'])
            for sentence in sentences:
                if fatal_sentence_check(sentence):
                    date_list.append(df.loc[i, 'datetime'])
                    url_list.append(df.loc[i, 'url'])
                    title_list.append(df.loc[i, 'title'])
                    sentence_list.append(sentence)
                    tag_list.append(df.loc[i, 'tag'])
        except:
            print(f"Could not find {df.loc[i, 'url']}. Article may have moved.")

    description = f'Extracted sentences from {len(df)} Toronto Star articles.'
    pbar.set_description(description)

    df_sentences = pd.DataFrame({'date': date_list, 'title': title_list, 'category': tag_list, 'url': url_list, 'sentence': sentence_list})
    df_sentences = df_sentences.drop_duplicates(('sentence')).reset_index(drop=True)
    print(f'{len(df_sentences)} extracted')

    if save_csv:
        df_sentences.to_csv(star_sentences_path)
        print(f'Saved to {star_sentences_path}')

    # National Post
    with requests.Session() as se:
        se.headers = user_agent_header

    df = pd.read_csv(post_articles_path)
    date_list, url_list, title_list, sentence_list, tag_list = [], [], [], [], []
    description = f'Extracting sentences from {len(df)} National Post articles...'
    pbar = tqdm(range(len(df)), desc=description)
    for i in pbar:
        try:
            sentences = get_post_sentences(df.loc[i, 'url'])
            for sentence in sentences:
                if fatal_sentence_check(sentence):
                    date_list.append(df.loc[i, 'datetime'])
                    url_list.append(df.loc[i, 'url'])
                    title_list.append(df.loc[i, 'title'])
                    sentence_list.append(sentence)
                    tag_list.append(df.loc[i, 'tag'])
        except:
            print(f"Could not find {df.loc[i, 'url']}. Article may have moved.")

    description = f'Extracted sentences from {len(df)} National Post articles.'
    pbar.set_description(description)

    df_sentences = pd.DataFrame({'date': date_list, 'title': title_list, 'category': tag_list, 'url': url_list, 'sentence': sentence_list})
    df_sentences = df_sentences.drop_duplicates(('sentence')).reset_index(drop=True)
    print(f'{len(df_sentences)} extracted')

    if save_csv:
        df_sentences.to_csv(post_sentences_path)
        print(f'Saved to {post_sentences_path}')
