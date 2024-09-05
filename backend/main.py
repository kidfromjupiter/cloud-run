import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from os import environ

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import BaseModel, UUID4
from supabase import AClient, acreate_client

from utils.aiohttp_singleton import HttpClient

load_dotenv(".env")

http_client = HttpClient()
supabase_client: AClient = None
SUPABASE_SERVICE_KEY = environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = environ.get("SUPABASE_ANON_KEY")
SUPABASE_URL = environ.get("SUPABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    http_client.start()
    global supabase_client
    supabase_client = await acreate_client(supabase_url=SUPABASE_URL, supabase_key=SUPABASE_SERVICE_KEY)
    yield


app = FastAPI(lifespan=lifespan)
metadataUrl = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
zoombotTestingStartUrl = "https://run.googleapis.com/v2/projects/woven-arcadia-432212-a6/locations/us-central1/jobs/zoombot-testing:run"


class MeetingRequest(BaseModel):
    meetingUrl: str
    timeout: int
    botName: str
    botId: str
    fromId: str
    wsLink: str
    userId: str


class BatchMeetingRequest(BaseModel):
    meetingUrl: str
    timeout: int
    botName: str
    botId: str
    fromId: str
    wsLink: str
    numberOfBots: int
    userId: str


def create_payload(request: MeetingRequest | BatchMeetingRequest, bot_id: str, group_id: str | None = None) -> dict:
    return {
        'overrides': {
            "containerOverrides": [
                {
                    "env": [
                        {"name": "MEETING_URL", "value": request.meetingUrl},
                        {"name": "BOTNAME", "value": request.botName},
                        {"name": "TIMEOUT", "value": str(request.timeout)},
                        {"name": "BOT_ID", "value": bot_id},
                        {"name": "WS_LINK", "value": request.wsLink},
                        {"name": "FROM_ID", "value": request.fromId},
                        {"name": "GROUP_ID", "value": group_id},
                    ]
                }
            ]
        }
    }


@app.get("/", tags=["root"])
async def root():
    return {"message": "Hello World"}


@app.post("/done/{user_id}/{bot_id}")
async def done(user_id: str, bot_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    (__, bot_data_list), _ = await supabase_client.table("bots").select("created_at, id").eq("id",
                                                                                             f'{bot_id}').execute()
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{user_id}').execute()
    # calculating leftover credits
    credit = profile_data_list[0]["credits"]
    started_time = datetime.fromisoformat(bot_data_list[0]["created_at"])
    time_now = datetime.now(timezone.utc)
    delta = time_now - started_time
    used_creds = delta.seconds // 60

    credit = max(0, credit - used_creds)

    updated_credit_data, _ = await supabase_client.table("profiles").update({"credits": credit}).eq("user_id",
                                                                                                    f"{user_id}").execute()
    updated_bot_data, _ = await (supabase_client.table("bots").update({"completed": True})
                                 .eq("id", f"{bot_id}")
                                 .eq("user_id", f"{user_id}")
                                 .execute())
    return {
        'botData': updated_bot_data[1][0],
        'profileData': updated_credit_data[1][0],
    }


@app.post("/done/group/{user_id}/{group_id}")
async def done_group(user_id: str, group_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    (__, bot_group_data_list), _ = await supabase_client.table("botgroups").select("created_at, id, alive").eq("id",
                                                                                                               f'{group_id}').execute()
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{user_id}').execute()
    # calculating leftover credits
    credit = profile_data_list[0]["credits"]
    started_time = datetime.fromisoformat(bot_group_data_list[0]["created_at"])
    time_now = datetime.now(timezone.utc)
    delta = time_now - started_time
    used_creds = delta.seconds // 60

    credit = max(0, credit - used_creds)

    updated_alive_count = int(bot_group_data_list[0]["alive"]) - 1
    updated_credit_data, _ = await supabase_client.table("profiles").update({"credits": credit}).eq("user_id",
                                                                                                    f"{user_id}").execute()
    updated_botgroup_data, _ = await supabase_client.table("botgroups").update(
        {"alive": updated_alive_count}).eq("id",
                                           f"{group_id}").execute()

    return {
        'botData': updated_botgroup_data[1][0],
        'profileData': updated_credit_data[1][0],
    }


@app.post("/test/batch/zoom")
async def launch_batch_zoombot(request: BatchMeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    bot_id = str(uuid.uuid4())
    payload = create_payload(request, bot_id)

    # get credits and see if this bot group is runnable
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{request.userId}').execute()

    total_credits_for_botgroup = request.timeout * request.numberOfBots // 60  # timeout is specified in seconds
    if profile_data_list[0]["credits"] < total_credits_for_botgroup:
        return {"status": "insufficient_credits"}

    # get cloud run access token
    r = await http_client.post(
        metadataUrl,
        headers={
            "Metadata-Flavor": "Google"
        }
    )
    json = await r.json()
    access_token = json['access_token']

    # create entry in bot groups table
    await supabase_client.schema("public").table('botgroups').insert({
        "meeting_url": request.meetingUrl,
        "timeout": request.timeout,
        "number": request.numberOfBots,
        "alive": request.numberOfBots,
        "user_id": request.userId
    }).execute()

    # send requests to google cloud run to start jobs
    for i in range(request.numberOfBots):
        await http_client.post(
            zoombotTestingStartUrl,
            headers={
                'Authorization': f'Bearer {access_token}',
            },
            json=payload
        )
   
    return {"success": True}


@app.post("/test/zoom")
async def launch_zoombot(request: MeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    bot_id = str(uuid.uuid4())
    payload = create_payload(request, bot_id)

    # get cloud run access token
    r = await http_client.post(
        metadataUrl,
        headers={
            "Metadata-Flavor": "Google"
        }
    )
    json = await r.json()
    access_token = json['access_token']

    # create entry in bots table
    await supabase_client.schema("public").table('bots').insert({
        "meeting_url": request.meetingUrl,
        "timeout": request.timeout,
        "user_id": request.userId,
        "id": bot_id
    }).execute()

    # send reqeust to google cloud run to start the job
    start_job = await http_client.post(
        zoombotTestingStartUrl,
        headers={
            'Authorization': f'Bearer {access_token}',
        },
        json=payload
    )
    return_data = await start_job.json()

    return return_data


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT') or 8000))
