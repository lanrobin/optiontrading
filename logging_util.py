import file_util
import env
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging(fileName):
    logPath = env.get_data_root_path() + "/log/"
    file_util.ensure_path_exists(logPath)
    time_rotating_file_handler = logging.handlers.TimedRotatingFileHandler(filename= logPath +"/"+fileName + '.log', when='D', interval=1, backupCount=7, encoding='utf-8')
    time_rotating_file_handler.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
                # filename=file_name,
                # filemode='a',
                handlers=[time_rotating_file_handler, logging.StreamHandler(sys.stdout)],
                )