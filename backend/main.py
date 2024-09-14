import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from os import environ

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import AClient, acreate_client

from utils.aiohttp_singleton import HttpClient
from utils.models import MeetingRequest, BatchMeetingRequest, Location, InsufficientFunds, ZoomBatchResponse, \
    ZoomResponse

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def getStartUrl(location: str):
    return f"https://run.googleapis.com/v2/projects/woven-arcadia-432212-a6/locations/{location}/jobs/zoombot-testing:run"


metadataUrl = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"


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


@app.post("/test/batch/zoom",
          responses={
              410: {"model": InsufficientFunds},
              200: {"model": ZoomBatchResponse}
          })
async def launch_batch_zoombot(request: BatchMeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    bot_id = str(uuid.uuid4())
    bot_group_id = bot_id
    payload = create_payload(request, bot_id, bot_group_id)

    # get credits and see if this bot group is runnable
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{request.userId}').execute()

    total_credits_for_botgroup = request.timeout * request.numberOfBots // 60  # timeout is specified in seconds
    if profile_data_list[0]["credits"] < total_credits_for_botgroup:
        return JSONResponse(status_code=410, content={"desc": "insufficient_credits"})

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
    supabase_response = await supabase_client.schema("public").table('botgroups').insert({
        "meeting_url": request.meetingUrl,
        "timeout": request.timeout,
        "number": request.numberOfBots,
        "alive": request.numberOfBots,
        "user_id": request.userId,
        "id": bot_group_id
    }).execute()

    # send requests to google cloud run to start jobs
    response_list = []
    changed_rows = []
    (data, count) = await (supabase_client.table('locations')
                           .select('name,last_modified,value')
                           .execute())
    all_locs = [Location(**loc) for loc in data[1]]
    for _ in range(request.numberOfBots):
        for location in all_locs:
            val = location.value
            if val >= 64:
                time_delta = datetime.now(tz=timezone.utc) - datetime.fromisoformat(
                    location.last_modified)
                print(time_delta.total_seconds())
                if time_delta.total_seconds() >= 60:
                    location.value = 0
                else:
                    print("switched to another location")
                    # endpoint will hit rate limit if another request is made. So switch to another loc
                    continue
            response = await http_client.post(
                getStartUrl(str(location.name)),
                headers={
                    'Authorization': f'Bearer {access_token}',
                },
                json=payload
            )
            location.value = location.value + 1
            location.last_modified = datetime.now(tz=timezone.utc).isoformat()
            if location not in changed_rows: changed_rows.append(location)

            response_json = await response.json()
            response_list.append(response_json)
            break
    if changed_rows:
        await supabase_client.table('locations').upsert(
            [l.model_dump() for l in changed_rows],
            on_conflict="name"
        ).execute()

    return supabase_response


@app.post("/test/zoom",
          responses={
              200: {"model": ZoomResponse},
              410: {"model": InsufficientFunds}
          })
async def launch_zoombot(request: MeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    bot_id = str(uuid.uuid4())
    payload = create_payload(request, bot_id)

    # get credits and see if this bot group is runnable
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{request.userId}').execute()

    total_credits_for_bot = request.timeout // 60  # timeout is specified in seconds
    if profile_data_list[0]["credits"] < total_credits_for_bot:
        return JSONResponse(status_code=410, content={"desc": "insufficient_credits"})
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
    supabase_response = await supabase_client.schema("public").table('bots').insert({
        "meeting_url": request.meetingUrl,
        "timeout": request.timeout,
        "user_id": request.userId,
        "id": bot_id
    }).execute()

    # send reqeust to google cloud run to start the job
    return_data = None
    changed_rows = []
    (data, count) = await (supabase_client.table('locations')
                           .select('name,last_modified,value')
                           .execute())
    all_locs = [Location(**loc) for loc in data[1]]
    for location in all_locs:
        val = location.value
        if val >= 64:
            time_delta = datetime.now(tz=timezone.utc) - datetime.fromisoformat(
                location.last_modified)
            print(time_delta.total_seconds())
            if time_delta.total_seconds() >= 60:
                location.value = 0
            else:
                print("switched to another location")
                # endpoint will hit rate limit if another request is made. So switch to another loc
                continue
        response = await http_client.post(
            getStartUrl(str(location.name)),
            headers={
                'Authorization': f'Bearer {access_token}',
            },
            json=payload
        )
        location.value = location.value + 1
        location.last_modified = datetime.now(tz=timezone.utc).isoformat()
        if location not in changed_rows: changed_rows.append(location)

        break
    if changed_rows:
        await supabase_client.table('locations').upsert(
            [l.model_dump() for l in changed_rows],
            on_conflict="name"
        ).execute()

    return supabase_response


@app.post("/test/killall")
async def kill_all():
    return JSONResponse(status_code=200)


@app.post("/test/batch/killall")
async def kill_all_batch():
    return JSONResponse(status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT') or 8000))
