import imaplib
import smtplib

import json

import email
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from os.path import basename

from string import Template
import re

import time


class MailServer:
    processed_mails = []

    def __init__(self, conf):
        self.from_addr = conf['FromAddress']
        self.admin_addr = conf['AdminEmail']

        self.imap_address = conf['IMAPAddress']
        self.imap_port = conf.getint('IMAPPort')
        self.smtp_address = conf['SMTPAddress']
        self.smtp_port = conf.getint('SMTPPort')

        self.login = conf['Login']
        self.password = conf['Password']

        self.subject_filter = conf['SubjectFilter']
        self.confirm_sub = conf['ConfirmSubject']

        self.confirm_date = time.strftime("%B %d", time.localtime(conf.getint('MatchDeadline')))

        with open("emailtemp.html", "r") as f:
            self.template = Template(f.read())
        try:
            with open("processed.json", 'r') as f:
                self.processed_mails = json.load(f)
        except FileNotFoundError:
            with open("processed.json", 'w+') as f:
                f.write("[]")

    def send_mail(self, content, target_email):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self.confirm_sub
        msg["From"] = self.from_addr
        msg["To"] = target_email

        text = content
        html = self.gen_mail(re.sub("\n", "\n<br>\n", content))

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        for i in range(10):
            try:
                self.smtp.sendmail(self.login, target_email, msg.as_string())
            except smtplib.SMTPServerDisconnected as e:
                print ("could not send email due to error:")
                print(e)
                self.connect_smtp()
                continue
            break

    def send_admin(self, file, text):
        msg = MIMEMultipart()
        msg["Subject"] = "FelixBot Secret Santa Matches"
        msg["From"] = self.from_addr
        msg["To"] = self.admin_addr
        msg["Date"] = formatdate(localtime=True)

        msg.attach(MIMEText(text))
        with open(file, "rb") as f:
            part = MIMEApplication(
                f.read(),
                Name=basename(file)
            )
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(file)
            msg.attach(part)
        self.smtp.sendmail(self.login, self.admin_addr, msg.as_string())
        print("Sent admin email to %s" % self.admin_addr)

    def gen_mail(self, content):
        return self.template.substitute(message=content)

    def send_confirm(self, status, target_email):
        content = status
        content += "\n"
        content += "Matches will be assigned on " + self.confirm_date
        content += " nyaa~"

        self.send_mail(content, target_email)
        print("Confirmation email sent.")

    def send_matches(self, matches_list):
        for participant, match in matches_list:
            message = "You have been matched against a challenger known as " + str(match["name"])
            message += ", who has requested '" + match["request"] + "'. Happy drawing nya~~"

            self.send_mail(message, participant["email"])
            print("Sent match to %s" % participant["email"])

    def connect(self):
        connect_imap()
        connect_smtp()

    def connect_imap(self):
        print("Connecting to IMAP4 server " + self.imap_address)
        self.mail = imaplib.IMAP4_SSL(self.imap_address, self.imap_port)
        self.mail.login(self.login, self.password)
        print("Done.")

    def connect_smtp(self):
        print("Connecting to SMTP server " + self.smtp_address)
        self.smtp = smtplib.SMTP(self.smtp_address, self.smtp_port)
        self.smtp.starttls()
        self.smtp.login(self.login, self.password)
        print("Done.")

    def update_mail(self, matchmaker):
        for i in range(10):
            try:
                self.mail.select()
                sub_filter = '(SUBJECT "' + self.subject_filter + '")'
                typ, data = self.mail.search(None, sub_filter)

                for num in data[0].split():
                    if str(num, "utf-8") in self.processed_mails:
                        continue
                    self.processed_mails.append(str(num, "utf-8)"))
                    with open("processed.json", "w") as f:
                        json.dump(self.processed_mails, f)
                    typ, data = self.mail.fetch(num, '(RFC822)')
                    email_message = email.message_from_bytes(data[0][1])

                    sender = email_message.get('From')
                    if sender == None:
                        sender = "Unknown"
                    payload = ""

                    subject = email_message.get('Subject')
                    if subject.lower() == self.subject_filter.lower():
                        if email_message.is_multipart():
                            for part in email_message.walk():
                                ctype = part.get_content_type()
                                cdispo = str(part.get('Content-Disposition'))
                                if ctype == 'text/plain' and 'attachment' not in cdispo:
                                    payload = part.get_payload(decode=True)
                                    break
                        else:
                            payload = email_message.get_payload(decode=True)

                        #Got email details, add it to matchmaker
                        status, p = matchmaker.add_participant(sender, payload.decode("unicode_escape"))
                        self.send_confirm(status, p["email"])
            except smtplib.SMTPServerDisconnected as e:
                print ("could not check email due to error:")
                print(e)
                self.connect_imap()
                continue
            break
