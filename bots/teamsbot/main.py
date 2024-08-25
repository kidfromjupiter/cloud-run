from os import environ
from bin.bot import ZoomBot

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
