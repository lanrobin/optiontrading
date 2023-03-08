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
SANDBOX = True

def get_stock_client(brokerName:str):
    if brokerName.casefold() == "TIGER".casefold():
        return TigerStockClient()
    else:
        raise Exception("Unknown broker:" + brokerName)

def close_position_if_executed(client: stock_base.IStockClient, symbol:str) -> bool:

    this_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0)
    expiried_opt_str_this_friday = this_friday.strftime("%Y-%m-%d")

    #positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
    positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
    if len(positions) < 1:
        # if there is no option expired this friday. We will try to open it.
        succeeded = client.sell_stock_to_close(symbol)
        logging.info("There must be some stocks, sell them to close, result:" + str(succeeded))
        order_status = client.sell_put_option_to_open(symbol, stock_base.get_put_option_strike_price(symbol), stock_base.get_contract_number_of_option(symbol), this_friday)
        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
        stock_base.save_positions_to_file(expiried_opt_str_this_friday, positions)
        logging.warning("There is no options expired this friday. We need to open it.")
        return True

    loaded_positions = stock_base.load_positions_from_file(expiried_opt_str_this_friday)

    if len(loaded_positions) < 1:
        logging.info("There is no options expired this friday locally, save the position from broker.")
        stock_base.save_positions_to_file(expiried_opt_str_this_friday, positions)
        return True

    logging.info(f"There are{len(positions)} options in the position and {len(loaded_positions)} options in the local disk.")

    # compare two position, if there is difference, that means some option got executed. we need to close the stock position.
    diff = set([ f"{p.Id}-{p.Quantity}".upper() for p in loaded_positions]) - set([ f"{p.Id}-{p.Quantity}".upper() for p in positions])
    if len(diff) > 0:
        logging.error(f"Following options differs:{diff}")
        # if there are some option gone, there must be some stock here, sell it.
        succeeded = client.sell_stock_to_close(symbol)
        logging.info("There must be some stocks, sell them to close, result:" + str(succeeded))
        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
        env.send_email("期权仓位变化了，需要主关注。", "已经把股票卖掉了。")



def switch_position(client: stock_base.IStockClient, symbol:str) -> bool:
    logging.debug("Begin switch position.")
    # env.send_email("开始调仓了", "成功了:" + market_date_utils.datetime_str(datetime.datetime.now()))
    this_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0)

    ### STEP 1: Get the current options position expired this friday.
    positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)

    ### STEP 2: If there is open options, sell them.
    logging.info(f"There are {len(positions)} contracts positions.")
    if len(positions) > 0:
       status = client.sell_position_to_close(positions)
       logging.info(f"Sold {len(positions)} contracts positions returns:{str(status)}")
    
    ### STEP 3: Sell options that expire in next Friday
    #stock_price = realtime_quote.get_realtime_quote_price(symbol)
    #logging.info(f"Get the {symbol} at price:{stock_price}")
    next_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 1)
    strike = stock_base.get_put_option_strike_price(symbol)
    contracts = stock_base.get_contract_number_of_option(symbol)
    status = client.sell_put_option_to_open(symbol, strike, contracts, next_friday)
    logging.info(f"Sold {len(positions)} contracts positions returns:{str(status)}")

    positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
    # options = client.get_option_chain(symbol, expiried_opt_str_this_friday, stock_base.OptionType.PUT)
    expiried_opt_str_next_friday = next_friday.strftime("%Y-%m-%d")
    stock_base.save_positions_to_file(expiried_opt_str_next_friday, positions)
    #loaded_positions = stock_base.load_positions_from_file(expiried_opt_str_this_friday)
    logging.info("Switch position finished.")
    return True

def main():
    logging_util.setup_logging("option_traiding")
    
    date = pd.Timestamp.now()
    date_str = date.strftime("%Y-%m-%d")
    logging.info("Program launching.")
    stockClient = get_stock_client("TIGER")


    stockClient.initialize(sandbox=SANDBOX)
    if not SANDBOX:
        raise Exception ("It is prod Now.")

    close_position_if_executed(stockClient, SYMBOL)
    switch_position(stockClient, SYMBOL)

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
        delta_to_open = market_open_time - current
        delta_to_close = market_close_time - current
        if delta_to_open > datetime.timedelta(minutes=1):
            logging.warning("Too early now, let's sleep for a while:" + str(delta_to_open))
            time.sleep(delta_to_open.total_seconds() - 1)
        elif current > market_open_time:
            if not start_email_sent:
                env.send_email("期权交易开始了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))
                start_email_sent = True

            if market_date_utils.is_date_week_end(date_str) and delta_to_close < datetime.timedelta(minutes = 5):
                logging.info("It is end of week today. We need switch the position.")
                succeeded = switch_position(stockClient, SYMBOL)
                logging.info("switch result:" + str(succeeded) +", job done.")
                break
            else:
                logging.info("Market is open, we need to monitor the position.")
                succeeded = close_position_if_executed(stockClient, SYMBOL)
                logging.info("Monitor result:" + str(succeeded) +", waiting for next round.")

        time.sleep(60) # sleep for 60 seconds and 
        current = datetime.datetime.now()

    logging.info("Market closed.")
    env.send_email("期权交易结束了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))

if __name__ == '__main__':
    main()