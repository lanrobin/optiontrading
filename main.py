import pandas as pd
import logging_util
import market_date_utils
import logging
import datetime
import time
import env

def switch_position() -> bool:
    print("Begin switch position")
    env.send_email("期权交易开始", "成功了:" + market_date_utils.datetime_str(datetime.datetime.now()))
    return True

def main():
    logging_util.setup_logging("option_traiding")
    
    date = pd.Timestamp.now()
    date_str = date.strftime("%Y-%m-%d")
    logging.info("Switch process begin.")

    if market_date_utils.is_date_week_end(date_str):
        # if today is the end of this week.
        market_close_time = market_date_utils.get_market_close_time(date_str)
        retried_time = 0
        while(retried_time < 10):
            current = datetime.datetime.now()
            delta = market_close_time - current
            if delta < datetime.timedelta():
                logging.error("Too late to switch: " + market_date_utils.datetime_str(current))
                return
            elif(delta < datetime.timedelta(minutes=5)):
                succeeded = switch_position()
                if(succeeded):
                    logging.info("switch result:" + str(succeeded) +", job done.")
                    return
                else:
                    retried_time += 1
                    logging.info("switch result:" + str(succeeded) +", retry " + market_date_utils.datetime_str(retried_time) + " times")
            elif delta > datetime.timedelta(minutes=10):
                logging.error("To early " + str(delta) +" to switch, exit.")
                env.send_email("期权交易异常", "开始太早了，现在才：" + market_date_utils.datetime_str(current))
                return
            
            logging.info("To early " + str(delta) +" to switch, sleep and try again.")
            time.sleep(10) # sleep if it is not the last 5 minutes.

    else:
        logging.info(date_str + " is not week end date, skip.")


if __name__ == '__main__':
    main()