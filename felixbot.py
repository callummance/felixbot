import os

import mailconnection
import matchmaker

import configparser
import csv
import time


class Bot:
    def __init__(self, conffile):

        configParser = configparser.ConfigParser()
        configParser.read(conffile)

        self.conf = configParser['DEFAULT']

        date_str = time.strftime("%B %d", time.localtime(self.conf.getint('MatchDeadline')))

        self.confirm_date = self.conf.getint('MatchDeadline')
        self.conn = mailconnection.MailServer(self.conf)
        self.conn.connect()
        self.mm = matchmaker.Matchmaker(self.conf["BackupFile"], self.conf["ResultsFile"])

    def monitor(self, polltime):
        print("Now Listening...")
        while True:
            self.conn.update_mail(self.mm)
            time.sleep(polltime)

            if self.should_match():
                matches = self.mm.make_matches()
                if not self.has_already_run():
                    self.conn.send_matches(matches)
                else:
                    print("Matches have already been sent out, bot will now terminate.")
                self.write_csv(matches)
                return

    def should_match(self):
        return self.confirm_date < time.time()

    def has_already_run(self):
        return os.path.exists(self.conf['ResultsCSV'])

    def write_csv(self, matches):
        with open(self.conf['ResultsCSV'], 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',', lineterminator='\n')
            csvwriter.writerow(["Name",
                                "Email",
                                "Request",
                                "Fulfilled by (name)",
                                "Fulfilled by (email)"])
            for p, m in matches:
                csvwriter.writerow([m["name"],
                                    m["email"],
                                    m["request"],
                                    p["name"],
                                    p["email"]
                                    ])
        self.conn.send_admin(self.conf['ResultsCSV'], "A csv file containing a list of matches has been attached.")









def main():
    felix = Bot("./felix.conf")
    felix.monitor(10)


if __name__ == '__main__':
    main()

