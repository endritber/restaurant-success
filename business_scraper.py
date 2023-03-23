#!/usr/bin/python3
from bs4 import BeautifulSoup
import requests
import argparse
import os
import pickle
import uuid
import time
from datetime import datetime
from tqdm import tqdm

BASE_URL = 'https://www.tripadvisor.com'
USER_AGENT = ({'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
     AppleWebKit/537.36 (KHTML, like Gecko) \
     Chrome/90.0.4430.212 Safari/537.36',
    'Accept-Language': 'en-US, en;q=0.5'})

class Scraper:
  def __init__(self, url):
    self.url = url
    self.data = {'business_id': [], 'business_name': [], 'categories':[],
                'city': [], 'full_address':[], 'display_phone': [],
                'review_count':[], 'stars': [], 'price_tag':[], 'is_claimed': [],
                'is_closed': [], 'coordinates':[], 'image': [], 'url': []}
    self.reviews = {'user_id': [], 'business_id': [], 'review_id':[],
                    'review_date':[], 'review_title':[], 'review_text':[],
                    'rating':[], 'votes':[]}
    self.soup = self.content(self.url)

  def content(self, url, next_url=''):
    url += next_url
    for attempt in range(3):
      try:
          response = requests.get(url, headers=USER_AGENT)
          break
      except requests.exceptions.ChunkedEncodingError:
          time.sleep(1)
    else:
      print(f"Failed to retrieve {url}")

    # create content  
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
  
  def fetch_info(self, soup_info):
    #retrieve business name information
    business_name = soup_info.find('h1', {'data-test-target': 'top-info-header'})
    business_name = business_name.text if business_name is not None else None

    # retrieve city information
    breadcrumb = soup_info.findAll('li', {'class', 'breadcrumb'})    
    city = breadcrumb[2].text.replace(u'\xa0', u' ')
    
    # retrieve location information
    location = soup_info.findAll('div', {'class': "vQlTa H3"})
    full_address, display_phone = None, None
    if location is not None:
      if len(location) > 1:
        location = location[1].findAll('a')
        full_address = location[0].text
        display_phone = location[1].text
        if '+ Add phone' in display_phone:
              display_phone = None

    # retrieve price tag and categories
    details = soup_info.find_all('a', {'class': 'dlMOJ'})
    price_tag = 'No price tag'
    categories = []
    if len(details) > 0:
       for tag in details:
          if '$' in tag.text:
             price_tag = tag.text
          else:
             categories.append(tag.text)

    # check elsewhere class if no category above found
    if len(categories) == 0:   
      categories = []
      info = soup_info.findAll('div', {'class': 'BMlpu'})
      for tag in info:
          try:
              key = tag.find('div', {'class':'tbUiL b'}).text
              if key.lower() != 'cuisines':
                continue
              value = tag.find('div', {'class': 'SrqKb'}).text
              categories.append(value)
          except:
              continue
       
    # retrieve business (restaurant) review count and average stars
    stars = soup_info.find('span', {'class', 'ZDEqb'})
    stars = stars.text if stars is not None else '0.0'

    review_count = soup_info.find('a', {'class': 'IcelI' })
    review_count = review_count.text.split(' ')[0] if review_count is not None else '0' 

    # retrieve business coordinates
    script = soup_info.findAll('script', type='text/javascript')
    coordinates = None
    for s in script:
        check = s.text.find('"coords":')
        if check != -1:
            coordinates = s.text[check:check+29].split(':')[-1].replace('"', '').replace('}', '').replace(']', '').replace(')', '')
            coordinates = [float(coor) for coor in coordinates.split(',')[:2]]

    # check if business is claimed
    claimed = soup_info.find('div', {"class": "XAnbq _S"})
    is_claimed = False if claimed is None else True

    #get image about business
    #TODO: decode base64 img source
    image = soup_info.find('img', {'class': 'basicImg'})
    if image is not None:
       image = image['src']

    #TODO: is it correct?
    is_closed = soup_info.find('span', {'class': 'mMkhr'})
    if is_closed is not None:
      check = is_closed.text.split(':')
      check = [e.replace(u'\xa0', u' ') for e in check]
      if check[0].strip() == 'Open now':
        is_closed = False
      elif check[0].strip() == 'Closed now':
         hours = ''.join(check[-3:]).split('-')
         try:
          left, right = hours
          left = left.strip()
          right = right.strip()
          left = left[:2] + ':' + left[2:]
          right = right[:2] + ':' + right[2:]
          left = datetime.strptime(left, '%I:%M %p').hour
          right = datetime.strptime(right, '%I:%M %p').hour
          if right in range(6):
              right = 24
          now = datetime.now().hour
          if left < now < right:
              is_closed = True
          else:
              is_closed = False
         except:
            is_closed = True
      else:
         is_closed = True
    else:
      if int(review_count.strip()) > 0:
         is_closed = False
      else:
         is_closed = True

    return business_name, categories, city, full_address, display_phone, review_count, stars, price_tag, coordinates, is_claimed, is_closed, image 
    
  def fetch_reviews_and_save(self, business_id, soup_info):
    reviews = soup_info.findAll('div', {'class':"prw_rup prw_reviews_review_resp"})
    if reviews is not None:
      for review in reviews:

        user_id = review.find('div', {'class': 'memberOverlayLink clickable'})
        user_id = user_id['id'] if user_id is not None else None

        review_id = review.find('div', {"class": "reviewSelector"})['data-reviewid']
        review_text = review.find('p', {'class':"partial_entry"}).text.strip()
        review_date = review.find('span', {'class': 'ratingDate'})['title']
        review_title = review.find('span', {'class', 'noQuotes'}).text
        buble_tag = review.select_one(":scope span[class*='bubble']")
        rating = buble_tag["class"][-1].split("_")[-1]
        
        votes = review.find('span', {'class':"numHelp"})
        votes = votes.text if votes is not None else '0'
        
        self.reviews['user_id'].append(user_id)
        self.reviews['business_id'].append(business_id)
        self.reviews['review_id'].append(review_id)
        self.reviews['review_text'].append(review_text)
        self.reviews['review_date'].append(review_date)
        self.reviews['review_title'].append(review_title)
        self.reviews['rating'].append(rating)
        self.reviews['votes'].append(votes)      
      
  def fill(self, href):
    soup_info = self.content(BASE_URL, href)
    business_id = uuid.uuid4()

    business_name, categories, city, full_address, \
    display_phone, review_count, stars, price_tag, \
    coordinates, is_claimed, is_closed, image = self.fetch_info(soup_info)
  
    # Fill Business Data
    self.data['business_id'].append(business_id)
    self.data['business_name'].append(business_name)
    self.data['categories'].append(categories)
    self.data['city'].append(city)
    self.data['full_address'].append(full_address)
    self.data['display_phone'].append(display_phone)
    self.data['review_count'].append(review_count)
    self.data['stars'].append(stars)
    self.data['price_tag'].append(price_tag)
    self.data['coordinates'].append(coordinates) 
    self.data['is_claimed'].append(is_claimed)
    self.data['is_closed'].append(is_closed)
    self.data['url'].append(BASE_URL+href)
    self.data['image'].append(image)

    # Fill Reviews Data
    self.fetch_reviews_and_save(business_id, soup_info)

  def fetch_and_save(self, hrefs):
    print('###########################\nStarting to fetch INFO\n###########################')
    for href in (t:=tqdm(set(hrefs))):
      t.set_description(f'fetching info on {href[19:]}')
      self.fill(href)

    print('saving data...')
    self.save()

  def save(self):
      os.makedirs('datasets', exist_ok=True)
      filname = '_'.join(self.url.split('/')[3].split('.')[0].split('-')[1:]) + '_data' + '.pickle'
      with open(f'datasets/{filname}', 'wb') as handle:
        pickle.dump(self.data, handle, protocol=pickle.HIGHEST_PROTOCOL)

      filname = '_'.join(self.url.split('/')[3].split('.')[0].split('-')[1:]) + '_reviews' + '.pickle'
      with open(f'datasets/{filname}', 'wb') as handle:
         pickle.dump(self.reviews, handle, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Scraper')
  parser.add_argument('--url', help='trip advisor url to scrape restaurant data', default='https://www.tripadvisor.com/Restaurants-g304082-Kosovo.html')

  args = parser.parse_args()
  url = args.url
  print(f"STARTING SCRAPER ON {url}")

  scraper = Scraper(url)
  hrefs = scraper.fetch_hrefs()
  scraper.fetch_and_save(hrefs)
