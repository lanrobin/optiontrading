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
PROD_ENV = False
DEBUG = False

__maintain_positoin_error_count = 0
__switch_position_error_count = 0

__EMAIL_MAX_COUNT = 5

def get_stock_client(brokerName:str):
    if brokerName.casefold() == "TIGER".casefold():
        return TigerStockClient()
    else:
        raise Exception("Unknown broker:" + brokerName)

def maintain_position(client: stock_base.IStockClient, symbol:str) -> bool:

    try:
        logging.debug("Begin maintain position.")
        this_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0)
        expiried_opt_str_this_friday = this_friday.strftime("%Y-%m-%d")
        expected_option_contract = stock_base.get_contract_number_of_option(symbol)

        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)

        current_option_contract = len(positions)
        logging.info(f"Expect {expected_option_contract} and current {current_option_contract}")

        if len(positions) < expected_option_contract:
            sell_option_contract = expected_option_contract - current_option_contract
            logging.info(f"We need to sell {sell_option_contract} options to fill up the position.")

            # sell all the stock for this symbol first.
            status = client.sell_all_stock_to_close(symbol=symbol)

            logging.warning(f"Sold stocks for {symbol} returns {status}")

            strike_price = stock_base.get_put_option_strike_price(symbol)

            ########----------------------------------------
            ## If today is the end of week, we don't sell option today. NO, if you don't sell it, margin will limit you from sell option for the next week.
            today = pd.Timestamp.now()
            today_str = today.strftime("%Y-%m-%d")
            ########----------------------------------------
            if not market_date_utils.is_date_week_end(date_str=today_str):
                logging.info(f"Will sell {sell_option_contract} options on {symbol} that expire at {expiried_opt_str_this_friday} on strike:{strike_price}")
                order_status = client.sell_put_option_to_open(symbol, strike_price, sell_option_contract, this_friday)
                logging.info(f"Option sold return:{order_status}")
                env.send_email("期权仓位变化了，需要主关注。", f"因为有些期权被行权了，所以新卖了{sell_option_contract}手，返回结果:{order_status}")
            else:
                logging.warn(f"Today {today_str} is end of week, we skip sell {sell_option_contract} option and wait for switch.")
            
            positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
            stock_base.save_positions_to_file(expiried_opt_str_this_friday, positions)
            logging.warning(f"Sold {sell_option_contract} options expired this friday and now total:{len(positions)}.")
            return True

        loaded_positions = stock_base.load_positions_from_file(expiried_opt_str_this_friday)

        if len(loaded_positions) < 1:
            logging.info("There is no options expired this Friday locally, save the position from broker.")
            stock_base.save_positions_to_file(expiried_opt_str_this_friday, positions)
            return True

        logging.info(f"There are {len(positions)} options in the position and {len(loaded_positions)} options in the local disk.")

        # compare two position, if there is difference, that means some option got executed. we need to close the stock position.
        diff = set([ f"{p.Id}-{p.Quantity}".upper() for p in loaded_positions]) - set([ f"{p.Id}-{p.Quantity}".upper() for p in positions])
        if len(diff) > 0:
            logging.error(f"Following options differs:{diff}")
            # if there are some option gone, there must be some stock here, sell it.
            # sell all the stock first.
            succeeded = client.sell_all_stock_to_close(symbol=symbol)
            logging.info("There must be some stocks, sell them to close, result:" + str(succeeded))
            positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
            stock_base.save_positions_to_file(expiried_opt_str_this_friday, positions)
            env.send_email("期权仓位变化了，需要主关注。", "已经把股票卖掉了。")

        __maintain_positoin_error_count = 0
    except Exception as e:
        __maintain_positoin_error_count += 1
        err_msg = f"maintain_position {__maintain_positoin_error_count}th error:{type(e)}:{e}"
        logging.error(err_msg)
        if __maintain_positoin_error_count < __EMAIL_MAX_COUNT or __maintain_positoin_error_count % 30 == 0:
            env.send_email("期权交易出错了", f"错误是:{err_msg}, 时间：{market_date_utils.datetime_str(datetime.datetime.now())}")



def switch_position(client: stock_base.IStockClient, symbol:str) -> bool:
    try:
        logging.debug("Begin switch position.")
        # env.send_email("开始调仓了", "成功了:" + market_date_utils.datetime_str(datetime.datetime.now()))
        this_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0)

        ### STEP 1: Get the current options position expired this friday.
        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)

        ### STEP 2: If there is open options, sell them.

        ################======================================
        # If the sold option is deep OOM option, we don't need to buy it back to save transcation fee.
        ################======================================
        logging.info(f"There are {len(positions)} contracts positions.")
        total_bought_options = 0
        for p in positions:
            status = client.buy_option_to_close(p.Id, p.OptionType, -p.Quantity)
            total_bought_options += -p.Quantity
            logging.info(f"Buy {p.Id} with {p.Quantity} contracts returns {status}")
        
        ### STEP 3: Sell options that expire in next Friday
        next_friday = market_date_utils.get_next_nth_friday(datetime.datetime.now(), 1)
        expiried_opt_str_next_friday = next_friday.strftime("%Y-%m-%d")

        strike = stock_base.get_put_option_strike_price(symbol)
        contracts = stock_base.get_contract_number_of_option(symbol)

        status = client.sell_put_option_to_open(symbol, strike, contracts, next_friday)
        logging.info(f"Sold {len(positions)} contracts that expire at {next_friday} positions returns:{str(status)}")

        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
        stock_base.save_positions_to_file(expiried_opt_str_next_friday, positions)

        env.send_email("调仓完成", f"买回了{total_bought_options}手{this_friday}到期的期权，再卖出了{contracts}手{expiried_opt_str_next_friday}到期的期权。时间：" + market_date_utils.datetime_str(datetime.datetime.now()))

        logging.info("Switch position finished.")

        # recovered.
        __switch_position_error_count = 0
        return True
    except Exception as e:
        __switch_position_error_count += 1
        err_msg = f"switch_position {__switch_position_error_count}th error:{type(e)}:{e}"
        logging.error(err_msg)
        if __switch_position_error_count < __EMAIL_MAX_COUNT or __switch_position_error_count % 30 == 0:
            env.send_email("期权交易出错了", f"错误是:{err_msg}, 时间：{market_date_utils.datetime_str(datetime.datetime.now())}")

def main():
    logging_util.setup_logging("option_traiding")
    
    date = pd.Timestamp.now()
    date_str = date.strftime("%Y-%m-%d")
    logging.info("Program launching.")
    stockClient = get_stock_client("TIGER")


    stockClient.initialize(prod_env=PROD_ENV)
    if PROD_ENV:
        raise Exception ("It is prod Now.")

    if DEBUG:
        maintain_position(stockClient, SYMBOL)
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
                succeeded = maintain_position(stockClient, SYMBOL)
                logging.info("Monitor result:" + str(succeeded) +", waiting for next round.")

        time.sleep(60) # sleep for 60 seconds and 
        current = datetime.datetime.now()

    logging.info("Market closed.")
    env.send_email("期权交易结束了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))

if __name__ == '__main__':
    main()