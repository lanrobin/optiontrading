'''from bs4 import BeautifulSoup
import requests

def get_realtime_quote_price(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}?p={symbol}&.tsrc=fin-srch"

    h = {
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }

    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    price = soup.find('fin-streamer', attrs={"data-symbol":f"{symbol}", "data-field":"regularMarketPrice"})
    return price.text if price is not None else ""
'''
import yfinance as yf
def get_realtime_quote_price(symbol):
    data = yf.download(tickers='QQQ', period='1d', interval='1m')
    return data.values[-1][0]