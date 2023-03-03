
#Special weekly end date. If the Friday is holiday, the Thursday is the week end date.
# And usually, Thursday market close a bit earlier.
# Get from https://www.nyse.com/markets/hours-calendars
# key=Date, value= ('MarketCloseTime', IsWeekEnd, IsMarketOpenToday, EarlyMarketCloseToday)
SPECIAL_WEEK_END_DATE = {
    # Good Friday
    "2023-04-06": ('16:00:00', True, True, False), # Thursday.
    "2023-04-07": ('16:00:00', True, False, False), # Friday
    "2024-03-28": ('16:00:00', True, True, False), # Thursday.
    "2024-03-29": ('16:00:00', True, False, False), # Friday
    "2025-04-17": ('16:00:00', True, True, False), # Thursday.
    "2025-04-18": ('16:00:00', True, False, False), # Friday
    # End Good Friday

    # Juneteenth National Independence Day
    "2025-06-19": ('16:00:00', False, False, False), # Thursday
    # End Juneteenth National Independence Day

    # Independence Day
    "2024-07-04": ('13:00:00', False, False, False), # Thursday
    "2025-07-03": ('13:00:00', True, True, True), # Thursday
    "2025-07-04": ('16:00:00', True, False, False), # Friday
    # End Independence Day

    # Thanksgiving Day
    "2023-11-23": ('16:00:00', False, False, False), # Thursday
    "2023-11-24": ('13:00:00', True, True, True), # Friday
    "2024-11-28": ('16:00:00', False, False, False), # Thursday
    "2024-11-29": ('13:00:00', True, True, True), # Friday
    "2025-11-27": ('16:00:00', False, False, False), # Thursday
    "2025-11-28": ('13:00:00', True, True, True), # Friday
    # End Thanksgiving Day

    # Christmas Day
    "2025-12-24": ('16:00:00', False, False, False), # Thursday
    # End Christmas Day
}