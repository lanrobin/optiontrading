import platform
import logging
from pathlib import Path
import json
import smtplib
from email.header import Header 
from email.mime.text import MIMEText
import re
from datetime import datetime
import sys
import ssl
import utils


def get_data_root_path():
    path = ""
    if platform.system().lower() == 'windows':
        path = "D:\\stock"
    elif platform.system().lower() == 'linux':
        if 'microsoft-standard' in platform.uname().release:
            path = "/home/lan/s"
        else:
            path = "/datadrive/stock"
    else:
        path = "/datadrive/stock"
    # Ensure the folder exists.
    Path(path).mkdir(parents=True, exist_ok=True)
    return path

# we make it singleton
class Settings(metaclass = utils.Singleton):
    def __init__(self, isProduction, smtpUrl, smtpPort, userName, passWord, sender, receiver, azureStorageConnectString):
        self.isProduction = isProduction
        self.smtpUrl = smtpUrl
        self.smtpPort = smtpPort
        self.userName = userName
        self.passWord = passWord
        self.sender = sender
        self.receiver = receiver
        self.azureStorageConnectString = azureStorageConnectString

def __get_settings():
    settingPath = get_data_root_path() +"/Settings.json"
    jsonStr = ""
    with open(settingPath, "r") as f:
        jsonStr = re.sub(r'\s+', '', f.read())
    
    j = json.loads(jsonStr)
    s = Settings(**j)
    return s


def send_email(subject, content):
    settings = GLOBAL_SETTING
    sender =  settings.sender # 发件人邮箱(最好写全, 不然会失败) 
    receivers = [settings.receiver] # 接收邮件，可设置为你的QQ邮箱或者其他邮箱 
    message = MIMEText(content, 'plain', 'utf-8') # 内容, 格式, 编码 
    message['From'] = "{}".format(sender) 
    message['To'] = ",".join(receivers) 
    message['Subject'] = subject
    
    try: 
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        smtpObj = smtplib.SMTP(settings.smtpUrl, settings.smtpPort) # 启用SSL发信, 端口一般是465
        smtpObj.ehlo()
        smtpObj.starttls(context=context)
        smtpObj.ehlo()
        smtpObj.login(settings.userName, settings.passWord) # 登录验证 
        smtpObj.sendmail(sender, receivers, message.as_string()) # 发送
        logging.info("邮件已经发送。")
    except smtplib.SMTPException as innerE: 
        logging.error(innerE)

GLOBAL_SETTING = __get_settings()


class OptionStrategySettings:
    def __init__(self, BackFillAfterSold:bool, ExpectedOptionContractNumber:int) -> None:
        self.BackFillAfterSold = BackFillAfterSold
        self.ExpectedOptionContractNumber = ExpectedOptionContractNumber


def get_option_strategy_setting():
    settingPath = get_data_root_path() +"/OptionStrategySettings.json"
    jsonStr = ""
    with open(settingPath, "r") as f:
        jsonStr = re.sub(r'\s+', '', f.read())
    
    j = json.loads(jsonStr)
    s = OptionStrategySettings(**j)
    return s