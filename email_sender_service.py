import pyinotify
import env
import file_util
import logging
import logging_util
import os
import fnmatch
import shutil
import smtplib
import ssl
from email.header import Header 
from email.mime.text import MIMEText
import time

class MyEventHandler(pyinotify.ProcessEvent):

    def __init__(self, watch_foler:str, move_to_folder:str, pevent=None):
        super().__init__(pevent)
        self.WatchFoler = watch_foler
        self.MoveToFolder = move_to_folder

    def process_IN_CREATE(self, event):
        logging.debug(f"process_IN_CREATE with path:{event.pathname}")
        if event.pathname.endswith('.txt'):
            self.process_folder_event()

    def process_IN_MOVED_TO(self, event):
        logging.debug(f"process_IN_MOVED_TO with path:{event.pathname}")
        if event.pathname.endswith('.txt'):
            self.process_folder_event()
    
    def process_folder_event(self):
        emails = self.get_all_pending_emails(self.WatchFoler, f"{env.get_email_file_prefix()}*.txt")
        if len(emails) > 0:
            settings = env.GLOBAL_SETTING
            sender =  settings.sender # 发件人邮箱(最好写全, 不然会失败) 
            receivers = [settings.receiver] # 接收邮件，可设置为你的QQ邮箱或者其他邮箱 
            retry_times = 0
            while retry_times < 5:
                try: 
                    #context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                    smtpObj = smtplib.SMTP(settings.smtpUrl, settings.smtpPort) # 启用SSL发信, 端口一般是465
                    smtpObj.ehlo()
                    #smtpObj.starttls(context=context)
                    smtpObj.starttls()
                    smtpObj.ehlo()
                    smtpObj.login(settings.userName, settings.passWord) # 登录验证
                    for email in emails:
                        subject, content = self.extract_email(email)
                        logging.debug(f"Try to send email subject:{subject}, content:{content}")
                        message = MIMEText(content, 'plain', 'utf-8') # 内容, 格式, 编码 
                        message['From'] = "{}".format(sender) 
                        message['To'] = ",".join(receivers) 
                        message['Subject'] = subject
                        smtpObj.sendmail(sender, receivers, message.as_string()) # 发送
                        self.move_file_to_sent(email, self.MoveToFolder)
                    
                    logging.info(f"{len(emails)} 封邮件已经发送。")
                    break
                except smtplib.SMTPException as innerE: 
                    retry_times += 1
                    logging.error(f"Send email failed {retry_times} with error:{innerE}")
                    time.sleep(30 * retry_times)
        else:
            logging.debug("No pending email, sleep 5 seconds and try again.")

    def get_all_pending_emails(self, folder, pattern):
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
    
    def extract_email(self, email_file):
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

    def move_file_to_sent(self, old_file, new_folder):
        filename = os.path.basename(old_file)
        new_filepath = os.path.join(new_folder, filename)
        shutil.move(old_file, new_filepath)

def main():

    email_folder = f"{env.get_data_root_path()}/emails"
    sent_email_folder = f"{env.get_data_root_path()}/sent_emails"
    file_util.ensure_path_exists(email_folder)
    file_util.ensure_path_exists(sent_email_folder)

    logging_util.setup_logging(f"email_server")

    wm = pyinotify.WatchManager()
    handler = MyEventHandler(email_folder, sent_email_folder)
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(email_folder, pyinotify.IN_CREATE | pyinotify.IN_MOVED_TO)
    logging.debug(f"Begin to watch {email_folder}")
    notifier.loop()

if __name__ == "__main__":
   main()
