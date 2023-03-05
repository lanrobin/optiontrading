import _thread
import datetime
from zinvest_trade_api.stream import Stream
from zinvest_trade_api.common import URL
from concurrent.futures import ThreadPoolExecutor
import utils
import zvsts_utils
import logging

class ZVSTSRespBase:
    def __init__(self, t:str) -> None:
        ZVSTSRespBase.T = t

class ZVSTSRespMsg(ZVSTSRespBase):
    def __init__(self, t: str, msg:str) -> None:
        super().__init__(t)
        ZVSTSRespMsg.Msg = msg



class ZVSTSStockMarketWatcher(metaclass=utils.Singleton):
    def __init__(self) -> None:
        ZVSTSStockMarketWatcher.Initialized = False
        ZVSTSStockMarketWatcher.Stream = Stream(zvsts_utils.ZVSTS_SETTING.Id, zvsts_utils.ZVSTS_SETTING.Key)
        ZVSTSStockMarketWatcher.LastPrice = {}

    def start_subscribe(self):
        if not self.Initialized:
            logging.info("quotes thread starting.")
            self.Initialized = True
            self._thread = _thread.start_new_thread(self.__thread_proc, self)
        else:
            logging.info("quotes thread already started.")

    def stop_subscribe(self):
        logging.info("quotes thread stopping.")
        self.Stream.stop_ws()
        logging.info("quotes thread stopped.")

    def get_current_price(self, symbol:str):
        if not self.Initialized or symbol not in self.LastPrice.keys():
            return (False, datetime.datetime.min, 0)
        else:
            return (True, self.LastPrice[symbol][0], self.LastPrice[symbol][1])


    async def __quote_update(self, q):
        print('quote', q)

    def __thread_proc(self):
        logging.info("__thread_proc starting.")
        self.Stream.subscribe_quotes(self.__quote_update, zvsts_utils.ZVSTS_SETTING.SubscribeSymobl)
        self.Stream.run()
        logging.info("__thread_proc finished.")