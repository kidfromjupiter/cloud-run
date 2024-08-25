import json
import sys
from uuid import uuid4

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import threading

from selenium.webdriver.chrome.webdriver import WebDriver

from .ws_manager import WebsocketConnection


class BotBase:
    def __init__(self, ws_link, meeting_id, bot_name, timeout, bot_id, to_id):
        self.timer = None
        self.timer_running = False
        self.ws_link = ws_link
        self.from_id = bot_id
        self.to_id= to_id
        self.websocket = WebsocketConnection(self.ws_link, self.from_id, self.to_id)
        self.participant_list = []
        self.meeting_id = meeting_id
        self.timer = None
        self.bot_name = bot_name
        self.timer_running = False
        self.timeout = timeout
        self.last_status = "Bot started"
        # Create Chrome instance

        opt = Options()
        opt.add_argument('--disable-blink-features=AutomationControlled')
        opt.add_argument('--no-sandbox')
        opt.add_argument('--start-maximized')

        opt.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 0,
            "profile.default_content_setting_values.notifications": 1
        })
        self.driver: WebDriver = webdriver.Chrome(options=opt)
        self.driver.maximize_window()

    def start_timer(self, interval, func):
        # Cancel any existing timer before starting a new one
        if self.timer_running:
            self.cancel_timer()

        print("Starting timer...")
        self.timer = threading.Timer(interval, func)
        self.timer.start()
        self.timer_running = True

    def cancel_timer(self):
        if self.timer is not None:
            print("Cancelling timer...")
            self.timer.cancel()
        self.timer_running = False

    def is_timer_running(self):
        return self.timer_running

    def setup_ws(self):
        self.websocket.connect()
        # self._loop() # Don't need this for now

    def _loop(self):
        while self.websocket.conn:
            message = self.websocket.conn.recv()
            msg: dict = json.loads(message)
            if "kill" in msg.keys():
                self.exit_func()
            if "getStatus" in msg.keys():
                self.websocket.send_status(self.last_status,self.bot_name,self.meeting_id) 


    def exit_func(self):
        self.driver.quit()
        sys.exit(0)

    def send_status(self):
        pass
