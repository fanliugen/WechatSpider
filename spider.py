import requests
from urllib.parse import urlencode
from pyquery import PyQuery as pq
import pymongo
from config import *
from requests.exceptions import ConnectionError
from lxml.etree import XMLSyntaxError
import re

base_url = 'http://weixin.sogou.com/weixin?'

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]

proxy = None

headers = {
    'Cookie': 'SUID=A49CFD722B0B940A000000005875993C; SUV=1484101936780494; pgv_pvi=5518991360; ssuid=5620749808; usid=O3kaZ5WSKq3GVPTC; dt_ssuid=7597244000; IPLOC=CN1100; ABTEST=2|1533519020|v1; weixinIndexVisited=1; ld=HZllllllll2z@UvLlllllVHo5hklllllWTJlnyllllylllllxklll5@@@@@@@@@@; LSTMV=251%2C73; LCLKINT=150789; JSESSIONID=aaa8PJ9iRLLts72eZ86tw; PHPSESSID=c6l8t0fmjobmhj29e50ekrt7o6; SUIR=3AFE9A93E9EC9A53D0A01711E91A6D2D; SNUID=6A1FF7780A0E79D330DABBB30B3D479C; ppinf=5|1533649849|1534859449|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToyNzolRTclOTQlOUYlRTUlOTElQkQlRTYlQTAlOTF8Y3J0OjEwOjE1MzM2NDk4NDl8cmVmbmljazoyNzolRTclOTQlOUYlRTUlOTElQkQlRTYlQTAlOTF8dXNlcmlkOjQ0Om85dDJsdURzdFZqbnZ6ZGJUaENlZkhIT1EwUE1Ad2VpeGluLnNvaHUuY29tfA; pprdig=fxcbr61Ult3XIEKmLIcGfKqcy0GnOusw5WuMLVeGoqOZru6KzjsFFGvNIxu2UgcwrN7zr-tcszzpM7vrRKkmgOR0GK79zNgwCdzbgJ7xD1mmbuRe7V8ma6iwiZYpEr5D7rMsd01LKVwEHCcPXIcqbAGgPMlpks0JMxUxwRhRotk; sgid=13-36459413-AVtpo7mNgJF2QTOSNMp7RMQ; ppmdig=15336498490000008b7164abd94ffdab834deea0960f3b6b; sct=43',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.162 Safari/537.36'
}

def get_proxy():
    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

#http://weixin.sogou.com/weixin?query=%E5%96%B7%E7%A0%82%E6%9C%BA&type=2&page=18&ie=utf8&p=0
def get_index(keyword,page):
    data = {
        'query':keyword,
        'page':page,
        'type':'2',
    }
    queries = urlencode(data)
    url = base_url + queries

    html = get_index_html(url)
    return html
    # try:
    #     response = requests.get(url,headers=headers)
    #     if response.status_code == 200:
    #         # print(response.text)
    #         return response.text
    #     return None
    # except ConnectionError:
    #     return None

def get_index_html(url,count=1):
    print('Crawling',url)
    print('Trying Count',count)
    global proxy
    if count >MAX_COUNT:
        print('Tried too Many Counts')
        return None
    try:
        if proxy:
            proxies={
                'http':'http://' + proxy
            }
            response = requests.get(url,allow_redirects=False,headers = headers,proxies=proxies)
        else:
            response = requests.get(url,allow_redirects=False,headers = headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            print('302')
            proxy = get_proxy()

            if proxy:
                print('using proxy',proxy)
                return get_index_html(url)
            else:
                print('Get Proxy Failed')
                return None
    except ConnectionError as e:
        print('Errow Occurred',e.args)
        proxy = get_proxy()
        count += 1
        return get_index_html(url,count)



def parse_index_page(html):
    doc = pq(html)
    items = doc('.txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

def get_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return  None

def parse_detail_page(html):
    try:
        doc = pq(html)
        title = doc('.rich_media_title').text()
        content = doc('#js_content').text()
        pattern = re.compile('var publish_time =(.*?)\|\| \"\"\;',re.S)
        date_raw = re.findall(pattern,html)[0]
        date =re.sub('\"','',date_raw).strip()
        nickname = doc('#js_profile_qrcode > div > strong').text()
        wechatId = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
        return {
            'title':title,
            'content':content,
            'date':date,
            'nickname':nickname,
            'wenchat':wechatId,
        }
    except XMLSyntaxError:
        return None
def save_to_mongo(data):
    condition={'title':data['title']}
    if db['articles'].update(condition,{'$set':data},True):
        print('Save to Mongo',data['title'])
    else:
        print('Save to Mongo Failed',data['title'])


def main():
    for page in range(1,51):
        html=get_index(KEYWORD,page)
        if html:
            article_urls = parse_index_page(html)
            if article_urls:
                for article_url in article_urls:
                    article_html = get_detail(article_url)
                    if article_html:
                        article_data = parse_detail_page(article_html)
                        if article_data:
                            save_to_mongo(article_data)




if __name__ == '__main__':
    main()