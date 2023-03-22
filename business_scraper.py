#!/usr/bin/python3
from bs4 import BeautifulSoup

import requests
import argparse
import os
import pickle

BASE_URL = 'https://www.tripadvisor.com'
USER_AGENT = ({'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
     AppleWebKit/537.36 (KHTML, like Gecko) \
     Chrome/90.0.4430.212 Safari/537.36',
    'Accept-Language': 'en-US, en;q=0.5'})

class Scraper:
  def __init__(self, url):
    self.url = url
    self.data = {'detail':[], 'city': [], 'full_address':[], \
       "name": [], 'phone_number': [], "review_count":[], 'stars': [], 'coords':[]}
    self.soup = self.content(self.url)

  def get_soup(self):
    return self.soup

  def get_data(self):
    return self.data

  def content(self, url, next_url=''):
    url += next_url
    response = requests.get(url, headers=USER_AGENT)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

  def find_href_tags(self, soup):
    tags = soup.findAll('a', {'class', 'Lwqic Cj b'})
    hrefs = []
    for href in tags:
      hrefs.append(href['href'])
    return hrefs

  def fetch_hrefs(self):
    print('###########################\nStarting to fetch HREFS\n###########################')
    hrefs = self.find_href_tags(self.soup)
    soup = self.soup
    while True:
      next_page_href = soup.find('a', {"class": "nav next rndBtn ui_button primary taLnk"}, href=True)
      if not next_page_href:
        print(f'fetched {len(hrefs)} points ...')
        break
      print(f"fetching next page hrefs on {next_page_href['href']} ...")
      soup = self.content(BASE_URL, next_page_href['href'])
      hrefs.extend(self.find_href_tags(soup))   
    
    return hrefs

  def info(self, href):
    print(f'fetching info on {href}')
    soup_info = self.content(BASE_URL, href)
    ##########
    # RETRIEVE NAME AND CITY
    ##########
    info_name_a_city = soup_info.findAll('li', {'class', 'breadcrumb'})
    name = info_name_a_city[4].text
    city = info_name_a_city[2].text.replace(u'\xa0', u' ')

    ##########
    # RETRIEVE ADDRESS AND PHONE NUMBER
    ##########
    try:
        info_address_a_phone_number = soup_info.findAll('div', {'class': "vQlTa H3"})[1].findAll('a')
        address = info_address_a_phone_number[0].text
        phone_number = info_address_a_phone_number[1].text
        if '+ Add phone' in phone_number:
            phone_number = None
    except:
        address, phone_number= None, None
    
    ##########
    # RETRIEVE DETAILS AND PRICE RANGE
    ##########
    detail = {}
    info = soup_info.findAll('div', {'class': 'BMlpu'})
    for tag in info:
        try:
            key = tag.find('div', {'class':'tbUiL b'}).text            
            value = tag.find('div', {'class': 'SrqKb'}).text
            detail[key.lower()] = value.lower()
        except:
            continue
            
    ##########
    # RETRIEVE REVIEWS
    ##########
    try:
        review = soup_info.find('div', {'class', 'QEQvp'}).text
        stars, review_count = review.replace(u'\xa0', u' ').split(' ')[:2]
    except:
        stars, review_count = None, None
    
    ##########
    # COORDINATES
    ##########
    script = soup_info.findAll('script', type='text/javascript')
    for s in script:
        check = s.text.find('"coords":')
        if check != -1:
            coords = s.text[check:check+29].split(':')[-1].replace('"', '').replace('}', '').replace(']', '')
    
    self.data['detail'].append(detail)
    self.data['city'].append(city)
    self.data['name'].append(name)
    self.data['full_address'].append(address)
    self.data['phone_number'].append(phone_number)
    self.data['review_count'].append(review_count)
    self.data['stars'].append(stars)
    self.data['coords'].append([float(coor) for coor in coords.split(',')[:2]]) 

  def fetch(self, hrefs):
    print('###########################\nStarting to fetch INFO\n###########################')
    for href in set(hrefs):
      self.info(href)

    print('saving data...')
    self.save()

  def save(self):
      os.makedirs('datasets', exist_ok=True)
      with open('datasets/kosovo_restaurant_reviews_g304082.pickle', 'wb') as handle:
        pickle.dump(self.data, handle, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Scraper')
  parser.add_argument('--url', help='trip advisor url to scrape restaurant data', default='https://www.tripadvisor.com/Restaurants-g304082-Kosovo.html')

  args = parser.parse_args()
  url = args.url

  scraper = Scraper(url)
  hrefs = scraper.fetch_hrefs()
  scraper.fetch(hrefs)
