import _thread
import datetime
from zinvest_trade_api.stream import Stream
from zinvest_trade_api.common import URL
from concurrent.futures import ThreadPoolExecutor
import utils
import zvsts_utils
import logging
import json

'''
Msg format check here: https://www.zvsts.com/api/#section/API/%E6%9C%80%E6%96%B0%E4%BB%B7%E6%8A%A5%E6%96%87
'''

class ZVSTSRespBase:
    def __init__(self, t:str) -> None:
        self.T = t

class ZVSTSRespMsg(ZVSTSRespBase):
    def __init__(self, t: str, msg:str) -> None:
        super().__init__(t)
        self.Msg = msg

class ZVSTSRespSub(ZVSTSRespBase):
    def __init__(self, t: str, snapshots:list, quotes:list) -> None:
        super().__init__(t)
        self.SnapShots = snapshots
        self.Quotes = quotes

class QuoteItem:
    def __init__(self, p:float, s:int) -> None:
        self.p = p
        self.s = s

class ZVSTSRespSnapShot(ZVSTSRespBase):
    def __init__(self, T: str, S:str, c:float, h:float, o:float, l:float, v:float, t:int) -> None:
        super().__init__(T)
        self.S = S
        self.c = c
        self.h = h
        self.o = o
        self.l = l
        self.v = v
        self.t = t

class ZVSTSRespQuote(ZVSTSRespBase):
    def __init__(self, T: str, S:str, t:int, a:list, b:list) -> None:
        super().__init__(T)
        self.S = S
        self.t = t
        self.a = a
        self.b = b
        

class ZVSTSStockMarketWatcher(metaclass=utils.Singleton):
    def __init__(self) -> None:
        self.Initialized = False
        self.Stream = Stream(zvsts_utils.ZVSTS_SETTING.Id, zvsts_utils.ZVSTS_SETTING.Key)
        self.LastPrice = {}

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


if __name__ == "__main__":
    jsonStr = '''{
      "T": "s",
      "S": "US_AAPL",
      "t": 142021,
      "a": [{
        "p": 485.20,
        "s": 8700
      }],
      "b": [{
        "p": 488.20,
        "s": 8600
      }]
    }'''

    j = json.loads(jsonStr)
    s = ZVSTSRespQuote(**j)
    print(s)