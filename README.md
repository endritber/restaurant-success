# Restaurant Success Model

----

##### Model that predicts if a restaurant is likely to close within the next years

----

###### Description

The goal of this project was to build a model that can predict whether a restaurant is likely to close within the next years. This information would be useful to restaurant lenders (such as banks) and investors.

Achieving this goal was by starting to build my own relevant dataset from Kosova, Albania, Macedonia, Montenegro Restaurants using BeautifulSoup Scraper from TripAdvisor.

- To scrape the data from these countries there is a urls.txt file containing each county and a scrap bash script to run the scraper on.

One example might include

```
./scrape

### OR

./business_scraper.py --url "https://www.tripadvisor.com/Restaurants-{code}-{country-kosovo}.html"
```

A url example might be - "https://www.tripadvisor.com/Restaurants-g304082-Kosovo.html"
