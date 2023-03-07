import abc
from enum import Enum
from typing import List

class OptionType(Enum):
    PUT = 0
    CALL = 1
    BOTH = 2

class SecurityType(Enum):
    STK = 0 # stock
    OPT = 1 # option

class StockOption:
    def __init__(self, symbol:str, id:str, type:OptionType, bid:float, ask:float, strike:float, expire_date:str) -> None:
        self.Symbol = symbol
        self.Id = id
        self.Type = type
        self.Bid = bid
        self.Ask = ask
        self.Strike = strike
        self.ExpireDate = expire_date

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
    NEW = 0
    PARTIAL_FILLED = 1
    FILLED = 2
    CANCELLED = 3
    EXPIRED = 4

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
    def __init__(self, acnt:str,
                 exchg:str,
                 sym:str,
                 average_cost:float,
                 total_qty:int,
                 sec_type:SecurityType,
                 trading_day:str) -> None:
        self.Account = acnt
        self.Exchange = exchg
        self.Symbol = sym
        self.AverageCost = average_cost
        self.Quantity = total_qty
        self.SecurityType = sec_type
        self.TradingDay = trading_day

class OrderOperationResult:
    def __init__(self, error_id:str, error_msg:str) -> None:
        self.ErrorId = error_id
        self.ErrorMsg = error_msg

class OrderStatus(Order):
    def __init__(self, id:str,
                 symbol:str,
                 type: OrderType,
                 side:OrderSide,
                 open_close:OrderOpenClose,
                 ttl:OrderTTL,
                 market:OrderMarket,
                 price:float,
                 quantity:int,
                 status_type: OrderStatusType,
                 filled_quantity:int,
                 error_id:str,
                 error_msg:str
                 ) -> None:
        super().__init__(id, symbol, type, side, open_close, ttl, market, price, quantity)
        self.StatusType = status_type
        self.FilledQuantity = filled_quantity
        self.ErrorId = error_id
        self.ErrorMsg = error_msg

class IStockClient(abc.ABC):

    @abc.abstractmethod
    def initialize(self, sandbox:bool):
        '''Intialize the client.'''
    
    @abc.abstractmethod
    def get_option_chain(self, symbol:str, expire_date_str:str, type:OptionType) -> List[StockOption]:
        '''Get the symbol's option chain with expected type and expire date.'''

    @abc.abstractmethod
    def get_position(self, market: OrderMarket, security_type: SecurityType) -> List[StockPosition]:
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