from bs4 import BeautifulSoup
import requests

def get_realtime_quote_price(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}?p={symbol}&.tsrc=fin-srch"
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    price = soup.find('fin-streamer', attrs={"data-symbol":f"{symbol}", "data-field":"regularMarketPrice"})
    return price.text if price is not None else ""
