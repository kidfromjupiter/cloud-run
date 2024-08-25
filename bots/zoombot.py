# import required modules
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from time import sleep

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


WAIT_ADMIT_TIME = 120
POLL_RATE = 0.3
GSTREAMER_PATH = Path(__file__).resolve().parent / "../utils/webrtc_gstreamer.py"


class ZoomMeet(BotBase):
    def __init__(self, meeting_link, xvfb_display, ws_link, meeting_id, zoom_email="", zoom_password=""):
        self.zoom_email = zoom_email
        self.zoom_password = zoom_password
        self.botname = "BotAssistant"
        self.meeting_link = meeting_link
        self.transcriptions = []
        self.last_transcription_sent = datetime.now()
        self.prev_subject = ""
        super().__init__(ws_link, xvfb_display, meeting_id)

    def join_meeting(self):
        print(self.xvfb_display)
        print(self.meeting_link)
        try:
            meeting_id = re.search(r'(?<=wc/)\d+', self.meeting_link).group()
        except:
            meeting_id = re.search(r'(?<=j/)\d+', self.meeting_link).group()
        password = re.search(r'(?<=pwd=)[^&]*', self.meeting_link).group()

        self.driver.get(f"https://app.zoom.us/wc/{meeting_id}/join?pwd={password}")

        self.driver.maximize_window()

        try: # region depenedent
            self.driver.implicitly_wait(10)
            self.driver.find_element(By.XPATH, "//button[@id='onetrust-accept-btn-handler']").click()

            self.driver.find_element(By.XPATH, '//button[@id="wc_agree1"]').click()
        except: # this section is region depended. In EU, this is required
            pass
        #

        self.driver.implicitly_wait(60)
        self.driver.find_element(By.ID, 'input-for-name').send_keys(self.botname)

        self.driver.implicitly_wait(10)
        join_button = self.driver.find_element(By.XPATH, '//button[contains(@class, "preview-join-button")]')

        # Click the join button
        sleep(5)
        join_button.click()

        # waiting till joined
        # Wait for the SVG with class "SvgShare" to appear
        self.driver.implicitly_wait(WAIT_ADMIT_TIME)
        self.driver.find_element(By.CLASS_NAME, 'SvgShare')

        # Wait for the element with text "Join Audio by Computer" to appear
        join_audio_button = WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[text()="Join Audio by Computer"]'))
        )
        sleep(5)

        # Click the join audio button
        if join_audio_button.is_enabled() and join_audio_button.is_displayed():
            # Click the join audio button
            join_audio_button.click()

        sleep(5)
        more_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, 'moreButton'))
        )

        # Click the more button twice. zoom issue
        more_button.click()
        sleep(2)
        more_button.click()

        self.driver.find_element(By.XPATH, '//a[@aria-label="Settings"]').click()

        meeting_controls = self.driver.find_element(By.XPATH, '//div[text()="Always show meeting controls"]/..')
        if meeting_controls.get_attribute("aria-checked") != "true":
            meeting_controls.click()

        self.driver.find_element(By.XPATH, '//button[contains(@class,"zm-btn settings-dialog__close")]').click()

        # enable close captions
        more_button = self.driver.find_element(By.ID, 'moreButton')
        # Click the more button twice. zoom issue
        more_button.click()
        sleep(2)
        more_button.click()



if __name__ == "__main__":
    try:
        args = sys.argv[1:]
        zoom = ZoomMeet(args[0],  # meeting url
                        args[1],  # xvfb numner 
                        args[2],  # ws_link 
                        args[3],  # meeting_id
                        )
        print("ran")
        thread = threading.Thread(target=zoom.setup_ws, daemon=True)
        thread.start()
        zoom.join_meeting()

    except Exception as e:
        raise e

    # Main event loop for zoombot
