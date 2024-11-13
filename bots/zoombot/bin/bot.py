import logging as lg
import re
from datetime import datetime
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .botbase import BotBase

lg.basicConfig(level=lg.INFO, filename="/var/log/py.log", filemode="w")
WAIT_ADMIT_TIME = 120
POLL_RATE = 0.5


class ZoomBot(BotBase):
    def __init__(self, ws_link, meeting_url, botName, timeout, bot_id, to_id, group_id, password, webinar):
        lg.info(f"Is a webinar? {webinar}")
        super().__init__(ws_link, meeting_url, botName, timeout, bot_id, to_id, group_id, password, webinar)

    def termination_check(self):
        self.driver.implicitly_wait(0.2)
        meeting_ended: list = self.driver.find_elements(By.XPATH, '//div[@aria-label="Meeting is end now"]')
        removed: list = self.driver.find_elements(By.XPATH, '//div[@aria-label="You have been removed"]')
        if meeting_ended or removed:
            self.exit_func()
            raise Exception("Meeting ended")

    def __pw_in_link_login_flow(self, meeting_id: str, password: str):
        self.driver.get(f"https://app.zoom.us/wc/{meeting_id}/join?pwd={password}")

        lg.info("in meeting page")
        self.driver.maximize_window()
        try:
            self.driver.implicitly_wait(10)
            self.driver.find_element(By.XPATH, "//button[@id='onetrust-accept-btn-handler']").click()

            self.driver.find_element(By.XPATH, '//button[@id="wc_agree1"]').click()
        except:
            pass

        self.driver.implicitly_wait(60)
        self.driver.find_element(By.ID, 'input-for-name').send_keys(self.bot_name)
        lg.info("input name")

        self.driver.implicitly_wait(0)
        try:
            email_field = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="input-for-email"]'))
            )
            email_field.send_keys("test@test.mail")
        except:
            pass

        self.driver.implicitly_wait(10)
        join_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "preview-join-button")]')

        # Click the join button
        sleep(5)
        join_button.click()
        self.last_status = "In wait room or joining"
        lg.info("in wait room or joining")

    def __in_meeting_flow(self):
        # waiting till joined
        # Wait for the SVG with class "SvgShare" to appear
        self.driver.implicitly_wait(WAIT_ADMIT_TIME)
        if not self.webinar:
            self.driver.find_element(By.CLASS_NAME, 'SvgShare')
            self.last_status = "Joined meeting"
            lg.info("In meeting")

            self.started_time = datetime.now()
        else:
            self.driver.find_element(By.XPATH, "//span[text()='Leave']")
            self.last_status = "Joined meeting"
            lg.info("In meeting")

            self.started_time = datetime.now()

        if not self.webinar:
            lg.info("Not a webinar. Joining audio")
            # Wait for the element with text "Join Audio by Computer" to appear
            join_audio_button = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.XPATH, '//*[text()="Join Audio by Computer"]'))
            )
            sleep(2)

            # Click the join audio button
            if join_audio_button.is_enabled() and join_audio_button.is_displayed():
                # Click the join audio button
                join_audio_button.click()
                lg.info("Clicked join audio button")

            sleep(2)

            # stopping incoming video
            more_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'moreButton'))
            )
            more_button.click()
            sleep(2)
            more_button.click()

            sleep(3)
            stop_video_button = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//a[@aria-label="Stop Incoming Video"]'))
            )

            # Click the stop video button
            stop_video_button.click()

    def __pw_separate_flow(self, password: str, meeting_id: str):
        self.driver.get(f"https://app.zoom.us/wc/{meeting_id}/join")

        lg.info("in meeting page")
        self.driver.maximize_window()
        try:
            self.driver.implicitly_wait(10)
            self.driver.find_element(By.XPATH, "//button[@id='onetrust-accept-btn-handler']").click()

            self.driver.find_element(By.XPATH, '//button[@id="wc_agree1"]').click()
        except:
            pass

        self.driver.implicitly_wait(60)
        self.driver.find_element(By.ID, 'input-for-name').send_keys(self.bot_name)
        lg.info("input name")

        self.driver.implicitly_wait(0)
        try:
            email_field = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//input[@id="input-for-email"]'))
            )
            email_field.send_keys("test@test.mail")
        except:
            pass

        self.driver.implicitly_wait(10)
        self.driver.find_element(By.ID, 'input-for-pwd').send_keys(password)

        self.driver.implicitly_wait(10)
        join_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "preview-join-button")]')

        # Click the join button
        sleep(5)
        join_button.click()
        self.last_status = "In wait room or joining"
        lg.info("in wait room or joining")

    def join_meeting_and_wait(self):
        try:
            try:
                meeting_id = re.search(r'(?<=wc/)\d+', self.meeting_url).group()
            except:
                meeting_id = re.search(r'(?<=j/)\d+', self.meeting_url).group()

            if self.password:
                password = self.password
                self.__pw_separate_flow(password, meeting_id)
            else:
                password = re.search(r'(?<=pwd=)[^&]*', self.meeting_url).group()
                self.__pw_in_link_login_flow(meeting_id, password)

            self.__in_meeting_flow()

            # main event loop
            while True:
                now = datetime.now()
                time_difference = now - self.started_time
                if time_difference.total_seconds() > self.timeout:
                    lg.info("quitting, time diff:", time_difference.total_seconds())
                    raise Exception("Timeout Reached")
                self.termination_check()
                sleep(POLL_RATE)

        except Exception as e:
            lg.error(e)
            raise Exception("Internal bot error")
