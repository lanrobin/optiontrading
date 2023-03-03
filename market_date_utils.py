import config
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
