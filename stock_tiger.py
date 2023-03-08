from stock_base import *

from tigeropen.common.consts import (Language,        # 语言
                                Market,           # 市场
                                BarPeriod,        # k线周期
                                QuoteRight)       # 复权类型
from tigeropen.tiger_open_config import TigerOpenClientConfig
#from tigeropen.common.util.signature_utils import read_private_key
#from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.common.consts import SecurityType as tst

import env
import logging
import realtime_quote

class TigerStockClient(IStockClient):

    def __init__(self) -> None:
        super().__init__()
        self.TradeClient = None
        self.QuoteClient = None


    def initialize(self, sandbox:bool):
        config_path = ""
        if sandbox:
            config_path = f"{env.get_data_root_path()}/tigersandbox"
        else:
            config_path = f"{env.get_data_root_path()}/tigerprod"
        
        client_config = TigerOpenClientConfig(sandbox_debug=sandbox, props_path=config_path)
        client_config.log_level = logging.DEBUG
        client_config.log_path = env.get_data_root_path() + "/log/tigerapi.log"
        client_config.timezone = "America/New_York"
        # 接口超时时间
        client_config.timeout = 15
        # 超时重试设置
        # 最长重试时间，单位秒
        client_config.retry_max_time = 60
        # 最多重试次数
        client_config.retry_max_tries = 5
        self.TradeClient = TradeClient(client_config)
    

    def get_option_chain(self, symbol:str, expire_date_str:str, type:OptionType) -> List[StockOption]:
        opt_data = realtime_quote.get_option_chain(symbol=symbol, expired_date_str=expire_date_str, option_type=type)
        options = []
        if opt_data is not None:
            for od in opt_data.values:
                options.append(StockOption(symbol = symbol,
                                        id = od[0],
                                        type = type,
                                        bid = od[4],
                                        ask = od[5],
                                        strike=od[2],
                                        expire_date = expire_date_str))
        
        # sorted.
        options.sort(key = lambda v: v.Strike)
        return options


    def get_position(self, market: OrderMarket, security_type: SecurityType, symbol:str) -> List[StockPosition]:
        tigerSecurityType = tst.ALL
        if security_type == SecurityType.OPT:
            tigerSecurityType = tst.OPT
        elif security_type == SecurityType.STK:
            tigerSecurityType = tst.STK
        elif security_type == SecurityType.ALL:
            tigerSecurityType = tst.ALL
        else:
            raise Exception("Unsupported security type:" + str(security_type))
        
        tigerMarketType = Market.US
        if market == OrderMarket.US:
            tigerMarketType = Market.US
        else:
            raise Exception("Unsupported market type:" + str(tigerMarketType))
        ps = self.TradeClient.get_positions(market = Market.US, sec_type=tigerSecurityType)
        all_items = self.__tiger_position_converter(ps)
        if(symbol is not None):
            return[p for p in all_items  if p.Symbol.casefold() == symbol.casefold()]
        else:
            return all_items
        


    def place_order(self, order:Order) -> OrderOperationResult:
        raise Exception("Not implemented.")


    def modify_order(self, order_id:str, new_quantity:int, new_price:float) -> OrderOperationResult:
        raise Exception("Not implemented.")
    

    def cancel_order(self, order_id:str) -> OrderOperationResult:
        raise Exception("Not implemented.")
    

    def query_order(self, order_id:str) -> OrderStatus:
        raise Exception("Not implemented.")
    
    
    def buy_position_to_close(self, opt_position:list[StockPosition]) -> list[OrderStatus]:
        logging.debug("buy_position_to_close called.")
        return []

    
    def sell_put_option_to_open(self, symbol:str, strike:float, quantity:int, expired_date:date) -> list[OrderStatus]:
        logging.debug("sell_position_to_open called.")
        return []
    
    
    def sell_position_to_close(self, opt_position:list[StockPosition]) -> list[OrderStatus]:
        logging.debug("sell_position_to_close called.")
        return []
    
    def sell_stock_to_close(self, symbol:str) -> list[OrderStatus]:
        logging.debug("sell_stock_to_close called.")
        return []
    
    def get_option_position(self, optMarket: OrderMarket, symbol:str, optionType:OptionType, expiry:date) -> list[OrderStatus]:
        put_call = ""
        if optionType == OptionType.CALL:
            put_call = "CALL"
        elif optionType == OptionType.PUT:
            put_call = "PUT"
        else:
            raise Exception("Unsupported OptionType:" + str(optionType))
        
        tigerMarketType = Market.US
        if optMarket == OrderMarket.US:
            tigerMarketType = Market.US
        else:
            raise Exception("Unsupported market type:" + str(tigerMarketType))
        
        ps = self.TradeClient.get_positions(market = tigerMarketType, sec_type = tst.OPT, expiry = expiry.strftime("%Y%m%d"))
        return self.__tiger_position_converter(ps)

    def __tiger_position_converter(self, ps:list) -> list[StockPosition]:
        positions = []
        if ps is not None:
            for p in ps:
                positions.append(StockPosition(Account = p.account,
                                               Exchange= p.contract.currency,
                                               Symbol = p.contract.symbol,
                                               Id = p.contract.identifier,
                                               AverageCost = p.average_cost,
                                               Quantity= p.quantity,
                                               SecurityType = SecurityType.OPT,
                                               OptionType = get_option_type_from_str(p.contract.put_call),
                                               TradingDate = "",
                                               MarketValue = p.market_value,
                                               MarketPrice= p.market_price,
                                               Expiry= p.contract.expiry,
                                               Strike= p.contract.strike
                                               ))
        return positions