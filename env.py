import platform
import logging
from pathlib import Path
import json
import re
from datetime import datetime
import sys
import utils
import time
import uuid

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

def __generate_email_file(subject, content):
    """
    Generate a new email file with the specified content and subject.

    Parameters:
    content (str): The content of the email.
    subject (str): The subject of the email.

    Returns:
    The path to the newly created email file.
    """
    filename = f"pending_email_{uuid.uuid4()}.txt"
    filepath = f'{get_data_root_path()}/emails/{filename}'

    with open(filepath, 'w') as f:
        f.write(f"SUBJECT--{subject}\n")
        f.write(f"CONTENT---{content}\n")
        f.write(f"TIME---{datetime.now()}\n")

    return filepath

def send_email(subject, content):
    __generate_email_file(subject, content)


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