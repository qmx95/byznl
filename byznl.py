from selenium import webdriver
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import random
from selenium.webdriver.chrome.options import Options
import os
import json
import logging

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
        self.fast = config['fast']
        self.znl_list = []

        if type(self.weibo_homepage) is list or type(self.share_num) is list:
            assert type(self.weibo_homepage) == type(self.share_num)
            assert len(self.weibo_homepage) == len(self.share_num)

        self.SCROLL_PAUSE_TIME = 3
        self.driver = self._init_chrome()
        self.FILE_NAME = "znl_weibo"

        count = 0
        if os.path.exists(self.FILE_NAME):
            with open(self.FILE_NAME, 'r') as f:
                for line in f:
                    self.znl_list.append(line.strip())
                    count += 1
        logging.info(f"read {count} urls from {self.FILE_NAME}")


    def _init_chrome(self):
        # open chrome
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=/Users/MengxiaoQian/Library/Application Support/Google/Chrome/Profile 5")  # Path to your chrome profile
        driver = webdriver.Chrome(
            executable_path="/Users/MengxiaoQian/.wdm/drivers/chromedriver/mac64/91.0.4472.19/chromedriver", chrome_options=options)
        logging.info("open chrome successfully!!")
        return driver

    def get_share_groups(self):
        self.driver.get('http://weibo.com')
        time.sleep(5)

        # log in
        while True:
            time.sleep(5)
            logging.info('please log in!!')
            if self.driver.current_url.startswith('https://weibo.com/u/'):
                break
        logging.info('log in successfully!')

        # go to chat page
        chat_url = "https://api.weibo.com/chat/#/chat?"
        self.driver.get(chat_url)
        time.sleep(5)

        # get group name list including palou
        groups = self.driver.find_elements_by_xpath('//span[@class="one-line usrn"]')
        group_name_list = []
        for group in groups:
            if "爬楼" in group.text:
                group_name_list.append(group.text)
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

    def get_znl_weibos(self, given_url, znl_num):
        # open a new tab
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.driver.get(given_url)
        time.sleep(5)

        # show all weibo on this page
        button = self.driver.find_element_by_xpath('//a[contains(text(), "全部") and (@class="S_txt1 " or @class="S_txt1 S_line1")]')
        button.click()
        time.sleep(3)

        logging.info(f"-----------begin to scan weibo {given_url}-------------")

        url_link_list = []
        page_num = 0
        while znl_num > len(url_link_list):
            # scroll down
            self.scroll_down_page()


            # check if next page is available, network latency issue??
            # FIXME: 末页bug，之后再改
            try:
                next_page = self.driver.find_element_by_xpath('//a[@class="page next S_txt1 S_line1"]')
            except:
                continue

            # get all weibos on this page
            weibos = self.driver.find_elements_by_xpath('//div[@class="WB_from S_txt2"]/a')
            for weibo in weibos:
                url_link = weibo.get_attribute("href")
                if url_link.startswith('https://weibo.com') and url_link.endswith('weibotime'):
                    url_link_list.append(url_link)

            logging.info(f"get total {len(url_link_list)} weibos from {page_num+1} pages")

            if znl_num <= len(url_link_list):
                break

            # go to next page
            next_page.click()
            page_num += 1
            time.sleep(2)

        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        time.sleep(1)

        logging.info(f"get {znl_num} weibos from {given_url}")
        logging.info(f"-----------weibo {given_url} scan done-------------")


        return [url for url in reversed(url_link_list[:znl_num])]


    def share_to_group(self):
        BUSY = False
        for group_name in self.group_name_list[:self.group_num]:
            # based on group name get corresponding group list element
            group = self.driver.find_element_by_xpath(
                '//span[contains(text(), "{0}") and @class="one-line usrn"]'.format(group_name))
            group = group.find_element_by_xpath('../../../..')
            group.click()
            time.sleep(10)
            logging.info(f"-------------begin to send weibo in group {group_name}--------------")
            index = 0

            # verify whether this group belongs to BUYUAN groups
            try:
                verification = self.driver.find_element_by_xpath('//*[@title="房纸_的官方认证粉丝群"]')
            except:
                logging.error(group_name + ' not for BOYUAN')
                self.driver.close()
                quit()

            # share weibo to group
            text_box = self.driver.find_element_by_id('webchat-textarea')
            for url in self.znl_list:
                text_box.clear()
                text_box.send_keys(url)
                time.sleep(random.uniform(0, 1)) if self.fast else time.sleep(random.uniform(1, 2))
                text_box.send_keys(Keys.ENTER)
                index += 1
                logging.info(f"{index} weibo sent successfully in {group_name} !!")

                # FIXME: busy逻辑我还没有测试，我的号一直没有busy
                if index % 3 == 0:
                    notice_list = self.driver.find_elements_by_xpath('//span[@class="notice_in"]')
                    for notice in notice_list:
                        if '链接消息太频繁了' in notice.text:
                            BUSY = True
                            break

                if BUSY:
                    logging.error("------------此号已频繁，请注意休息-----------------")
                    with open(self.FILE_NAME, 'w') as f:
                        for url in self.url_list[index:]:
                            f.write(url + '\n')
                    self.driver.close()
                    quit()

            logging.info(f"-------------{group_name} sent {index} weibos done-------------")

    def weibo_share(self):
        self.group_name_list = self.get_share_groups()
        if type(self.weibo_homepage) is list:
            for tmp_page, tmp_num in zip(self.weibo_homepage, self.share_num):
                self.znl_list.extend(self.get_znl_weibos(tmp_page, tmp_num))
        else:
            self.znl_list.extend(self.get_znl_weibos(self.weibo_homepage, self.share_num))
        logging.info(f'total znl num is {len(self.znl_list)}')
        self.share_to_group()
        if os.path.exists(self.FILE_NAME):
            os.remove(self.FILE_NAME)
        self.driver.close()








if __name__ == '__main__':

    with open('config.json', 'r') as f:
        data = json.load(f)

    weibo_share = WeiboShare(data)
    weibo_share.weibo_share()