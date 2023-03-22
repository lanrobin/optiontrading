from stock_base import *
import json
import re
from snbpy.common.domain.snb_config import SnbConfig
from snbpy.snb_api_client import SnbHttpClient
from snbpy.common.constant.snb_constant import API_VERSION, HttpMethod, OrderSide, Currency, TimeInForce, \
    OrderType
from snbpy.common.constant.snb_constant import SecurityType as SST
import logging
from datetime import date, datetime
import uuid
import typing

#Snowball Settings
class SnowballSettings(object):
    def __init__(self, account, key, url):
        self.account = account
        self.key = key
        self.url = url


class SnbOrderStatus(OrderStatus):
    def __init__(self, order) -> None:
        super().__init__(order)

    def get_order_status(self) -> OrderStatusType:
        return SnbOrderStatus.convert_order_status(self.brokerOrder)
    def get_order_id(self) -> str:
        return str(self.brokerOrder["id"]) if self.brokerOrder is not None else ""

    def get_order_quatity(self) -> int:
        return self.brokerOrder["quantity"] if self.brokerOrder is not None else 0

    def get_order_filled(self) -> int:
        return self.brokerOrder["filled_quantity"] if self.brokerOrder is not None else 0

    def get_order_remaining(self) -> str:
        return self.brokerOrder["quantity"] - self.brokerOrder["filled_quantity"] if self.brokerOrder is not None else 0
    
    def __str__(self) -> str:
        if self.brokerOrder is None:
            return "Invalid OrderStatus"
        else:
            return f"OrderStatus, id:{self.get_order_id()},status:{self.get_order_status()}"
    @staticmethod
    def convert_order_status(order) -> OrderStatusType:
        if order is None:
            return OrderStatusType.UNKNOWN
        elif order["status"] == "EXPIRED":
            return OrderStatusType.EXPIRED
        elif order["status"] == "REPORTED":
            return OrderStatusType.NEW
        elif order["status"] == "WITHDRAWED":
            return OrderStatusType.CANCELLED
        elif order["status"] == "WAIT_REPORT":
            return OrderStatusType.HELD
        elif order["status"] == "PART_CONCLUDED":
            return OrderStatusType.PARTIALLY_FILLED
        elif order["status"] == "CONCLUDED":
            return OrderStatusType.FILLED
        elif order["status"] == "INVALID":
            return OrderStatusType.REJECTED
        else:
            raise Exception("Unknown order status:" + str(order["status"]))


class SnowballStockClient(IStockClient):

    def __init__(self) -> None:
        super().__init__()
        self.SnbHttpClient = None
        self.QuoteClient = None
        self.AccountId = None


    def initialize(self, prod_env:bool, account:str, symbol:str):
        config_path = ""
        if prod_env:
            config_path = f"{env.get_data_root_path()}/snbprod/SnowballSettings.json"
        else:
            config_path = f"{env.get_data_root_path()}/snbsandbox/SnowballSettings.json"

        josnStr = ""
        with open(config_path, "r") as f:
            jsonStr = re.sub(r'\s+', '', f.read())
        
        j = json.loads(jsonStr)
        settings = SnowballSettings(**j)

        config = SnbConfig()
        config.account = settings.account
        config.key = settings.key
        config.sign_type = 'None'
        config.snb_server = settings.url
        config.snb_port = '443'
        config.timeout = 1000
        config.schema = 'https'

        self.SnbHttpClient = SnbHttpClient(config)
        self.SnbHttpClient.login()
        self.AccountId = settings.account


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
        snb_security_type = "STK"
        if security_type == SecurityType.OPT:
            snb_security_type = "OPT"
        elif security_type == SecurityType.STK:
            snb_security_type = "STK"
        else:
            raise Exception("Unsupported security type:" + str(security_type))

        resp = self.SnbHttpClient.get_position_list(security_type=snb_security_type)
        items = []
        if(resp is not None and len(resp.data) > 0):
            items = self.__snb_position_converter(resp.data, symbol)
        return [i for i in items if i.Symbol.casefold() == symbol.casefold()]
        


    def place_order(self, order:Order) -> OrderOperationResult:
        raise Exception("Not implemented.")


    def modify_order(self, order_id:str, new_quantity:int, new_price:float) -> OrderOperationResult:
        raise Exception("Not implemented.")
    

    def cancel_order(self, order_id:str) -> OrderOperationResult:
        raise Exception("Not implemented.")
    

    def query_order(self, order_id:str) -> OrderStatus:
        order = self.SnbHttpClient.get_order_by_id(order_id)
        return SnbOrderStatus(order = order)
    
    
    def buy_option_to_close(self, id:str, opt_type:OptionType, quantity:int) -> OrderStatus:
        logging.info("buy_option_to_close called.")
        order_id = self.__generate_new_order_id()
        security_type = SST.OPT
        exchange = "USEX"
        side = OrderSide.BUY
        currency = Currency.USD
        price  = 0
        order_type = OrderType.MARKET
        tif = TimeInForce.DAY
        force_only_rth = True
        resp = self.SnbHttpClient.place_order(order_id=order_id,
                                             security_type=security_type,
                                             symbol=id,
                                             exchange=exchange,
                                             side=side,
                                             currency=currency,
                                             quantity=quantity,
                                             price=price,
                                             order_type=order_type,
                                             tif=tif,
                                             force_only_rth=force_only_rth)
        
        logging.debug(f"place order:{order_id} on symbol:{id} resp code:{resp.result_code}, msg:{resp.result_str}")
        order_resp = self.SnbHttpClient.get_order_by_id(order_id=order_id)

        return self.__snb_order_converter([order_resp.data])

    
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
        id = target_option.Id

        order_id = self.__generate_new_order_id()
        security_type = SST.OPT
        exchange = "USEX"
        side = OrderSide.SELL
        currency = Currency.USD
        price  = 0
        order_type = OrderType.MARKET
        tif = TimeInForce.DAY
        force_only_rth = True
        resp = self.SnbHttpClient.place_order(order_id,
                                             security_type,
                                             id,
                                             exchange,
                                             side,
                                             currency,
                                             quantity,
                                             price,
                                             order_type,
                                             tif,
                                             force_only_rth)
        
        logging.debug(f"place order:{order_id} on symbol:{id} resp code:{resp.result_code}, msg:{resp.result_str}")
        order_resp = self.SnbHttpClient.get_order_by_id(order_id=order_id)

        return self.__snb_order_converter([order_resp.data])
    
    
    def sell_position_to_close(self, opt_position:StockPosition) -> OrderStatus:
        logging.info("sell_position_to_close called.")
        raise Exception("Not implemented.")
    
    def sell_stock_to_close(self, symbol:str, quantity:int) -> OrderStatus:
        order_id = self.__generate_new_order_id()
        security_type = SST.STK
        exchange = "USEX"
        side = OrderSide.SELL
        currency = Currency.USD
        price  = 0
        order_type = OrderType.MARKET
        tif = TimeInForce.DAY
        force_only_rth = True
        resp = self.SnbHttpClient.place_order(order_id=order_id,
                                             security_type=security_type,
                                             symbol=symbol,
                                             exchange=exchange,
                                             side=side,
                                             currency=currency,
                                             quantity=quantity,
                                             price=price,
                                             order_type=order_type,
                                             tif=tif,
                                             force_only_rth=force_only_rth)
        
        logging.debug(f"place order:{order_id} on symbol:{id} resp code:{resp.result_code}, msg:{resp.result_str}")
        order_resp = self.SnbHttpClient.get_order_by_id(order_id=order_id)

        return self.__snb_order_converter([order_resp.data])

    def buy_stock_to_open(self, symbol: str, quantity: int) -> OrderStatus:
        order_id = self.__generate_new_order_id()
        security_type = SST.STK
        exchange = "USEX"
        side = OrderSide.BUY
        currency = Currency.USD
        price  = 0
        order_type = OrderType.MARKET
        tif = TimeInForce.DAY
        force_only_rth = True
        resp = self.SnbHttpClient.place_order(order_id=order_id,
                                             security_type=security_type,
                                             symbol=symbol,
                                             exchange=exchange,
                                             side=side,
                                             currency=currency,
                                             quantity=quantity,
                                             price=price,
                                             order_type=order_type,
                                             tif=tif,
                                             force_only_rth=force_only_rth)
        
        logging.debug(f"place order:{order_id} on symbol:{id} resp code:{resp.result_code}, msg:{resp.result_str}")
        order_resp = self.SnbHttpClient.get_order_by_id(order_id=order_id)

        return self.__snb_order_converter([order_resp.data])
    
    def sell_all_stock_to_close(self, symbol:str) -> OrderStatus:
        stock_position = self.get_position(market = OrderMarket.US, security_type=SecurityType.STK, symbol=symbol)
        result = None
        if len(stock_position) == 0:
            logging.info("No position for symbol:" + symbol)
            return SnbOrderStatus(order = None)
        elif len(stock_position) == 1:
            quantity = stock_position[0].Quantity
            succeeded = self.sell_stock_to_close(symbol = symbol, quantity=quantity)
            logging.info(f"Sell {quantity} of {symbol} to close, result:{succeeded}")
            return succeeded
        else:
            logging.error(f"Incorrect number of position:{len(stock_position)} for symbol:{symbol}")
            raise Exception("Incorrect position for symbol:" + symbol +", count:" + str(len(stock_position)))

    def get_option_position(self, optMarket: OrderMarket, symbol:str, optionType:OptionType, expiry:date) -> List[StockPosition]:
        if optionType != OptionType.CALL and optionType != OptionType.PUT:
            raise Exception("Unsupported OptionType:" + str(optionType))
        
        expiry_str = expiry.strftime("%y%m%d")
        raw_position = self.get_position(market=optMarket, security_type=SecurityType.OPT, symbol=symbol)
        return [r for r in raw_position if r.Expiry == expiry_str and r.Symbol == symbol and r.OptionType == optionType]
    
    def sell_option_with_protection_to_open(self, symbol:str, opt_type: OptionType,strike:float, quantity:int, expired_date:date, protect_times:float) -> OrderStatus:
        logging.info("sell_position_to_open called.")
        raise Exception("sell_option_with_protection_to_open didn't implemented yet.")
    
    def get_account_id(self) -> str:
        return self.AccountId
    
    def get_open_option_orders(self, market: OrderMarket, symbol:str, opt_type: OptionType, expired_date:date) -> list:
        raw_orders = []
        resp = self.SnbHttpClient.get_order_list(page=1, size=10, status=None, security_type="OPT")
        raw_orders.extend(resp.data["items"])

        # if there are more orders, fetch them all.
        while resp is not None and resp.data["count"] >= resp.data["size"]:
            resp = self.SnbHttpClient.get_order_list(page=resp.data["page"] + 1, size=10, status=None, security_type="OPT")
            raw_orders.extend(resp.data["items"].values())
        target_orders = []
        id_prefix = f"{symbol}{expired_date.strftime('%y%m%d')}"

        if opt_type == OptionType.CALL:
            id_prefix = id_prefix + "C"
        elif opt_type == OptionType.PUT:
            id_prefix = id_prefix + "P"

        if raw_orders != None and len(raw_orders) > 0:
            filterred_orders = [o for o in raw_orders if o["symbol"].startswith(id_prefix) and o["status"] != "CONCLUDED" and o["status"] != "INVALID" and o["status"] != "EXPIRED"]
            target_orders = self.__snb_order_converter(filterred_orders)
        return target_orders
    
    def get_client_name(self) -> str:
        return "雪盈证券"

    def __convert_security_type(self, sec_type: str) -> SecurityType:
        
        if "OPT" == sec_type:
            return SecurityType.OPT
        elif "STK" == sec_type:
            return SecurityType.STK
        else:
            raise Exception(f"Unsupported security type:{sec_type}")

    @staticmethod
    def __get_option_type(id:str) -> OptionType:
        put_call = re.findall('[a-zA-Z]', id)
        if put_call is None or len(put_call) == 0:
            return OptionType.NONE
        if put_call[-1].casefold() == "C".casefold():
            return OptionType.CALL
        if put_call[-1].casefold() == "P".casefold():
            return OptionType.PUT
        return OptionType.NONE
    
    @staticmethod
    def __to_order_market_type(market: str) -> OrderMarket:

        snbMarketType = "None"
        if market == "USEX":
            snbMarketType = OrderMarket.US
        else:
            raise Exception("Unsupported market type:" + str(market))
        
        return snbMarketType
    
    @staticmethod
    def __to_snb_market_type(market: OrderMarket) -> OrderMarket:

        snbMarketType = "None"
        if market == OrderMarket.US:
            snbMarketType = "USEX"
        else:
            raise Exception("Unsupported market type:" + str(market))
        
        return snbMarketType
        
    def __snb_position_converter(self, ps:list, symbol:str) -> list:
        positions = []
        if ps is not None:
            for p in ps:
                sec_type = self.__convert_security_type(p["security_type"])
                strike = 0
                expiry = ""
                real_symbol = p["symbol"]
                if sec_type == SecurityType.OPT:
                    strike, expiry = self.__get_strike_and_expiry_from_symbol_id(p["symbol"])
                    real_symbol = self.__get_symbol_from_option_id(p["symbol"])
                positions.append(StockPosition(Account = p["account_id"],
                                               Exchange= p["exchange"],
                                               Symbol = real_symbol,
                                               Id = p["symbol"],
                                               AverageCost = p["average_price"],
                                               Quantity= p["position"],
                                               SecurityType = sec_type,
                                               OptionType = self.__get_option_type(p["symbol"]),
                                               TradingDate = "",
                                               MarketValue = p["market_price"] * p["position"],
                                               MarketPrice= p["market_price"],
                                               Expiry= expiry,
                                               Strike= strike
                                               ))
        return positions
    
    def __snb_order_converter(self, orders:list) -> list:
        common_orders = []
        if orders is not None:
            for o in orders:
                common_orders.append(Order(o["id"],
                                           self.__get_symbol_from_option_id(o["symbol"]),
                                           SnbOrderStatus.convert_order_status(o),
                                           o["side"],
                                           OrderOpenClose.CLOSE,
                                           o["tif"],
                                           self.__to_order_market_type(o["exchange"]),
                                           o["average_price"],
                                           o["quantity"],
                                           self.__convert_security_type(o["security_type"]),
                                           o["symbol"]
                                           ))
        
        return common_orders
    
    def __get_symbol_from_option_id(self, id:str)->str:
        result = ''
        for char in id:
            if char.isalpha():
                result += char
            else:
                break
        
        return result
    
    def __get_strike_and_expiry_from_symbol_id(self, id:str) -> typing.Tuple[float, str]:
        parts = re.findall(r'[0-9]+', id)
        if(len(parts) == 2):
            strike = float(parts[1])/1000.0
            return (strike, parts[0])
        
        return None

    def __generate_new_order_id(self)->str:
        return f"{self.AccountId}{int(datetime.now().timestamp())}"

if __name__ == "__main__":
    client = SnowballStockClient()
    client.initialize(False, "DU1730009", "QQQ")
    #items = client.get_position(OrderMarket.US, SecurityType.OPT, "SPY")
    #orders = client.get_open_option_orders(OrderMarket.US, "SPY", OptionType.PUT, date(year=2023, month=3, day=24))
    #opt_positions = client.get_option_position(OrderMarket.US, "SPY", OptionType.PUT, date(2023, 3, 24))
    order_status = client.buy_stock_to_open("QQQ", 5)
    print(str(order_status))
    order_status = client.sell_stock_to_close("QQQ", 5)
    print(str(order_status))
