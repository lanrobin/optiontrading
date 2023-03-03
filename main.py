import pandas as pd
import logging_util
import market_date_utils
import logging
import datetime
import time

def switch_position() -> bool:
    print("Begin switch position")
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
                logging.error("Too late to switch.")
                break
            elif(delta < datetime.timedelta(minutes=5)):
                succeeded = switch_position()
                if(succeeded):
                    logging.info("switch result:" + str(succeeded) +", job done.")
                    break
                else:
                    retried_time += 1
                    logging.info("switch result:" + str(succeeded) +", retry " + str(retried_time) + " times")
            time.sleep(10) # sleep if it is not the last 5 minutes.

    else:
        logging.info(date_str + " is not week end date, skip.")


if __name__ == '__main__':
    main()