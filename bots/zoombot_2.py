import logging as lg
import re
from os import environ
from time import sleep
from .botbase import BotBase

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

lg.basicConfig(level=lg.DEBUG, filename="py_log.log", filemode="w")
WAIT_ADMIT_TIME = 120
POLL_RATE = 0.1

class ZoomBot(BotBase):
    def __init__(self, ws_link, meeting_id, botName, timeout, bot_id, to_id):
        super().__init__(ws_link, meeting_id, botName, timeout, bot_id, to_id)

    def join_meeting(self):
        try:
            try:
                meeting_id = re.search(r'(?<=wc/)\d+', self.meeting_id).group()
            except:
                meeting_id = re.search(r'(?<=j/)\d+', self.meeting_id).group()
            password = re.search(r'(?<=pwd=)[^&]*', self.meeting_id).group()

            self.driver.get(f"https://app.zoom.us/wc/{meeting_id}/join?pwd={password}")

            print("in meeting page")
            self.driver.maximize_window()
            try:
                self.driver.implicitly_wait(10)
                self.driver.find_element(By.XPATH, "//button[@id='onetrust-accept-btn-handler']").click()

                self.driver.find_element(By.XPATH, '//button[@id="wc_agree1"]').click()
            except:
                pass

            self.driver.implicitly_wait(60)
            self.driver.find_element(By.ID, 'input-for-name').send_keys(self.bot_name)
            print("input name")

            self.driver.implicitly_wait(10)
            join_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "preview-join-button")]')

            # Click the join button
            sleep(5)
            join_button.click()
            self.last_status = "In wait room or joining"
            print("in wait room or joining")

            # waiting till joined
            # Wait for the SVG with class "SvgShare" to appear
            self.driver.implicitly_wait(WAIT_ADMIT_TIME)
            self.driver.find_element(By.CLASS_NAME, 'SvgShare')
            self.last_status = "Joined meeting"

            # Wait for the element with text "Join Audio by Computer" to appear
            join_audio_button = WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.XPATH, '//*[text()="Join Audio by Computer"]'))
            )
            sleep(2)

            # Click the join audio button
            if join_audio_button.is_enabled() and join_audio_button.is_displayed():
                # Click the join audio button
                join_audio_button.click()

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
            sleep(600)

        except Exception as e:
            print(e)
            elements = self.driver.find_elements(By.CLASS_NAME, 'SvgShare')
            if elements:
                self.driver.save_screenshot(f"error.png")
            self.driver.save_screenshot(f"exit.png")
            page = self.driver.page_source
            with open("page.html", "w") as file:
                file.write(page)
            self.driver.quit()
            self.driver = None


if __name__ == '__main__':
    meeting_url = environ.get("MEETING_URL") 
    bot_name = environ.get("BOTNAME")
    timeout = environ.get("TIMEOUT")
    bot_id = environ.get("BOT_ID") 
    from_id = environ.get("FROM_ID")
    ws_link = environ.get("WS_LINK")
    bot = ZoomBot(
        ws_link,
        meeting_url,
        bot_name,
        timeout,
        bot_id,
        from_id,
    )
    bot.join_meeting()
    
