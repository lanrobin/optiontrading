import utils
import env
import re
import json

# we make it singleton
class ZVSTSSetting(metaclass = utils.Singleton):
    def __init__(self, id:str, key:str, ss: list):
        self.Id = id
        self.Key = key
        self.SubscribeSymobl = ss

def __get_zvsts_settings():
    settingPath = env.get_data_root_path() +"/ZVSTSSettings.json"
    jsonStr = ""
    with open(settingPath, "r") as f:
        jsonStr = re.sub(r'\s+', '', f.read())
    
    j = json.loads(jsonStr)
    s = ZVSTSSetting(**j)
    return s

ZVSTS_SETTING = __get_zvsts_settings()