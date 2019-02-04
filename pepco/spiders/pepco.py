from __future__ import division, absolute_import, unicode_literals
from scrapy import Spider
from selenium import webdriver
from time import sleep
import os
import csv


class PepcoSpider(Spider):
    name = "pepco"
    start_urls = [
        'https://secure.pepco.com/Pages/Login.aspx'
    ]
    passed_vals = []

    def __init__(self, download_directory=None, *args, **kwargs):
        super(PepcoSpider, self).__init__(*args, **kwargs)

        with open('Pepco Credentials.csv', 'rb') as csvfile:
            reader = csv.reader(csvfile)
            self.password_list = []
            self.username_list = []
            for row_index, row in enumerate(reader):
                if row_index != 0:
                    self.username_list.append(row[0])
                    self.password_list.append(row[1])

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
                sleep(10)
                continue

    def parse(self, response):

        all_users_option = True
        user_index = 0
        account_page_num = 0
        account_index = 0
        while all_users_option:

            if user_index == 0:
                self.driver.get(response.url)
            if self.driver.current_url != 'https://secure.pepco.com/Pages/Login.aspx':
                self.driver.get('https://secure.pepco.com/Pages/Login.aspx')

            self.login(user_index)
            sleep(5)
            all_accounts_all_pages_finished = False
            account_page_num = 1
            while not all_accounts_all_pages_finished:
                try:
                    if self.driver.current_url != 'https://secure.pepco.com/Pages/ChangeAccount.aspx':
                        self.driver.get('https://secure.pepco.com/Pages/ChangeAccount.aspx')
                    sleep(5)
                    all_accounts_one_page_finished = False
                    account_index = 0

                    while not all_accounts_one_page_finished:

                        if self.driver.current_url != 'https://secure.pepco.com/Pages/ChangeAccount.aspx':
                            self.driver.get('https://secure.pepco.com/Pages/ChangeAccount.aspx')
                            sleep(5)

                        index = 1
                        while index < account_page_num:
                            self.driver.find_elements_by_xpath('//li[@class="paginate_button next"]')[0].click()
                            index += 1
                        sleep(5)

                        account_selected = True
                        account_rows = self.driver.find_elements_by_xpath('//table[@id="changeAccountDT1"]//tbody//tr')
                        while account_selected:
                            try:
                                account_rows[account_index].find_elements_by_xpath(
                                    './/td[@class="action-cell ng-scope"]//button')[1].click()
                                sleep(5)
                                account_index = account_index + 1

                                if self.driver.current_url != 'https://secure.pepco.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx':
                                    self.driver.get(
                                        'https://secure.pepco.com/MyAccount/MyBillUsage/Pages/Secure/AccountHistory.aspx')
                                sleep(5)

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

                                sleep(5)

                                account_number = self.driver.find_elements_by_xpath(
                                    '//p[contains(text(), "Account")]//span[@class="exc-data-neutral ng-binding"]'
                                )
                                account_number = account_number[0].text if account_number else None

                                all_pages_crawled = False
                                while not all_pages_crawled:
                                    rows = self.driver.find_elements_by_xpath('//table//tbody//tr')
                                    row = rows[0]

                                    # for row in rows:
                                    bill_date_info = row.find_elements_by_xpath('.//td')[0].text.split('/')
                                    bill_date = bill_date_info[2] + bill_date_info[0] + bill_date_info[1]
                                    print_btn = row.find_elements_by_xpath(
                                        './/td//button[contains(text(), "View")]')[0]
                                    if '{}-{}'.format(account_number, bill_date) not in self.logs:
                                        print '--- downloading ---'
                                        yield self.download_page(print_btn, account_number, bill_date)

                                    print('======moving to other account=======')

                                    print account_index
                                    print account_page_num
                                    print user_index

                                    try:
                                        self.driver.find_elements_by_xpath('//li[@class="paginate_button next"]')[
                                            0].click()

                                    except:
                                        all_pages_crawled = True

                                self.driver.find_elements_by_xpath(
                                    '//button[@class="btn btn-primary" and contains(text(), "Change Account")]')[
                                    0].click()
                            except:
                                account_selected = False

                            # if account_index > len(account_rows) - 1:
                            if account_index > 2:
                                all_accounts_one_page_finished = True

                    print("=====move to next account page=====")
                    print account_index
                    print account_page_num
                    print user_index

                    account_page_num += 1

                    sleep(5)
                    logout_button = self.driver.find_element_by_xpath(
                        '//button[contains(text(), "Sign Out")]'
                    )
                    logout_button.click()
                    sleep(5)
                    if self.driver.current_url != 'https://secure.pepco.com/Pages/Login.aspx':
                        self.driver.get('https://secure.pepco.com/Pages/Login.aspx')
                    sleep(5)
                    self.login(user_index)

                    if account_page_num > 24:
                        all_accounts_all_pages_finished = True
                except:
                    # sleep(2)
                    all_accounts_all_pages_finished = True

            print('===========All files of your account have been downloaded============')

            user_index = user_index + 1
            # if user_index > len(self.username_list) - 1:
            if user_index > 1:
                all_users_option = False

        print('===========All files of all users have been downloaded================')
        print account_index
        print account_page_num
        print user_index
        # self.driver.close()

    def download_page(self, print_btn=None, account_number=None, bill_date=None):

        file_name = '{}_{}.pdf'.format(account_number, bill_date)

        print "===================================="
        print file_name

        if os.path.exists('C:/Users/webguru/Downloads/BillImage.pdf'):
            os.remove('C:/Users/webguru/Downloads/BillImage.pdf')
        if os.path.exists('C:/Users/webguru/Downloads/BillImage (1).pdf'):
            os.remove('C:/Users/webguru/Downloads/BillImage (1).pdf')
        print_btn.click()
        sleep(5)
        self.write_logs('{}-{}'.format(account_number, bill_date))

        if os.path.exists('C:/Users/webguru/Downloads/BillImage.pdf'):
            os.rename('C:/Users/webguru/Downloads/BillImage.pdf', 'C:/Users/webguru/Downloads/' + file_name)
        if os.path.exists('C:/Users/webguru/Downloads/BillImage (1).pdf'):
            os.rename('C:/Users/webguru/Downloads/BillImage (1).pdf', 'C:/Users/webguru/Downloads/' + file_name)
        sleep(5)

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
