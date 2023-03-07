import yfinance as yf
import time

'''print_header = False
while True:

    data = yf.download(tickers='0700.HK', period='1d', interval='1m')
    if not print_header:
        print(data.columns)
        print_header = True
    print(data.values[-1])
    time.sleep(20)
    '''
from bs4 import BeautifulSoup
import requests

url = 'https://xueqiu.com/S/00700'
while True:
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'lxml')
    price = soup.find('div', class_ = 'stock-current')
    print(price)
    time.sleep(10)