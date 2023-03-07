import pandas as pd
import logging_util
import market_date_utils
import logging
import datetime
import time
import env
import realtime_quote
import stock_base
from stock_tiger import TigerStockClient

SYMBOL = "QQQ"

def close_position_if_executed(client: stock_base.IStockClient) -> bool:
    pass

def switch_position(client: stock_base.IStockClient, symbol:str) -> bool:
    logging.debug("Begin switch position.")
    stock_price = realtime_quote.get_realtime_quote_price(symbol)
    logging.info(f"Get the {symbol} at price:{stock_price}")
    #env.send_email("期权交易开始", "成功了:" + market_date_utils.datetime_str(datetime.datetime.now()))
    next_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 1)
    options = client.get_option_chain(symbol, next_friday.strftime("%Y-%m-%d"), stock_base.OptionType.PUT)
    return True

def main():
    logging_util.setup_logging("option_traiding")
    
    date = pd.Timestamp.now()
    date_str = date.strftime("%Y-%m-%d")
    logging.info("Program launching.")
    stockClient = TigerStockClient()
    succeeded = switch_position(client = stockClient, symbol = SYMBOL)

    start_email_sent = False
    # it will begin 5 minutes before market open and 5 minutes after the market close.
    current = datetime.datetime.now()
    market_open_time = datetime.datetime.combine(current.date(), datetime.time(hour=9, minute=30))
    market_close_time = market_date_utils.get_market_close_time(date_str)

    if not market_date_utils.is_market_open(date_str):
        logging.warning("Market is not open today:" + date_str)
        return
    if current > market_close_time:
        logging.warning("Market is closed today at :" + market_date_utils.datetime_str(market_close_time))
        return
    while current < market_close_time:
        delta = market_open_time - current
        if delta > datetime.timedelta(minutes=1):
            logging.warning("Too early now, let's sleep for a while:" + str(delta))
            time.sleep(delta.total_seconds() - 1)
        elif current > market_open_time:
            if not start_email_sent:
                env.send_email("期权交易开始了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))
                start_email_sent = True
            # market is open now.
            succeeded = switch_position()
            logging.info("switch result:" + str(succeeded) +", job done.")

        time.sleep(60) # sleep for 60 seconds and 
        current = datetime.datetime.now()

    logging.info("Market closed.")
    env.send_email("期权交易结束了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))

if __name__ == '__main__':
    main()