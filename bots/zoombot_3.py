import logging as lg
import re
from datetime import datetime
from multiprocessing import Queue
from time import sleep

from channels.layers import get_channel_layer
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .aux import Message, send_message, send_status
from .zoombot_aux import mute, muteall, mutebuthost, removespotlights, request_all_to_unmute, request_cameras, spotlight

lg.basicConfig(level=lg.DEBUG, filename="py_log.log", filemode="w")
WAIT_ADMIT_TIME = 120
NAME = "Meetingheld.in"
MESSAGE_POLL_RATE = 0.1


def check_ended(driver):
    meeting_ended: list = driver.find_elements(By.XPATH, '//div[@aria-label="Meeting is end now"]')
    removed: list = driver.find_elements(By.XPATH, '//div[@aria-label="You have been removed"]')
    if meeting_ended or removed:
        driver.quit()
        driver = None
        raise Exception("Meeting ended")


def run_zoombot(meeting_link, userid, timeout, q: Queue):
    startTime = datetime.now()
    channel_layer = get_channel_layer()
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    if not settings.DEV:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--user-data-dir=chrome-data")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox")

    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(chrome_options)
    send_status(userid, "Bot started", channel_layer)
    # retrying for 3 times if theres an error
    try:
        try:
            meeting_id = re.search(r'(?<=wc/)\d+', meeting_link).group()
        except:
            meeting_id = re.search(r'(?<=j/)\d+', meeting_link).group()
        password = re.search(r'(?<=pwd=)[^&]*', meeting_link).group()

        driver.get(f"https://app.zoom.us/wc/{meeting_id}/join?pwd={password}")

        if not settings.DEV:
            accept_cookies = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))
            )
            accept_cookies.click()

            agree = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//button[@id="wc_agree1"]'))
            )
            agree.click()

        name_input = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, 'input-for-name'))
        )

        # Enter the name "Socialstream"
        name_input.send_keys(NAME)

        join_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[contains(@class, "preview-join-button")]'))
        )
        sleep(5)
        # Click the join button
        join_button.click()
        send_status(userid, "If wait room is enabled, admit bot now", channel_layer)

        # waiting till joined
        # Wait for the SVG with class "SvgShare" to appear
        svg_share = WebDriverWait(driver, WAIT_ADMIT_TIME).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'SvgShare'))
        )

        # Wait for the element with text "Join Audio by Computer" to appear
        join_audio_button = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[text()="Join Audio by Computer"]'))
        )
        send_status(userid, "Admitted to meeting", channel_layer)
        sleep(5)

        # Click the join audio button
        if join_audio_button.is_enabled() and join_audio_button.is_displayed():
            # Click the join audio button
            join_audio_button.click()

        sleep(5)
        more_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'moreButton'))
        )

        # Click the more button twice. zoom issue
        more_button.click()
        sleep(2)
        more_button.click()

        sleep(3)
        stop_video_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@aria-label="Stop Incoming Video"]'))
        )

        # Click the stop video button
        stop_video_button.click()

        # Click the more button twice. zoom issue
        more_button.click()
        sleep(2)
        more_button.click()

        settings_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@aria-label="Settings"]'))
        )
        settings_button.click()

        meeting_controls = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[text()="Always show meeting controls"]/..'))
        )
        if meeting_controls.get_attribute("aria-checked") != "true":
            meeting_controls.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//button[contains(@class,"zm-btn settings-dialog__close")]'))
        ).click()

        # Wait for the div with class "footer-chat-button" to appear
        chat_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@feature-type="chat"]'))
        )
        # Click the SVG
        sleep(2)
        chat_button.click()
        sleep(1)
        chat_button.click()

        participant_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@feature-type="participant"]'))
        )
        lg.info("got participant button")
        participant_button.click()
        sleep(5)
        participant_button.click()
        # Wait for the chat container with class "chat-container__chat-list" to appear
        chat_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "chat-container__chat-list")]'))
        )
        sent_id_list: list[str] = []
        spotlights: list[str] = []
        author = ""
        avatar = ""
        while True:
            if not q.empty():
                command = q.get()
                # ! is removed in consumers.py
                command, *args = command.split("#")
                print(args)
                match command:
                    case "spotlight":

                        print("spotlight")
                        spotlights = [*args, *spotlights]
                        spotlight(driver, lg, userid, channel_layer, *args)
                    case "unspot":
                        removespotlights(driver, lg, userid, channel_layer)
                    case "mutebuthost":
                        mutebuthost(driver, lg, userid, channel_layer)
                    case "unmuteall":
                        request_all_to_unmute(driver, lg, userid, channel_layer)
                    case "mute":
                        mute(driver, lg, userid, channel_layer, *args)
                    case "muteall":
                        muteall(driver, lg, userid, channel_layer)
                    case "cameras":
                        request_cameras(driver, args, lg, userid, channel_layer)
            check_ended(driver)
            now = datetime.now()
            time_difference = now - startTime
            if time_difference.total_seconds() > timeout * 60 * 60:
                raise Exception("Timeout Reached")

            send_status(userid, "Listening for messages", channel_layer)
            chat_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "chat-container__chat-list")]'))
            )
            messages = chat_container.find_elements(By.XPATH, ".//div[@class='chat-item-container']")
            if len(messages) > 0:
                message = messages[-1]
                driver.execute_script("arguments[0].scrollIntoView();", message)
                try:
                    message.find_element(By.XPATH, ".//div[contains(@class, 'info-header')]")
                    try:
                        # avatar image isnt always available. 
                        avatar = message.find_element(By.XPATH,
                                                      ".//img[@class='chat-item__user-avatar']").get_attribute("src")
                    except:
                        pass
                    finally:
                        author = message.find_element(By.XPATH, ".//span[contains(@class,'chat-item__sender')]").text
                except:
                    pass
                finally:
                    msg_content = message.find_element(By.XPATH, ".//div[@class='new-chat-message__content']").text
                    content_id = message.find_element(By.XPATH,
                                                      ".//div[@class='new-chat-message__content']/div/div").get_attribute(
                        "id")
                    new_msg = Message("zoom", author, msg_content, avatar, content_id)
                    if new_msg.contentId not in sent_id_list:
                        sent_id_list.append(new_msg.contentId)
                        # send to server
                        send_message(userid, new_msg.stringify(), channel_layer)
                        print(f"New message from {new_msg.chatname} in Zoom chat: {new_msg.chatmessage}")
                sleep(MESSAGE_POLL_RATE)
    except Exception as e:
        print(e)
        send_status(userid, "Bot ended", channel_layer)
        elements = driver.find_elements(By.CLASS_NAME, 'SvgShare')
        if elements:
            driver.save_screenshot(f"error.png")
        driver.save_screenshot(f"exit.png")
        page = driver.page_source
        url = driver.current_url
        with open("page.html", "w") as file:
            file.write(page)
        with open("url.txt", "w") as file:
            file.write(url)

        driver.quit()
        driver = None
