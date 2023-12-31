
#Special weekly end date. If the Friday is holiday, the Thursday is the week end date.
# And usually, Thursday market close a bit earlier.
# Get from https://www.nyse.com/markets/hours-calendars
# key=Date, value= (MarketCloseHour, IsWeekEnd, IsMarketOpenToday, EarlyMarketCloseToday)
SPECIAL_WEEK_END_DATE = {
    # Good Friday
    "2023-04-06": (16, True, True, False), # Thursday.
    "2023-04-07": (16, True, False, False), # Friday
    "2024-03-28": (16, True, True, False), # Thursday.
    "2024-03-29": (16, True, False, False), # Friday
    "2025-04-17": (16, True, True, False), # Thursday.
    "2025-04-18": (16, True, False, False), # Friday
    "2026-04-03": (16, True, False, False), # Friday
    # End Good Friday

    # Juneteenth National Independence Day
    "2025-06-19": (16, False, False, False), # Thursday
    "2026-06-19": (16, False, False, False), # Thursday
    # End Juneteenth National Independence Day

    # Independence Day
    "2023-07-03": (13, False, True, True), # Thursday
    "2023-07-04": (13, False, False, False), # Thursday
    "2024-07-03": (13, False, True, True), # Thursday
    "2024-07-04": (13, False, False, False), # Thursday
    "2025-07-03": (13, True, True, True), # Thursday
    "2025-07-04": (16, True, False, False), # Friday
    "2026-07-02": (16, True, False, False), # Friday
    "2026-07-03": (16, True, False, False), # Friday
    # End Independence Day

    # Thanksgiving Day
    "2023-11-23": (16, False, False, False), # Thursday
    "2023-11-24": (13, True, True, True), # Friday
    "2024-11-28": (16, False, False, False), # Thursday
    "2024-11-29": (13, True, True, True), # Friday
    "2025-11-27": (16, False, False, False), # Thursday
    "2025-11-28": (13, True, True, True), # Friday
    "2026-11-26": (16, False, False, False), # Thursday
    "2026-11-27": (13, True, True, True), # Friday
    # End Thanksgiving Day

    # Christmas Day
    "2024-12-24": (13, False, True, True), # Tuesday
    "2025-12-24": (13, False, True, True), # WednesDay
    "2026-12-24": (13, False, True, True), # Thursday
    # End Christmas Day
}


# from here https://www.standard.com/individual/retirement/stock-market-and-bank-holidays
# https://www.nyse.com/markets/hours-calendars
MARKET_CLOSE_DATES = {
    "2022-11-24",
    "2022-12-26",
    "2023-01-02",
    "2023-01-16",
    "2023-02-20",
    "2023-04-07",
    "2023-05-29",
    "2023-06-19",
    "2023-07-04",
    "2023-09-04",
    "2023-11-23",
    "2023-12-25",
    "2024-03-01",
    "2024-01-15",
    "2024-02-19",
    "2024-03-29",
    "2024-05-27",
    "2024-06-19",
    "2024-07-04",
    "2024-09-02",
    "2024-11-28",
    "2024-12-25",
    "2025-01-01",
    "2025-01-20",
    "2025-02-17",
    "2025-04-18",
    "2025-05-26",
    "2025-06-19",
    "2025-07-04",
    "2025-09-01",
    "2025-11-27",
    "2025-12-25",
    "2026-01-01",
    "2026-01-19",
    "2026-02-16",
    "2026-04-03",
    "2026-05-25",
    "2026-06-19",
    "2026-07-03",
    "2026-09-07",
    "2026-11-26",
    "2026-12-25"
}