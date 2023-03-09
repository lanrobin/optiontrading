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
from tigeropen.common.consts import OrderStatus as tos
from tigeropen.common.util.contract_utils import stock_contract, option_contract
from tigeropen.common.util.order_utils import (market_order,        # 市价单
                                            limit_order,         # 限价单
                                            stop_order,          # 止损单
                                            stop_limit_order,    # 限价止损单
                                            trail_order,         # 移动止损单
                                            order_leg)           # 附加订单

import env
import logging
import realtime_quote
from jproperties import Properties



class TigerOrderStatus(OrderStatus):
    def __init__(self, order) -> None:
        super().__init__(order)

    def get_order_status(self) -> OrderStatusType:
        if self.brokerOrder is None:
            return OrderStatusType.UNKNOWN
        elif self.brokerOrder.status == tos.EXPIRED:
            return OrderStatusType.EXPIRED
        elif self.brokerOrder.status == tos.NEW:
            return OrderStatusType.NEW
        elif self.brokerOrder.status == tos.CANCELLED:
            return OrderStatusType.CANCELLED
        elif self.brokerOrder.status == tos.HELD:
            return OrderStatusType.HELD
        elif self.brokerOrder.status == tos.PARTIALLY_FILLED:
            return OrderStatusType.PARTIALLY_FILLED
        elif self.brokerOrder.status == tos.FILLED:
            return OrderStatusType.FILLED
        elif self.brokerOrder.status == tos.REJECTED:
            return OrderStatusType.REJECTED
        else:
            raise Exception("Unknown order status:" + str(self.brokerOrder.status))

    def get_order_id(self) -> str:
        return str(self.brokerOrder.id) if self.brokerOrder is not None else ""

    def get_order_quatity(self) -> int:
        return self.brokerOrder.quantity if self.brokerOrder is not None else 0

    def get_order_filled(self) -> int:
        return self.brokerOrder.filled if self.brokerOrder is not None else 0

    def get_order_remaining(self) -> str:
        return self.brokerOrder.remaining if self.brokerOrder is not None else 0
    
    def __str__(self) -> str:
        if self.brokerOrder is None:
            return "Invalid OrderStatus"
        else:
            return f"OrderStatus, id:{self.get_order_id()},status:{self.get_order_status()}"

class TigerStockClient(IStockClient):

    def __init__(self) -> None:
        super().__init__()
        self.TradeClient = None
        self.QuoteClient = None
        self.AccountId = None


    def initialize(self, prod_env:bool):
        config_path = ""
        if prod_env:
            config_path = f"{env.get_data_root_path()}/tigersandbox"
        else:
            config_path = f"{env.get_data_root_path()}/tigerprod"

        configs = Properties()
        with open(f"{config_path}/tiger_openapi_config.properties", 'rb') as read_prop:
            configs.load(read_prop)

        
        client_config = TigerOpenClientConfig(sandbox_debug=False, props_path=config_path)
        client_config.log_level = logging.DEBUG
        client_config.log_path = env.get_data_root_path() + "/log/tigerapi.log"
        client_config.timezone = "America/New_York"
        client_config.tiger_id = configs["tiger_id"].data
        client_config.account = configs["account"].data
        client_config.private_key = configs["private_key_pk1"].data

        # 接口超时时间
        client_config.timeout = 15
        # 超时重试设置
        # 最长重试时间，单位秒
        client_config.retry_max_time = 60
        # 最多重试次数
        client_config.retry_max_tries = 5
        self.TradeClient = TradeClient(client_config)
        self.AccountId = configs["account"].data
    

    def get_option_chain(self, symbol:str, expire_date_str:str, type:OptionType) -> List[StockOption]:
        option_type = "CALL"
        if type == OptionType.PUT:
            option_type = "PUT"
        elif option_type == "CALL":
            option_type = "CALL"
        else:
            raise Exception("Unsupport option type:" + type)

        opt_data = realtime_quote.get_option_chain(symbol=symbol, expired_date_str=expire_date_str, option_type=option_type)
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
        order = self.TradeClient.get_order(id = order_id)
        return OrderStatus(id = order_id, error_id="0", error_msg="OK", order = order)
    
    
    def buy_option_to_close(self, id:str, opt_type:OptionType, quantity:int) -> OrderStatus:
        logging.info("buy_option_to_close called.")
        contract = option_contract(identifier = id)

        order = market_order(account = self.AccountId, contract = contract, action = "BUY", quantity=quantity)

        self.TradeClient.place_order(order)

        return OrderStatus(order.id, "0", "OK", order)

    
    def sell_put_option_to_open(self, symbol:str, strike:float, quantity:int, expired_date:date) -> OrderStatus:
        logging.info("sell_position_to_open called.")
        expiry_str = expired_date.strftime("%Y-%m-%d")
        option_chains = self.get_option_chain(symbol = symbol, expire_date_str = expiry_str, type = OptionType.PUT)
        target_option = None
        for oc in reversed(option_chains):
            if oc.Strike < strike:
                target_option = oc
                break
        if target_option == None:
            raise Exception("Unable find suitable for symbol:" + symbol +" at strike:" + str(strike) +" in expiry:" + expiry_str)
        id = target_option.Id[0:len(symbol)] + "  " + target_option.Id[len(symbol):]

        contract = option_contract(identifier = id)

        order = market_order(account = self.AccountId, contract = contract, action = "SELL", quantity=quantity)

        self.TradeClient.place_order(order)

        return OrderStatus(order.id, "0", "OK", order)
    
    
    def sell_position_to_close(self, opt_position:StockPosition) -> OrderStatus:
        logging.info("sell_position_to_close called.")
        return []
    
    def sell_stock_to_close(self, symbol:str, quantity:int) -> OrderStatus:
        contract = stock_contract(symbol=symbol, currency='USD')
        order = market_order(account = self.AccountId, contract = contract, action="SELL",quantity = quantity)
        self.TradeClient.place_order(order)
        return OrderStatus(id = order.id, error_id="0", error_msg="OK", order = order)

    
    def sell_all_stock_to_close(self, symbol:str) -> OrderStatus:
        stock_position = self.get_position(market = OrderMarket.US, security_type=SecurityType.STK, symbol=symbol)
        result = None
        if len(stock_position) == 0:
            logging.info("No position for symbol:" + symbol)
            return OrderStatus("", "", "", None)
        elif len(stock_position) == 1:
            quantity = stock_position[0].Quantity
            succeeded = self.sell_stock_to_close(symbol = symbol, quantity=quantity)
            logging.info("There must be some stocks, sell them to close, result:" + str(succeeded))
            return succeeded
        else:
            logging.error("Incorrect position for symbol:" + symbol)
            raise Exception("Incorrect position for symbol:" + symbol +", count:" + str(len(stock_position)))

    def get_option_position(self, optMarket: OrderMarket, symbol:str, optionType:OptionType, expiry:date) -> List[StockPosition]:
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
        
        expiry_str = expiry.strftime("%Y%m%d")
        ps = self.TradeClient.get_positions(market = tigerMarketType, sec_type = tst.OPT, expiry = expiry_str)
        raw_position = self.__tiger_position_converter(ps)
        return [r for r in raw_position if r.Expiry == expiry_str]
    
    def __convert_security_type(self, tigerType: tst) -> SecurityType:
        if tst.OPT == tigerType:
            return SecurityType.OPT
        elif tst.STK == tigerType:
            return SecurityType.STK

    def __get_option_type(self, put_call:str) -> OptionType:
        if put_call is None:
            return OptionType.NONE
        if put_call.casefold() == "CALL".casefold():
            return OptionType.CALL
        if put_call.casefold() == "PUT".casefold():
            return OptionType.PUT
        return OptionType.NONE
        
    def __tiger_position_converter(self, ps:list) -> List[StockPosition]:
        positions = []
        if ps is not None:
            for p in ps:
                positions.append(StockPosition(Account = p.account,
                                               Exchange= p.contract.currency,
                                               Symbol = p.contract.symbol,
                                               Id = p.contract.identifier,
                                               AverageCost = p.average_cost,
                                               Quantity= p.quantity,
                                               SecurityType = self.__convert_security_type(p.contract.sec_type),
                                               OptionType = self.__get_option_type(p.contract.put_call),
                                               TradingDate = "",
                                               MarketValue = p.market_value,
                                               MarketPrice= p.market_price,
                                               Expiry= p.contract.expiry,
                                               Strike= p.contract.strike
                                               ))
        return positions