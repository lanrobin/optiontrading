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
from stock_base import OptionType

def get_realtime_quote_price(symbol):
    data = yf.download(tickers='QQQ', period='1d', interval='1m')
    return data.values[-1][0]

def get_option_chain(symbol:str, expired_date_str:str, option_type:OptionType):
    if option_type == OptionType.BOTH:
        raise Exception("Invalid option type:" + str(option_type))
    ticker = yf.Ticker(symbol)
    options = ticker.option_chain(expired_date_str)
    return options.calls if option_type == OptionType.CALL else options.puts