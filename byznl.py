import datetime
import json
import logging
import os
import platform
import random
import sys
import time
import pickle

import regex as re
import selenium.webdriver as webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(filename="share_weibo_log",
                    filemode='w',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)


class WeiboShare(object):
    def __init__(self, config: dict):
        self.weibo_homepage = config['weibo_home_page']
        self.share_num = config['znl_num']
        self.group_num = config['group_num']
        self.files = config['file']
        self.fast = config['fast']
        self.share_start_time = config['start_time']
        self.znl_list = []
        self.group_name_list = []

        self._config_check()

        self.SCROLL_PAUSE_TIME = 2
        self.driver = WeiboShare._init_chrome()
        self.FILE_NAME = "znl_weibo"

        for file_name in self.files:
            count = 0
            if os.path.exists(file_name):
                with open(file_name, encoding="utf8", errors='ignore') as f:
                    for line in f:
                        self.znl_list.append(line.strip())
                        count += 1
            logging.info(f"read {count} urls from {file_name}")

    def _config_check(self):
        assert type(self.weibo_homepage) is list
        assert type(self.share_num) is list
        assert type(self.files) is list
        assert type(self.share_start_time) is list

        # check
        if len(self.weibo_homepage) != 0:
            if len(self.share_start_time) != 0 and len(self.share_num) != 0:
                logging.error("Please only fill in one of [znl_num] or [start_time]")
                quit()
            if (len(self.weibo_homepage) != len(self.share_num)) and (
                    len(self.weibo_homepage) != len(self.share_start_time)):
                logging.error("The number of [weibo_home_page] is different with the number of [znl_num]/[start_time]")
                quit()

        # set start_time/share_num
        if len(self.weibo_homepage) != 0:
            if len(self.share_start_time) == 0:
                self.share_start_time = ["2021-06-01 00:00"] * len(self.weibo_homepage)
            if len(self.share_num) == 0:
                self.share_num = [sys.maxsize] * len(self.weibo_homepage)

        self.share_start_time = [datetime.datetime.strptime(tmp_time, '%Y-%m-%d %H:%M') for tmp_time in
                                 self.share_start_time]

    def wait_element_to_present(self, delay, element):
        try:
            WebDriverWait(self.driver, delay).until(
                EC.presence_of_element_located(element))
        except TimeoutException:
            logging.exception('Failed to wait element within ' + str(delay) + 's')
            self.driver.save_screenshot(str(time.time()) + '.png')
            self.driver.close()
            sys.exit(1)

    @staticmethod
    def resource_path(relative_path: str) -> str:
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(__file__)

        return os.path.join(base_path, relative_path)

    @staticmethod
    def _init_chrome():
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        # change windows size if too large
        options.add_argument('--window-size=1280,720')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        # to disable dumbass notification
        options.add_experimental_option('prefs',
                                        {'profile.default_content_setting_values.notifications': 2
                                         })

        if platform.system() == 'Windows':
            logging.info('Running on Windows')
            return webdriver.Chrome(WeiboShare.resource_path('chromedriver.exe'), chrome_options=options)

        logging.info('Running on Mac / *nix')
        return webdriver.Chrome(WeiboShare.resource_path('chromedriver'), chrome_options=options)

    def get_share_groups(self):
        self.driver.get('http://weibo.com')

        # must add cookies after access the website, or else encounter invalid doamin execption
        try:
            # add cookies
            cookies = pickle.load(open('cookies.pkl', 'rb'))
            for cookie in cookies:
                self.driver.add_cookie(cookie)
        except FileNotFoundError:
            logging.error('No cookie found, need to re-login')

        self.driver.get('https://weibo.com/')  # access Weibo

        # log in
        # Rely on UI change intead of URL, seem not mandatory to wait forever as well
        self.wait_element_to_present(300, (By.ID, 'v6_pl_rightmod_myinfo'))
        logging.info('log in successfully!')

        # go to chat page
        chat_url = "https://api.weibo.com/chat/#/chat?"
        self.driver.get(chat_url)
        time.sleep(5)

        # get group name list including palou
        groups = self.driver.find_elements_by_xpath('//span[@class="one-line usrn"]')
        group_name_list = []
        regex_pattern = "伯远爬楼\d+群\s+\d\.\d+解散"
        for group in groups:
            if re.fullmatch(regex_pattern, group.text.strip()):
                group_name_list.append(group.text)
        logging.info(f'available groups {group_name_list}')
        return group_name_list

    def scroll_down_page(self):
        # Get scroll height
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")

        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")

            # Wait to load page
            time.sleep(self.SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def get_znl_weibos(self, given_url, znl_num, start_time):
        # open a new tab
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.driver.get(given_url)
        time.sleep(10)

        # show all weibo on this page
        button = self.driver.find_element_by_xpath(
            '//a[contains(text(), "全部") and (@class="S_txt1 " or @class="S_txt1 S_line1")]')
        button.click()
        time.sleep(3)

        logging.info(f"-----------begin to scan weibo {given_url}-------------")

        url_link_list = []
        page_num, full_flag = 0, False
        while True:
            # scroll down
            self.scroll_down_page()

            # check if next page is available, network latency issue??
            # FIXME: 末页bug，之后再改
            try:
                next_page = self.driver.find_element_by_xpath('//a[@class="page next S_txt1 S_line1"]')
            except:
                continue

            # get all weibos on this page
            weibos = self.driver.find_elements_by_xpath('//div[@class="WB_detail"]/div[@class="WB_from S_txt2"]/a')
            for weibo in weibos:
                weibo_time = weibo.get_attribute("title").strip()
                if weibo_time == "":
                    continue
                weibo_time = datetime.datetime.strptime(weibo_time, '%Y-%m-%d %H:%M')
                if (start_time > weibo_time and len(url_link_list) != 0) or znl_num <= len(url_link_list):
                    full_flag = True
                    break
                url_link = weibo.get_attribute("href")
                if url_link.startswith('https://weibo.com') and url_link.endswith('weibotime'):
                    url_link_list.append(url_link)

            logging.info(f"get total {len(url_link_list)} weibos from {page_num + 1} pages")

            if full_flag:
                break

            # go to next page
            next_page.click()
            page_num += 1
            time.sleep(2)

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(1)

        logging.info(f"get {len(url_link_list)} weibos from {given_url}")
        logging.info(f"-----------weibo {given_url} scan done-------------")

        with open(given_url[20:30], 'w') as f:
            for url in url_link_list:
                f.write(url + '\n')
        return [url for url in reversed(url_link_list)]

    def share_to_group(self):
        busy = False
        for group_name in self.group_name_list[:self.group_num]:
            # based on group name get corresponding group list element
            group = self.driver.find_element_by_xpath(
                '//span[contains(text(), "{0}") and @class="one-line usrn"]'.format(group_name))
            group = group.find_element_by_xpath('../../../..')
            group.click()
            time.sleep(15)
            logging.info(f"-------------begin to send weibo in group {group_name}--------------")
            index = 0

            # verify whether this group belongs to BUYUAN groups
            # FIXME: weired sometimes the title doesn't show up, you can comment this part
            # try:
            #     verification = self.driver.find_element_by_xpath('//*[@title="房纸_的官方认证粉丝群"]')
            # except:
            #     logging.error(group_name + ' not for BOYUAN')
            #     continue

            # share weibo to group
            text_box = self.driver.find_element_by_id('webchat-textarea')
            for url in self.znl_list:
                text_box.clear()
                text_box.send_keys(url)
                time.sleep(random.uniform(0, 1)) if self.fast else time.sleep(random.uniform(1, 2))
                text_box.send_keys(Keys.ENTER)
                index += 1
                logging.info(f"{index} weibo sent successfully in {group_name} !!")

                if index % 3 == 0:
                    notice_list = self.driver.find_elements_by_xpath('//span[@class="notice_in"]')
                    for notice in notice_list:
                        if '链接消息太频繁了' in notice.text:
                            busy = True
                            break

                if busy:
                    logging.error("------------The limit of messages has been reached, please try again later-----------------")
                    with open(self.FILE_NAME, 'w') as f:
                        for url in self.znl_list[index:]:
                            f.write(url + '\n')
                    self.driver.close()
                    quit()

            logging.info(f"-------------{group_name} sent {index} weibos done-------------")

    def weibo_share(self):
        try:
            self.group_name_list = self.get_share_groups()
            for tmp_page, tmp_num, tmp_start_time in zip(self.weibo_homepage, self.share_num, self.share_start_time):
                self.znl_list.extend(self.get_znl_weibos(tmp_page, tmp_num, tmp_start_time))
            logging.info(f'total znl num is {len(self.znl_list)}')
            self.share_to_group()
            if os.path.exists(self.FILE_NAME):
                os.remove(self.FILE_NAME)

            pickle.dump(self.driver.get_cookies(), open('cookies.pkl', 'wb'))  # save cookies
            self.driver.close()
        except Exception as e:
            self.driver.save_screenshot(str(time.time()) + '.png')
            self.driver.close()
            logging.error(str(e))
            sys.exit()


if __name__ == '__main__':
    try:
        with open('config.json', 'r') as f:
            data = json.load(f)

        weibo_share = WeiboShare(data)
        weibo_share.weibo_share()
    except Exception as e:
        logging.error(str(e))
        sys.exit()


