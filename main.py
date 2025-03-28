import pandas as pd
import logging_util
import market_date_utils
import logging
import datetime
import time
import env
import stock_base
from stock_tiger import TigerStockClient
from stock_snowball import SnowballStockClient
import sys, getopt

SWITCH_SECONDS_BEFORE_MARKET_CLOSE = 20
SHORT_SLEEP_SECONDS_BEFORE_MARKET_CLOSE = 65
__EMAIL_MAX_COUNT = 5
PROTECT_TIMES = 4

G_maintain_position_error_count = 0
G_switch_position_error_count = 0
G_target_symbol = None
G_broker_name = "TIGER"
G_debug_main_method = True
G_prod_env = False
G_account = None
G_expected_option_contract_number = 0
G_position_incorrect_email_sent = False


def get_stock_client(brokerName:str):
    if brokerName.casefold() == "TIGER".casefold():
        return TigerStockClient()
    elif brokerName.casefold() == "SNOWBALL".casefold():
        return SnowballStockClient()
    else:
        raise Exception("Unknown broker:" + brokerName)
    
def get_position_summary(client: stock_base.IStockClient, symbol:str) -> list:
     # After market close, we need to send the summary.
    stk_positions = client.get_position(stock_base.OrderMarket.US, stock_base.SecurityType.STK, G_target_symbol)
    position_strs = []
    for sp in stk_positions:
        position_strs.append(sp.to_summary_str())

    opt_positions = client.get_position(stock_base.OrderMarket.US, stock_base.SecurityType.OPT, G_target_symbol)
    for op in opt_positions:
        position_strs.append(op.to_summary_str())

    return position_strs

def maintain_position(client: stock_base.IStockClient, symbol:str, market_close:datetime) -> bool:

    global G_maintain_position_error_count
    global G_expected_option_contract_number
    global G_position_incorrect_email_sent

    try:
        logging.debug("Begin maintain position.")
        this_friday = market_date_utils.get_option_expiry_this_week(market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0))
        expiried_opt_str_this_friday = this_friday.strftime("%Y-%m-%d")
        expected_option_contract = G_expected_option_contract_number #stock_base.get_contract_number_of_option(symbol)

        # check if there are open orders.
        open_orders_quantity = 0
        open_orders = client.get_open_option_orders(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
        for o in open_orders:
            logging.info(f"Open order:{o}")
            open_orders_quantity += abs(o.Quantity)

        if open_orders_quantity > 0:
            logging.warn(f"There are {open_orders_quantity} open orders for symbol:{symbol}  expires at {expiried_opt_str_this_friday}")

        # check the current position.
        existing_contract_number = 0
        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
        if len(positions) > 0:
            for p in positions:
                existing_contract_number += abs(p.Quantity)
                logging.info(f"Existing position: {p}")
        logging.info(f"Expect {expected_option_contract} and current {existing_contract_number}")


        if existing_contract_number + open_orders_quantity< expected_option_contract:
            sell_option_contract = expected_option_contract - existing_contract_number - open_orders_quantity
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
            
            # we will refill the position if there are more than 4 hours to market close time.
            refill_position = True if market_close - datetime.datetime.now() > datetime.timedelta(hours=4) else False
            logging.warning(f"We need to refill_position:{refill_position}")
            if not market_date_utils.is_date_week_end(date_str=today_str) and refill_position:
                logging.info(f"Will sell {sell_option_contract} options on {symbol} that expire at {expiried_opt_str_this_friday} on strike:{strike_price}")
                order_status = client.sell_put_option_to_open(symbol, strike_price, sell_option_contract, this_friday)
                logging.info(f"Option sold return:{order_status}")
                env.send_email(f"{client.get_client_name()}期权仓位变化了，需要主关注。", f"因为有些期权被行权了，所以新卖了{sell_option_contract}手，返回结果:{order_status}")

                # 在这里我们需要等待一定的时间来让订单被执行。我们最多等待10分钟。
                sleep_times_before_order_to_fill = 0
                start_waiting_order_to_fill_time = datetime.datetime.now()
                while datetime.datetime.now() - start_waiting_order_to_fill_time < datetime.timedelta(minutes=10):
                    
                    open_orders_quantity = 0
                    open_orders = client.get_open_option_orders(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
                    for o in open_orders:
                        logging.info(f"Open order:{o}")
                        open_orders_quantity += abs(o.Quantity)

                    existing_contract_number = 0
                    positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
                    if len(positions) > 0:
                        for p in positions:
                            existing_contract_number += abs(p.Quantity)
                            logging.info(f"Existing position: {p}")

                    logging.debug(f"There still {open_orders_quantity} open order for {symbol} expired at:{expiried_opt_str_this_friday} and the position is:{existing_contract_number}")

                    if open_orders_quantity == 0 and existing_contract_number >= expected_option_contract:
                        logging.debug(f"All order are filled. break")
                        break
                    else:
                        sleep_times_before_order_to_fill += 1
                        logging.debug(f"Order are not filled, sleep and retry:{sleep_times_before_order_to_fill} times")
                        time.sleep(30)

                if sleep_times_before_order_to_fill > 2:
                    email_msg_unfilled = f"一共sleep了:{sleep_times_before_order_to_fill}次了，仓位是,open_orders_quantity:{open_orders_quantity}, existing_contract_number:{existing_contract_number}"
                    logging.error(email_msg_unfilled)
                    env.send_email("卖单还没有完成了", email_msg_unfilled)
            else:
                logging.warn(f"Today {today_str} is end of week, we skip sell {sell_option_contract} option and wait for switch.")
            
            positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)
            stock_base.save_positions_to_file(expiried_opt_str_this_friday, client.get_account_id(), symbol, positions)
            logging.warning(f"Sold {sell_option_contract} options expired this friday and now total:{len(positions)}.")
            return True
        elif existing_contract_number + open_orders_quantity > expected_option_contract:
            msg = f"仓位信息不对，expected_option_contract：{expected_option_contract} < existing_contract_number:{existing_contract_number} + open_orders_quantity:{open_orders_quantity}, G_position_incorrect_email_sent:{G_position_incorrect_email_sent}"
            logging.error(msg)
            if not G_position_incorrect_email_sent:
                env.send_email("出错了!仓位信息不对!", msg)
                G_position_incorrect_email_sent = True
        
        loaded_positions = stock_base.load_positions_from_file(expiried_opt_str_this_friday, client.get_account_id(), symbol)
        if len(loaded_positions) < 1:
            logging.info("There is no options expired this Friday locally, save the position from broker.")
            stock_base.save_positions_to_file(expiried_opt_str_this_friday, client.get_account_id(), symbol, positions)
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
            stock_base.save_positions_to_file(expiried_opt_str_this_friday,  client.get_account_id(), symbol, positions)
            env.send_email(f"{client.get_client_name()}期权仓位变化了，需要主关注。", f"已经把股票卖掉了:{diff}")

        G_maintain_position_error_count = 0
        return True
    except Exception as e:
        G_maintain_position_error_count += 1
        err_msg = f"maintain_position {G_maintain_position_error_count}th error:{type(e)}:{e}"
        logging.error(err_msg)
        if G_maintain_position_error_count < __EMAIL_MAX_COUNT or G_maintain_position_error_count % 30 == 0:
            env.send_email(f"{client.get_client_name()}期权交易出错了", f"错误是:{err_msg}, 时间：{market_date_utils.datetime_str(datetime.datetime.now())}")
        return False



def switch_position(client: stock_base.IStockClient, symbol:str, market_close: datetime) -> bool:
    global G_switch_position_error_count
    global G_expected_option_contract_number
    try:
        logging.debug("Begin switch position.")
        # env.send_email("开始调仓了", "成功了:" + market_date_utils.datetime_str(datetime.datetime.now()))
        this_friday = market_date_utils.get_option_expiry_this_week(market_date_utils.get_next_nth_friday(datetime.datetime.now(), 0))

        ### STEP 1: Get the current options position expired this friday.
        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, this_friday)

        ### STEP 2: If there is open options, sell them.

        ################======================================
        # If the sold option is deep OOM option, we don't need to buy it back to save transcation fee.
        ################======================================
        logging.info(f"There are {len(positions)} contracts positions.")
        total_bought_options = 0
        for p in positions:
            logging.info(f"Closing position: {p}")
            status = client.buy_option_to_close(p.Id, p.OptionType, -p.Quantity)
            total_bought_options += abs(p.Quantity)
            logging.info(f"Buy {p.Id} with {p.Quantity} contracts returns {status}")

        ###Here we should check if the order to buy option filled. And then continue.
        
        ### STEP 3: Sell options that expire in next Friday
        next_friday = market_date_utils.get_option_expiry_this_week(market_date_utils.get_next_nth_friday(datetime.datetime.now(), 1))
        expiried_opt_str_next_friday = next_friday.strftime("%Y-%m-%d")

        strike = stock_base.get_put_option_strike_price(symbol)
        contracts = G_expected_option_contract_number #stock_base.get_contract_number_of_option(symbol)
        
        sold_contract_number = 0
        existing_contract_number = 0
        next_friday_positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
        logging.info(f"There are {len(next_friday_positions)} position for {symbol}  expires at {expiried_opt_str_next_friday}")
        if len(next_friday_positions) > 0:
            for nfp in next_friday_positions:
                existing_contract_number += abs(nfp.Quantity)

         # check if there are open orders.
        open_orders = client.get_open_option_orders(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
        open_orders_quantity = 0

        for o in open_orders:
            open_orders_quantity += abs(o.Quantity)

        if open_orders_quantity > 0:
            logging.warn(f"There are {open_orders_quantity} open orders for symbol:{symbol} expires at {expiried_opt_str_next_friday}.")

        
        if existing_contract_number + open_orders_quantity < contracts:
            sold_contract_number = contracts - existing_contract_number - open_orders_quantity
            status = client.sell_put_option_to_open(symbol, strike, sold_contract_number, next_friday)
            logging.info(f"Sold {sold_contract_number} contracts that expire at {next_friday} positions returns:{str(status)}")
        else:
            logging.warn("Already had enough position for {symbol} that expire at {next_friday}")

        while True:
            # check if there are open orders.
            open_orders = client.get_open_option_orders(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
            open_orders_quantity = 0

            for o in open_orders:
                open_orders_quantity += abs(o.Quantity)
            time.sleep(5) # wait for 5 seconds and retry.
            current = datetime.datetime.now()
            if open_orders_quantity == 0 or current >= market_close:
                break
        
        
       

        positions = client.get_option_position(stock_base.OrderMarket.US, symbol, stock_base.OptionType.PUT, next_friday)
        stock_base.save_positions_to_file(expiried_opt_str_next_friday,  client.get_account_id(), symbol, positions)
        email_msg = ""

        if open_orders_quantity == 0:
            email_msg = f"买回了{total_bought_options}手{this_friday}到期的期权，再卖出了{sold_contract_number}手{expiried_opt_str_next_friday}到期的期权。时间：" + market_date_utils.datetime_str(datetime.datetime.now())
            env.send_email(f"{client.get_client_name()}调仓完成", email_msg)
        else:
            email_msg = f"买回了{total_bought_options}手{this_friday}到期的期权，再卖出了{sold_contract_number}手{expiried_opt_str_next_friday}到期的期权,但是有{open_orders_quantity}没有成交。时间：" + market_date_utils.datetime_str(datetime.datetime.now())
            env.send_email(f"{client.get_client_name()}。注意！！调仓没有完成！", email_msg)
        
        logging.info(email_msg)
        logging.info("Switch position finished.")

        # recovered.
        G_switch_position_error_count = 0
        return True
    except Exception as e:
        G_switch_position_error_count += 1
        err_msg = f"switch_position {G_switch_position_error_count}th error:{type(e)}:{e}"
        logging.error(err_msg)
        if G_switch_position_error_count < __EMAIL_MAX_COUNT or G_switch_position_error_count % 30 == 0:
            env.send_email(f"{client.get_client_name()}期权交易出错了", f"错误是:{err_msg}, 时间：{market_date_utils.datetime_str(datetime.datetime.now())}")
        return False

def main():
    global G_target_symbol
    global G_broker_name
    global G_debug_main_method
    global G_prod_env
    global G_account
    global G_expected_option_contract_number
    opts, _ = getopt.getopt(sys.argv[1:], shortopts="s:b:d:e:a:n:", longopts=["symbol=", "broker=", "debug=", "env=", "account=", "number="])

    for opt, value in opts:
        if opt in ("-s", "--symbol"):
            G_target_symbol = value
        elif opt in ("-b", "--broker"):
            G_broker_name = value
        elif opt in ("-d", "--debug"):
            G_debug_main_method = True if "TRUE".casefold() == value.casefold() else False
        elif opt in ("-e", "--env"):
            G_prod_env = True if "PROD".casefold() == value.casefold() else False
        elif opt in ("-a", "--account"):
            G_account = value
        elif opt in ("-n", "--number"):
            try:
                G_expected_option_contract_number = int(value)
            except ValueError:
                G_expected_option_contract_number = 0

    if G_account == None:
        raise Exception("No account provide!!")
    
    if G_target_symbol == None:
        raise Exception("No symbol provide!!")
    
    if G_expected_option_contract_number < 1:
        raise Exception(f"No expected contract number provided:{G_expected_option_contract_number}")

    logging_util.setup_logging(f"{G_broker_name}_{G_account}_{G_target_symbol}_option_traiding")
    
    date = pd.Timestamp.now()
    date_str = date.strftime("%Y-%m-%d")
    logging.info(f"Program launching with G_target_symbol:{G_target_symbol}, G_broker_name:{G_broker_name}, G_debug_main_method:{G_debug_main_method}, G_prod_env:{G_prod_env}, G_expected_option_contract_number:{G_expected_option_contract_number}")
    stockClient = get_stock_client(G_broker_name)


    stockClient.initialize(prod_env=G_prod_env, account=G_account, symbol=G_target_symbol)
    if G_prod_env:
        logging.warn("It is in prod env.")
        # raise Exception ("It is prod Now.")

    start_email_sent = False
    # it will begin 5 minutes before market open and 5 minutes after the market close.
    current = datetime.datetime.now()
    market_open_time = datetime.datetime.combine(current.date(), datetime.time(hour=9, minute=30))
    market_close_time = market_date_utils.get_market_close_time(date_str)
    sleep_seconds_before_next_loop = 55
    stop_maintain_position = False

    logging.debug(f"market_open_time:{market_date_utils.datetime_str(market_open_time)}, market_close_time:{market_date_utils.datetime_str(market_close_time)}")

    if G_debug_main_method:
        maintain_position(stockClient, G_target_symbol, market_close_time)
        switch_position(stockClient, G_target_symbol, market_close_time)

    if not market_date_utils.is_market_open(date_str):
        logging.warning("Market is not open today:" + date_str)
        env.send_email(f"{stockClient.get_client_name()}今天放假！", "所以不用交易。")
        return
    if current > market_close_time:
        logging.warning("Market is closed today at :" + market_date_utils.datetime_str(market_close_time))
        return
    while current < market_close_time:
        delta_to_open = market_open_time - current
        delta_to_close = market_close_time - current
        if delta_to_open > datetime.timedelta(minutes = 1):
            logging.warning("Too early now, let's sleep for a while:" + str(delta_to_open))
            time.sleep(delta_to_open.total_seconds() - 55) # We will sleep 55 second at end of process.
        elif current > market_open_time:
            if not start_email_sent:
                env.send_email(f"{stockClient.get_client_name()}期权交易开始了。", "时间:" + market_date_utils.datetime_str(datetime.datetime.now()))
                start_email_sent = True

            is_end_of_week = market_date_utils.is_date_week_end(date_str)
            logging.debug(f"is_end_of_week:{is_end_of_week},market_close_time:{market_date_utils.datetime_str(market_close_time)},delta_to_close:{delta_to_close}")
            if is_end_of_week:
                if delta_to_close < datetime.timedelta(seconds = SWITCH_SECONDS_BEFORE_MARKET_CLOSE):
                    logging.info("It is end of week today. We need switch the position.")
                    succeeded = switch_position(stockClient, G_target_symbol, market_close_time)
                    logging.info("switch result:" + str(succeeded) +", job done.")
                    break
                elif delta_to_close < datetime.timedelta(seconds=SHORT_SLEEP_SECONDS_BEFORE_MARKET_CLOSE):
                    sleep_seconds_before_next_loop = 5
                    stop_maintain_position = True
                    logging.info(f"Step into fast sleep stage and skip maintain step. sleep interval:{sleep_seconds_before_next_loop}")
            
            logging.debug(f"sleep_seconds_before_next_loop:{sleep_seconds_before_next_loop},stop_maintain_position:{stop_maintain_position}")

            if not stop_maintain_position:
                # we will always matain the position regardless of end of the week.
                logging.info("Market is open, we need to monitor the position.")
                succeeded = maintain_position(stockClient, G_target_symbol, market_close_time)
                logging.info("Monitor result:" + str(succeeded) +", waiting for next round.")
            else:
                logging.info(f"It is now the fast transcation stage. sleep_seconds_before_next_loop:{sleep_seconds_before_next_loop}")

        time.sleep(sleep_seconds_before_next_loop) # sleep for 55 seconds and 
        current = datetime.datetime.now()

   
    position_strs = get_position_summary(stockClient, G_target_symbol)
    summary_str = "\n".join(position_strs)
    logging.info(f"Market closed. Positions:{summary_str}")
    env.send_email(f"{stockClient.get_client_name()}期权交易结束了。", f"时间:{market_date_utils.datetime_str(datetime.datetime.now())}, 仓位:{summary_str}")

if __name__ == '__main__':
    main()