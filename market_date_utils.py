import config
import datetime
import pandas as pd


def is_date_week_end(date_str: str) -> bool:
    '''
    This function judge if a date is week end.
    '''
    date = pd.Timestamp(date_str)

    # If the date is not Thursday or Friday, it should not be the week end.
    if(date.dayofweek != 3 and date.dayofweek != 4):
        return False
    
    # If it is special date, judge by the table.
    if date_str in config.SPECIAL_WEEK_END_DATE:
        return config.SPECIAL_WEEK_END_DATE[date_str][1]
    else:
    # Else, only Friday is the week end. 
        return date.day_of_week == 4

def get_market_close_time(date_str: str) -> datetime.datetime:
    '''Get the market close time, if the market is not openning, 16:00:00 returns'''
    date = pd.Timestamp(date_str)
    market_close_date = datetime.date.fromisoformat(date_str)
    # If it is special close date, get it.
    if date_str in config.SPECIAL_WEEK_END_DATE.keys():
        return datetime.datetime.combine(market_close_date, datetime.datetime.time(hour = config.SPECIAL_WEEK_END_DATE[date_str][0]))
    else:
        #other are all 16:00:00
        return datetime.datetime.combine(market_close_date, datetime.time(hour = 16))
    
def datetime_str(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")