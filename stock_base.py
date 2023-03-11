import abc
import orjson
import re
from enum import Enum
from typing import List
from file_util import ensure_path_exists
import env
import logging
from datetime import date
import realtime_quote
import os.path

class OptionType(Enum):
    NONE = 0
    CALL = 1
    PUT = 2
    BOTH = 3

class SecurityType(Enum):
    ALL = 0
    STK = 1 # stock
    OPT = 2 # option

class StockOption:
    def __init__(self, symbol:str, id:str, type:OptionType, bid:float, ask:float, strike:float, expire_date:str) -> None:
        self.Symbol = symbol
        self.Id = id
        self.Type = type
        self.Bid = bid
        self.Ask = ask
        self.Strike = strike
        self.Expiry = expire_date

class OrderType(Enum):
    MarketOrder = 0
    LimitOrder = 1

class OrderSide(Enum):
    BUY = 0
    SELL = 1

class OrderOpenClose(Enum):
    OPEN = 0
    CLOSE = 1

class OrderTTL(Enum):
    GTC = 0
    DAY = 1

class OrderMarket(Enum):
    US = 0

class OrderStatusType(Enum):
    EXPIRED = 0
    NEW = 1
    CANCELLED = 2
    HELD = 3
    PARTIALLY_FILLED = 4
    FILLED = 5
    REJECTED = 6
    UNKNOWN = -1

class Order:
    def __init__(self, id:str,
                 symbol:str,
                 type: OrderType,
                 side:OrderSide,
                 open_close:OrderOpenClose,
                 ttl:OrderTTL,
                 market:OrderMarket,
                 price:float,
                 quantity:int,
                 sec_type:SecurityType
                 ) -> None:
        self.Id = id
        self.Symbol = symbol
        self.Type = type
        self.Side = side
        self.OpenClose = open_close
        self.TTL = ttl
        self.Market = market
        self.Price = price
        self.Quantity = quantity
        self.SecurityType = sec_type

class StockPosition:
    def __init__(self,
                 Account:str,
                 Exchange:str,
                 Symbol:str,
                 Id:str,
                 AverageCost:float,
                 Quantity:int,
                 SecurityType:SecurityType,
                 OptionType:OptionType,
                 TradingDate:str,
                 MarketValue:float,
                 MarketPrice:float,
                 Expiry:str,
                 Strike:float) -> None:
        self.Account = Account
        self.Exchange = Exchange
        self.Symbol = Symbol
        self.Id = Id
        self.AverageCost = AverageCost
        self.Quantity = Quantity
        self.SecurityType = SecurityType
        self.OptionType = OptionType
        self.TradingDate = TradingDate
        self.MarketValue = MarketValue
        self.MarketPrice = MarketPrice
        self.Expiry = Expiry
        self.Strike = Strike

class OrderOperationResult:
    def __init__(self, error_id:str, error_msg:str) -> None:
        self.ErrorId = error_id
        self.ErrorMsg = error_msg

class OrderStatus(abc.ABC):
    def __init__(self,order) -> None:
        self.brokerOrder = order

    @abc.abstractmethod
    def get_order_status(self) -> OrderStatusType:
        '''Get order status.'''

    @abc.abstractmethod
    def get_order_id(self) -> str:
        '''Get order id.'''

    @abc.abstractmethod
    def get_order_quatity(self) -> int:
        '''pass'''

    @abc.abstractmethod
    def get_order_filled(self) -> int:
        '''pass'''

    @abc.abstractmethod
    def get_order_remaining(self) -> int:
        '''pass'''

class IStockClient(abc.ABC):

    @abc.abstractmethod
    def initialize(self, prod_env:bool, account:str, symbol:str):
        '''Intialize the client.'''
    
    @abc.abstractmethod
    def get_option_chain(self, symbol:str, expire_date_str:str, type:OptionType) -> List[StockOption]:
        '''Get the symbol's option chain with expected type and expire date. Sorted by strike asc.'''

    @abc.abstractmethod
    def get_position(self, market: OrderMarket, security_type: SecurityType, symbol:str) -> List[StockPosition]:
        '''Get the positions in target market.'''

    @abc.abstractmethod
    def place_order(self, order:Order) -> OrderOperationResult:
        '''Place an self.'''

    @abc.abstractmethod
    def modify_order(self, order_id:str, new_quantity:int, new_price:float) -> OrderOperationResult:
        '''Modify an self.'''
    
    @abc.abstractmethod
    def cancel_order(self, order_id:str) -> OrderOperationResult:
        '''Modify an self.'''
    
    @abc.abstractmethod
    def query_order(self, order_id:str) -> OrderStatus:
        '''Query an self.'''

    @abc.abstractmethod
    def buy_option_to_close(self, id:str, opt_type:OptionType, quantity:int) -> OrderStatus:
        '''Query an self.'''

    @abc.abstractmethod
    def sell_put_option_to_open(self, symbol:str, strike:float, quantity:int, expired_date:date) -> OrderStatus:
        '''Query an self.'''
    
    @abc.abstractmethod
    def sell_position_to_close(self, opt_position:StockPosition) -> OrderStatus:
        '''Query an self.'''

    @abc.abstractmethod
    def sell_stock_to_close(self, symbol:str, quantity:int) -> OrderStatus:
        '''Query an self.'''

    @abc.abstractmethod
    def sell_all_stock_to_close(self, symbol:str) -> OrderStatus:
        '''Query an self.'''
    
    @abc.abstractmethod
    def get_option_position(self, market: OrderMarket, symbol:str, optionType:OptionType, expiry:date) -> List[StockPosition]:
        '''Query an self.'''
    
    @abc.abstractmethod
    def sell_option_with_protection_to_open(self, symbol:str, opt_type: OptionType,strike:float, quantity:int, expired_date:date, protect_times:float) -> OrderStatus:
        '''Query an self.'''

    @abc.abstractmethod
    def get_account_id(self) -> str:
        '''Get order id.'''
        
def get_option_type_from_str(opt_type:str) -> OptionType:
    if opt_type.casefold() == "PUT".casefold():
        return OptionType.PUT
    elif opt_type.casefold() == "CALL".casefold():
        return OptionType.CALL
    else:
        return OptionType.NONE
    

def save_positions_to_file(expired_str:str, account:str, symbol:str, positions:List[StockPosition]) -> bool:
    filename = get_positions_local_file_name(expired_str, account, symbol)
    with open(filename, 'wb') as f:
        json_str = orjson.dumps(positions,  default = lambda x: x.__dict__)
        f.write(json_str)
    return True

def load_positions_from_file(expired_str:str, account:str, symbol:str) -> List[StockPosition]:
    objs = []
    filename = get_positions_local_file_name(expired_str, account, symbol)
    if not os.path.isfile(filename):
        return objs
    
    with open(filename, 'rb') as f:
        objs = orjson.loads(f.read())
    positions = []
    for o in objs:
        positions.append(StockPosition(**o))
    
    return positions

def get_positions_local_file_name(expired_date_str:str, account:str, symbol:str) -> str:
    path = f"{env.get_data_root_path()}/position/"
    ensure_path_exists(path)
    return f"{path}/{expired_date_str}_{account}_{symbol}_opt.json"

def get_put_option_strike_price(symbol:str) -> float:
    return realtime_quote.get_realtime_quote_price(symbol) * (1 + __get_stock_miu(symbol))

def get_contract_number_of_option(symbol:str) -> int:
    return 2


def __get_stock_miu(symbol:str):
    if symbol.upper() == "SPY":
        return 0.130108/100
    elif symbol.upper() == "QQQ":
        return 0.169529/100
    elif symbol.upper() == "IWM":
        return 0.105214/100
    else:
        raise Exception("Unsupported symbol:" + symbol)