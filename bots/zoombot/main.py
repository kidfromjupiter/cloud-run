import sys
from os import environ

import requests

from bin.bot import ZoomBot

if __name__ == '__main__':
    try:
        meeting_url = environ.get("MEETING_URL")
        bot_name = environ.get("BOTNAME")
        timeout = int(environ.get("TIMEOUT"))
        bot_id = environ.get("BOT_ID")
        from_id = environ.get("FROM_ID")
        ws_link = environ.get("WS_LINK")
        group_id = environ.get("GROUP_ID")
        bot = ZoomBot(
            ws_link,
            meeting_url,
            bot_name,
            timeout,
            bot_id,
            from_id,
            group_id
        )
        bot.join_meeting()
    except Exception as e:
        print(e)
        BASE_URL = 'https://backend-testing-514385437890.us-central1.run.app'
        USER_ID = environ.get("FROM_ID")
        BOT_ID = environ.get("BOT_ID")
        if not environ.get("GROUP_ID"):
            requests.post(
                f"{BASE_URL}/done/{USER_ID}/{BOT_ID}",
            )
            print("Not in a group. Made a request after it quit")
        else:
            requests.post(
                f"{BASE_URL}/done/group/{USER_ID}/{BOT_ID}",
            )
            print("In a group. Made a request after it quit")

        sys.exit(0)