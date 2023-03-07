import yfinance as yf
import time


if __name__ == "__main__":
    qqq = yf.Ticker("QQQ")
    while True:
        info = qqq.fast_info
        print("price:" + str(info.last_price))
        time.sleep(15)