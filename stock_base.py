import abc
from enum import Enum
from typing import List

class OptionType(Enum):
    PUT = 0
    CALL = 1
    BOTH = 2

class StockOption:
    def __init__(self, symbol:str, id:str, type:OptionType, bid:float, ask:float, strike:float) -> None:
        StockOption.Symbol = symbol
        StockOption.Id = id
        StockOption.Type = type
        StockOption.Bid = bid
        StockOption.Ask = ask
        StockOption.Strike = strike

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
                 quantity:int
                 ) -> None:
        Order.Id = id
        Order.Symbol = symbol
        Order.Type = type
        Order.Side = side
        Order.OpenClose = open_close
        Order.TTL = ttl
        Order.Market = market
        Order.Price = price
        Order.Quantity = quantity

class StockPosition:
    def __init__(self) -> None:
        pass

class OrderOperationResult:
    def __init__(self, error_id:str, error_msg:str) -> None:
        OrderOperationResult.ErrorId = error_id
        OrderOperationResult.ErrorMsg = error_msg

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
        OrderStatus.StatusType = status_type
        OrderStatus.FilledQuantity = filled_quantity
        OrderStatus.ErrorId = error_id
        OrderStatus.ErrorMsg = error_msg

class IStockClient(abc.ABC):

    @abc.abstractmethod
    def initialize():
        '''Intialize the client.'''
    
    @abc.abstractmethod
    def get_option_chain(self, symbol:str, expire_date_str:str, type:OptionType) -> List[StockOption]:
        '''Get the symbol's option chain with expected type and expire date.'''

    @abc.abstractmethod
    def get_position(self, market: OrderMarket) -> List[StockPosition]:
        '''Get the positions in target market.'''

    @abc.abstractmethod
    def place_order(self, order:Order) -> OrderOperationResult:
        '''Place an order.'''

    @abc.abstractmethod
    def modify_order(self, order_id:str, new_quantity:int, new_price:float) -> OrderOperationResult:
        '''Modify an order.'''
    
    @abc.abstractmethod
    def cancel_order(self, order_id:str) -> OrderOperationResult:
        '''Modify an order.'''
    
    @abc.abstractmethod
    def query_order(self, order_id:str) -> OrderStatus:
        '''Query an order.'''