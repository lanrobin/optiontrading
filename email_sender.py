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

G_debug_main_method = True

'''When there are multiple process to trade, email sending has a concurrent problem.
So we create an standalone program to send all emails.'''

def get_all_pending_emails(folder, pattern):
    """
    Get a list of all files in the specified folder that start with the
    specified pattern.

    Parameters:
    folder (str): The folder path to search.
    pattern (str): The pattern to match.

    Returns:
    A list of file paths that match the pattern.
    """
    # Expand the user path and get a list of all files in the folder
    files = os.listdir(os.path.expanduser(folder))

    # Filter the list of files to only include those that match the pattern
    matching_files = [f for f in files if fnmatch.fnmatch(f, pattern)]

    # Construct the full file paths and return the list
    return [os.path.join(folder, f) for f in matching_files]

def extract_email(email_file):
    """
    Extract the subject and content from the specified email file.

    Parameters:
    email_file (str): The path to the email file to extract data from.

    Returns:
    A tuple containing the subject and content strings.
    """
    with open(email_file) as f:
        lines = f.readlines()

    subject = None
    content = None

    for line in lines:
        if line.startswith('SUBJECT--'):
            subject = line[len('SUBJECT--'):].strip()
        elif line.startswith('CONTENT---'):
            content = line[len('CONTENT---'):].strip()

        if subject is not None and content is not None:
            break

    return subject, content

def move_file_to_sent(old_file, new_folder):
    filename = os.path.basename(old_file)
    new_filepath = os.path.join(new_folder, filename)
    shutil.move(old_file, new_filepath)

def main():
    global G_debug_main_method

    parser = argparse.ArgumentParser(description='email_sender script')
    parser.add_argument('--debug', '-d', help='Enable debug this script')
    args, unknown = parser.parse_known_args()

    G_debug_main_method = True if "TRUE".casefold() == args.debug.casefold() else False

    logging_util.setup_logging(f"email_server")

    current = datetime.datetime.now()
    market_open_time = datetime.datetime.combine(current.date(), datetime.time(hour=9, minute=30))
    date_str = current.strftime("%Y-%m-%d")
    market_close_time = market_date_utils.get_market_close_time(date_str)

    email_folder = f"{env.get_data_root_path()}/emails"
    sent_email_folder = f"{env.get_data_root_path()}/sent_emails"
    file_util.ensure_path_exists(email_folder)
    file_util.ensure_path_exists(sent_email_folder)

    if not G_debug_main_method:
        if not market_date_utils.is_market_open(date_str):
            logging.warning("Market is not open today:" + date_str)
            return
        if current > market_close_time:
            logging.warning("Market is closed today at :" + market_date_utils.datetime_str(market_close_time))
            return
    
    logging.debug("Begin to monitor folder and send emails.")
    # we will extra 5 minutes after market close.
    while current < market_close_time + datetime.timedelta(minutes=5) or G_debug_main_method:

        emails = get_all_pending_emails(email_folder, "pending_email*.txt")
        if len(emails) > 0:
            settings = env.GLOBAL_SETTING
            sender =  settings.sender # 发件人邮箱(最好写全, 不然会失败) 
            receivers = [settings.receiver] # 接收邮件，可设置为你的QQ邮箱或者其他邮箱 
            retry_times = 0
            while retry_times < 5:
                try: 
                    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                    smtpObj = smtplib.SMTP(settings.smtpUrl, settings.smtpPort) # 启用SSL发信, 端口一般是465
                    smtpObj.ehlo()
                    smtpObj.starttls(context=context)
                    smtpObj.ehlo()
                    smtpObj.login(settings.userName, settings.passWord) # 登录验证
                    for email in emails:
                        content, subject = extract_email(email)
                        logging.debug(f"Try to send email subject:{subject}, content:{content}")
                        message = MIMEText(content, 'plain', 'utf-8') # 内容, 格式, 编码 
                        message['From'] = "{}".format(sender) 
                        message['To'] = ",".join(receivers) 
                        message['Subject'] = subject
                        smtpObj.sendmail(sender, receivers, message.as_string()) # 发送
                        move_file_to_sent(email, sent_email_folder)
                    
                    logging.info(f"{len(emails)} 封邮件已经发送。")
                    break
                except smtplib.SMTPException as innerE: 
                    retry_times += 1
                    logging.error(f"Send email failed {retry_times} with error:{innerE}")
                    time.sleep(30 * retry_times)
        else:
            logging.debug("No pending email, sleep 5 seconds and try again.")
        # sleep 5 seconds and try next round.
        time.sleep(5)
    logging.debug("Finished job.")


if __name__ == "__main__":
    env.send_email("测试主题", "测试内容从程序生成。")
    main()