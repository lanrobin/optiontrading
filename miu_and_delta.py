import smtplib
import env
import logging_util
import market_date_utils
import datetime
import logging
import file_util
import os
import fnmatch
import smtplib
import ssl
from email.header import Header 
from email.mime.text import MIMEText
import time
import shutil
import sys
import argparse
from stock_tiger import TigerStockClient
from tigeropen.common.consts import BarPeriod
import numpy as np

G_debug_main_method = True
G_target_symbol = "QQQ"
G_broker_name = "TIGER"
G_account = None
G_prod_env = False

def get_stock_client(brokerName:str):
    if brokerName.casefold() == "TIGER".casefold():
        return TigerStockClient()
    else:
        raise Exception("Unknown broker:" + brokerName)

def to_datetime(milliseconds:int):
    seconds = milliseconds / 1000
    dt = datetime.datetime.fromtimestamp(seconds)
    return dt

def distribution(data):
    # 我们把数据按0.1%来归一化。先算出随机变量的期望和方差
    cannonicalData = []
    for d in data:
        cannonicalData.append(int(d * 100)/100.0)

    possibilities = {}
    for d in cannonicalData:
        if(d not in possibilities):
            possibilities[d] = 0
        possibilities[d] = possibilities[d] + 1

    exp = 0.0
    dataLength = len(cannonicalData)
    for k,v in possibilities.items():
        exp += k * v / dataLength
    
    print("期望值：" + str(exp))
    print("最大值：" + str(max(cannonicalData)))
    print("最小值：" + str(min(cannonicalData)))
    #plt.hist(cannonicalData, bins=1, color="pink", edgecolor="b")
    #plt.show()
    
    print("均值:" + str(np.mean(cannonicalData)))
    # 求一下标准差
    print("方差:" + str(np.var(cannonicalData)))
    stdValue = np.std(cannonicalData)
    print("标准差:" + str(stdValue))
    return exp, stdValue

def main():
    global G_debug_main_method
    global G_target_symbol
    global G_broker_name
    global G_prod_env

    parser = argparse.ArgumentParser(description='email_sender script')
    parser.add_argument('--debug', '-d', help='Enable debug this script')
    parser.add_argument('--symbol', '-s', help='Symbol to get the miu and delta')
    parser.add_argument('--broker', '-b', help='Broker name to use')
    parser.add_argument('--account', '-a', help='Account of the broker to use')
    args, unknown = parser.parse_known_args()

    G_debug_main_method = True if "TRUE".casefold() == args.debug.casefold() else False
    G_target_symbol = args.symbol.upper()
    G_broker_name = args.broker.upper()
    G_account = args.account

    logging_util.setup_logging(f"email_server")

    if G_account == None:
        logging.error(f"G_account is None.")
        raise("G_account is None.")

    stockClient = get_stock_client(G_broker_name)


    stockClient.initialize(prod_env=G_prod_env, account=G_account, symbol=G_target_symbol)

    #'''
    history_start_time = datetime.datetime.strptime("2002-01-01", '%Y-%m-%d')
    history_end_time = history_start_time + datetime.timedelta(days=365)
    week_k_list = stockClient.QuoteClient.get_bars(symbols=["TLT"], period=BarPeriod.DAY, begin_time=history_start_time.strftime('%Y-%m-%d'), end_time= history_end_time.strftime('%Y-%m-%d'), limit=1000)
    weekly_lines = ["Date,Open,High,Low, Close, Volume"]
    all_changes = []
    dedup_dict = {}
    while len(week_k_list.values) > 0:
        for i,v in enumerate(week_k_list.values):
            dt_str = to_datetime(v[1]).strftime('%Y-%m-%d')
            line = f"{dt_str},{v[2]},{v[3]},{v[4]},{v[5]},{v[6]}"
            if dt_str not in dedup_dict.keys():
                print(line)
                weekly_lines.append(line)
                dedup_dict[dt_str] = [dt_str,v[2],v[3],v[4],v[5],v[6]]
        
        logging.debug("sleep 2 seconds and continue.")
        time.sleep(2)
        history_start_time = history_end_time
        history_end_time = history_end_time + datetime.timedelta(days=365)
        week_k_list = stockClient.QuoteClient.get_bars(symbols=[G_target_symbol], period=BarPeriod.DAY, begin_time=history_start_time.strftime('%Y-%m-%d'), end_time= history_end_time.strftime('%Y-%m-%d'), limit=1000)
        
    file_path = f"{env.get_data_root_path()}/{G_target_symbol}_weekly.csv"
    with open(file_path, "w") as f:
        f.writelines(weekly_lines)

    #exp, stdValue = distribution(all_changes)
    
    logging.debug(f"write {len(weekly_lines)} lines to file:{file_path}")
    #'''

    volatility_file_path = f"{env.get_data_root_path()}/volatility/{G_target_symbol}weekly.csv"
    
    dedup_dict = {}
    all_changes = []
    with open(volatility_file_path, "r") as f:
        lines = f.read().splitlines()[1:]
        for l in lines:
            parts = l.split(',')
            dedup_dict[parts[0]] = []

    #o_chains = stockClient.QuoteClient.get_option_chain(symbol=G_target_symbol, expiry=stock_expiry)

    h_list = stockClient.QuoteClient.get_option_bars(identifiers=["TLT 210521P00131000"], begin_time="2021-05-14", end_time="2021-05-21", period=BarPeriod.DAY)

    print(h_list)

    '''
    for k,v in dedup_dict.items():
        strike = int(float(int(v[1] * (1 + exp) * 2))/2*1000)
        expiry_date = datetime.datetime.strptime(k, "%Y-%m-%d") - datetime.timedelta(3)
        expiry_str = expiry_date.strftime('%y%m%d')
        option_start_time = expiry_date - datetime.timedelta(7)
        id = f"{G_target_symbol} {expiry_str}P{strike:0>8}"
        o_list = stockClient.QuoteClient.get_option_bars(identifiers=[id], begin_time=option_start_time.strftime('%Y-%m-%d'), end_time=k, period=BarPeriod.DAY)
        if len(o_list) > 0 and len(o_list.values) > 0:
            print(o_list)
        else:
            print(f"no option history for {id}")

        time.sleep(2)
    '''

if __name__ == "__main__":
    main()