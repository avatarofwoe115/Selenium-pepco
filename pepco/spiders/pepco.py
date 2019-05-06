from __future__ import division, absolute_import, unicode_literals
from scrapy import Spider
from selenium import webdriver
from time import sleep
import os
import csv
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime, timedelta, date


class PepcoSpider(Spider):
    name = "pepco"
    start_urls = [
        'https://secure.pepco.com/Pages/Login.aspx'
    ]
    passed_vals = []

    def __init__(self, download_directory=None, *args, **kwargs):
        super(PepcoSpider, self).__init__(*args, **kwargs)

        with open('Pepco Credentials All.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile)
            self.password_list = []
            self.username_list = []
            self.accountOwnerID_credential_list = []
            for row_index, row in enumerate(reader):
                if row_index != 0:
                    self.accountOwnerID_credential_list.append(row[0])
                    self.username_list.append(row[1])
                    self.password_list.append(row[2])

        with open('TEST_EquityMgmt2LLC-account_number REV.csv', 'rb') as csvfile_numbers:
            reader_numbers = csv.reader(csvfile_numbers)
            self.accountOwnerID_list = []
            self.accountNumber_list = []
            self.lastDownloadBillDate_list = []
            self.billCycleDays_list = []
            for row_index, row in enumerate(reader_numbers):
                if row_index != 0:
                    self.accountOwnerID_list.append(row[0])
                    self.accountNumber_list.append(row[1])
                    self.lastDownloadBillDate_list.append(row[2])
                    self.billCycleDays_list.append(row[3])

        self.user_index = 0

        self.download_directory = download_directory if download_directory else 'C:/Users/webguru/Downloads/pepco/'

        if not os.path.exists(self.download_directory):
            os.makedirs(self.download_directory)

        cwd = os.getcwd().replace("\\", "//").replace('spiders', '')
        opt = webdriver.ChromeOptions()
        opt.add_argument("--start-maximized")
        # opt.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path='{}/chromedriver.exe'.format(cwd), chrome_options=opt)

        with open('{}/scrapy.log'.format(cwd), 'r') as f:
            self.logs = [i.strip() for i in f.readlines()]
            f.close()

    def login(self, user_index=None):
        while True:
            try:

                user_email = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-group-double")]//input[contains(@id, "Username")]')
                user_name = self.username_list[user_index]
                password = self.password_list[user_index]
                user_email.send_keys(user_name)
                user_password = self.driver.find_element_by_xpath(
                    '//div[contains(@class, "exc-form-group-double")]//input[contains(@id,"Password")]'
                )
                user_password.send_keys(password)
                btn_login = self.driver.find_element_by_xpath(
                    '//button[contains(@processing-button, "Signing In...")]'
                )
                btn_login.click()
                break
            except:
                time.sleep(10)
                continue

    def parse(self, response):

        all_users_option = True

        user_index = 0
        accountOwnerID = self.accountOwnerID_list[user_index]
        login_index = self.accountOwnerID_credential_list.index(accountOwnerID)
        while all_users_option:

            if user_index == 0:
                self.driver.get(response.url)
            if self.driver.current_url != 'https://secure.pepco.com/Pages/Login.aspx':
                self.driver.get('https://secure.pepco.com/Pages/Login.aspx')
            self.login(login_index)
            time.sleep(3)

            account_index = 0
            all_numbers_option = True
            while all_numbers_option:

                if self.driver.current_url != 'https://secure.pepco.com/Pages/ChangeAccount.aspx':
                    self.driver.get('https://secure.pepco.com/Pages/ChangeAccount.aspx')

                time.sleep(15)

                account_number_search_input = self.driver.find_element_by_xpath(
                    '//div[contains(@id, "changeAccountDT1_filter")]//input[contains(@type, "search")]')

                account_number = self.accountNumber_list[account_index]
                # account_number = self.driver.find_elements_by_xpath(
                #     '//div[@class="exc-account-summary"]/p[contains(text(), "Account #")]/span')[0].text
                # account_number = '55019181241'

                account_number_search_input.send_keys(account_number)
                time.sleep(2)
                account_number_search_input.send_keys(Keys.ENTER)
                account_rows = self.driver.find_elements_by_xpath('//table[@id="changeAccountDT1"]//tbody//tr')

                if account_rows:
                    time.sleep(5)
                    view_button = account_rows[0].find_elements_by_xpath(
                        './/td[@class="action-cell ng-scope"]//button')
                    if view_button:
                        view_button[1].click()
                    else:
                        pass
                else:
                    pass

                time.sleep(3)
                if self.driver.current_url != 'https://secure.pepco.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx':
                    self.driver.get(
                        'https://secure.pepco.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx')
                    time.sleep(3)

                options = self.driver.find_elements_by_xpath('//select[@id="StatementType"]//option')
                if options:
                    statement_type = options[2]
                    statement_type.click()

                search_button = self.driver.find_elements_by_xpath(
                    '//button[@class="btn btn-primary" and @processing-button="Processing..."]'
                )
                if search_button:
                    search_button[0].click()
                else:
                    print "There is no search button"

                time.sleep(5)

                all_pages_crawled = False
                while not all_pages_crawled:
                    rows = self.driver.find_elements_by_xpath('//table//tbody//tr')
                    if rows:
                        row = rows[0]
                        bill_date_info = row.find_elements_by_xpath('.//td')[0].text.split('/')
                        if bill_date_info[0] != 'No results found.':
                            bill_date = bill_date_info[2] + bill_date_info[0] + bill_date_info[1]

                            print_btn = row.find_elements_by_xpath(
                                './/td//button[contains(text(), "View")]')[0]

                            last_downloaded_date = datetime.strptime(self.lastDownloadBillDate_list[user_index], "%m/%d/%Y")

                            # if '{}-{}'.format(account_number, bill_date) not in self.logs:
                            if last_downloaded_date + timedelta(days=28) < datetime.now():
                                print '--- downloading ---'
                                yield self.download_page(print_btn, account_number, bill_date)
                                time.sleep(2)

                            try:
                                self.driver.find_elements_by_xpath('//li[@class="paginate_button next"]')[
                                    0].click()
                            except:
                                all_pages_crawled = True
                        else:
                            all_pages_crawled = True

                change_account_btn = self.driver.find_elements_by_xpath(
                    '//button[@class="btn btn-primary" and contains(text(), "Change Account")]')
                if change_account_btn:
                    change_account_btn[0].click()
                else:
                    self.driver.get('https://secure.pepco.com/Pages/ChangeAccount.aspx')
                time.sleep(3)

                account_index = account_index + 1
                if account_index > len(self.accountOwnerID_list) - 1:
                    all_numbers_option = False

            print('===========All files of your account have been downloaded================')
            # user_index = user_index + 1
            # if user_index > len(self.accountOwnerID_list) - 1:
            #     all_users_option = False
            all_users_option = False
            self.driver.close()

            with open('TEST_EquityMgmt2LLC-account_number REV.csv', 'rb') as csv_read:
                reader = csv.reader(csv_read)
                lines = list(reader)
                for i in range(1, 4):
                    lines[i][2] = '5/2/2019'

            with open('updated_EquityMgmt2LLC-account_number REV.csv', 'w') as csv_write:
                writer = csv.writer(csv_write)
                writer.writerows(lines)

        print('===========All files of all users have been downloaded================')
        self.driver.close()

    def download_page(self, print_btn=None, account_number=None, bill_date=None):

        file_name = '{}_{}.pdf'.format(account_number, bill_date)

        print "===================================="
        print file_name

        if os.path.exists('C:/Users/webguru/Downloads/BillImage.pdf'):
            os.remove('C:/Users/webguru/Downloads/BillImage.pdf')
        if os.path.exists('C:/Users/webguru/Downloads/BillImage (1).pdf'):
            os.remove('C:/Users/webguru/Downloads/BillImage (1).pdf')
        print_btn.click()
        time.sleep(5)

        self.write_logs('{}-{}'.format(account_number, bill_date))

        if os.path.exists('C:/Users/webguru/Downloads/BillImage.pdf'):
            os.rename('C:/Users/webguru/Downloads/BillImage.pdf', 'C:/Users/webguru/Downloads/pepco/' + file_name)
        if os.path.exists('C:/Users/webguru/Downloads/BillImage (1).pdf'):
            os.rename('C:/Users/webguru/Downloads/BillImage (1).pdf', 'C:/Users/webguru/Downloads/pepco/' + file_name)
        time.sleep(5)

        return {
            'file_name': file_name,
            'account_number': account_number,
            'bill_date': bill_date
        }

    def date_to_string(self, d):
        d = d.split('/')
        return ''.join([i.zfill(2) for i in d])

    def write_logs(self, bill_id):
        cwd = os.getcwd().replace("\\", "//").replace('spiders', '')
        with open('{}/scrapy.log'.format(cwd), 'a') as f:
            f.write(bill_id + '\n')
            f.close()
        self.logs.append(bill_id)
