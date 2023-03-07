import yfinance as yf
import time


if __name__ == "__main__":

    print_header = False
    while True:
        data = yf.download(tickers='QQQ', period='1d', interval='1m')
        if not print_header:
            print(data.columns)
            print_header = True

        print(data.values[-1])
        time.sleep(10)