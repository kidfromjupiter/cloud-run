import io
import logging as lg
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from os import environ
from typing import Annotated, Optional

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import AClient, acreate_client

from utils.aiohttp_singleton import HttpClient
from utils.models import MeetingRequest, Location, InsufficientFunds, ZoomBatchResponse, \
    ZoomResponse, MalformedRequest, KillAllRequest, EventArcRequest

load_dotenv(".env")

# lg.basicConfig(level=lg.INFO, filename="/var/log/py.log", filemode="w")

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


# ws_manager = ConnectionManager()
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


def create_payload(
        meeting_url: str,
        bot_name: str, ws_link: str,
        from_id: str, timeout: int,
        bot_id: str, group_id: str | None = None,
        password: str | None = None,
        webinar: bool | None = None,

) -> dict:
    websocket_link = f"http://localhost:8000/ws/{bot_id}" if environ.get("DEV") else ws_link
    return {
        'overrides': {
            "containerOverrides": [
                {
                    "env": [
                        {"name": "MEETING_URL", "value": meeting_url},
                        {"name": "BOTNAME", "value": bot_name},
                        {"name": "TIMEOUT", "value": str(timeout)},
                        {"name": "BOT_ID", "value": bot_id},
                        {"name": "WS_LINK", "value": websocket_link},
                        {"name": "FROM_ID", "value": from_id},
                        {"name": "GROUP_ID", "value": group_id},
                        {"name": "PASSWORD", "value": password},
                        {"name": "WEBINAR", "value": str(webinar) if webinar is not None else None},
                    ]
                }
            ]
        }
    }


# @app.websocket("/ws/{bot_id}")
# async def websocket_endpoint(websocket: WebSocket, bot_id: str):
#     await ws_manager.connect(websocket, bot_id)
#     print("Connected", bot_id)
#     try:
#         async for message in websocket.iter_json():
#             print(message)
#     except WebSocketDisconnect:
#         ws_manager.disconnect(bot_id)
#         print(f"Client #{bot_id} left the chat")
# 
# 
# @app.websocket("/ws/group/{group_id}")
# async def websocket_endpoint(websocket: WebSocket, group_id: str):
#     await ws_manager.connect_group(websocket, group_id)
#     print("Connected bot in group", group_id)
#     try:
#         async for message in websocket.iter_json():
#             print(message)
#     except WebSocketDisconnect:
#         ws_manager.disconnect(group_id)
#         print(f"Client #{group_id} left the chat")


@app.get("/test/bots/{user_id}",
         responses={
             200: {"model": ZoomResponse}
         })
async def bots(user_id: str):
    response = await (supabase_client.table("bots")
                      .select("*")
                      .eq("user_id", user_id)
                      .eq("completed", False)
                      ).execute()
    return response


@app.get("/test/current_usage/{user_id}")
async def current_usage(user_id: str):
    (__, botgroups_list), _ = await (supabase_client.table("botgroups")
                                     .select("alive")
                                     .eq("user_id", f'{user_id}')
                                     .gt("alive", 0)
                                     .execute())
    (__, _), (___, count) = await (supabase_client.table("bots")
                                   .select("*", count='exact')
                                   .eq("user_id", f'{user_id}')
                                   .eq("completed", False)
                                   .execute())
    total_alive_in_botgroups = count
    for botgroup in botgroups_list:
        total_alive_in_botgroups += int(botgroup['alive'])

    return total_alive_in_botgroups


@app.get("/test/credits/{user_id}")
async def credits(user_id: str):
    (__, profile_data), _ = await (supabase_client.table("profiles")
                                   .select("credits")
                                   .eq("user_id", f'{user_id}')
                                   .execute())
    return profile_data[0]['credits']


@app.get("/test/groups/{user_id}",
         responses={
             200: {"model": ZoomBatchResponse}
         })
async def bots_groups(user_id: str):
    response = await (supabase_client.table("botgroups")
                      .select("*")
                      .eq("user_id", user_id)
                      .gt("alive", 0)
                      ).execute()
    return response


@app.post("/done/{user_id}/{bot_id}")
async def done(user_id: str, bot_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    supabase_client.rpc("update_credits_and_bots",{
        'profile_id': user_id,
        'bot_id': bot_id,
    })
    return True

@app.post("/done/group/{user_id}/{group_id}")
async def done_group(user_id: str, group_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    supabase_client.rpc("update_credits_and_botgroup",{
        'profile_id': user_id, 
        'group_id': group_id,
    })
    return True


@app.post("/test/batch/zoom",
          responses={
              410: {"model": InsufficientFunds},
              200: {"model": ZoomBatchResponse},
              404: {"model": MalformedRequest}
          })
async def launch_batch_zoombot(timeout: Annotated[int, Form()],
                               user_id: Annotated[str, Form()],
                               number_of_bots: Annotated[int, Form()],
                               meeting_url: Annotated[str, Form()],
                               ws_link: Annotated[str, Form()],
                               name_file: UploadFile,
                               group_name: Annotated[str, Form()],
                               http_client: aiohttp.ClientSession = Depends(http_client),
                               password: Annotated[Optional[str], Form()] = None,
                               webinar: Annotated[Optional[bool], Form()] = None,
                               ):
    bot_group_id = str(uuid.uuid4())
    bot_id = bot_group_id
    ws_link = f"wss://backend-testing-514385437890.us-central1.run.app/ws/{bot_group_id}"
    names = []
    with name_file.file as f:
        for line in io.TextIOWrapper(f, encoding='utf-8'):
            names.append(line.rstrip())

    if number_of_bots != len(names):
        return JSONResponse(status_code=404,
                            content={"desc": "Number of bots must be equal to the number of names provided"})

    # get credits and see if this bot group is runnable
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{user_id}').execute()

    total_credits_for_botgroup = timeout * number_of_bots // 60  # timeout is specified in seconds
    if profile_data_list[0]["credits"] < total_credits_for_botgroup:
        return JSONResponse(status_code=410, content={"desc": "insufficient_credits"})

    access_token = None
    if environ.get("ENV") != "DEV":
        # get cloud run access token
        r = await http_client.post(
            metadataUrl,
            headers={
                "Metadata-Flavor": "Google"
            }
        )
        json = await r.json()
        access_token = json['access_token']

    # send requests to google cloud run to start jobs
    response_list = []
    changed_rows = []
    (data, count) = await (supabase_client.table('locations')
                           .select('name,last_modified,value')
                           .execute())
    all_locs = [Location(**loc) for loc in data[1]]
    meta = []
    for i in range(number_of_bots):
        payload = create_payload(
            meeting_url=meeting_url,
            timeout=timeout,
            ws_link=ws_link,
            bot_name=names[i],
            from_id=user_id,
            bot_id=bot_id,
            group_id=bot_group_id,
            password=password,
            webinar=webinar,
        )  # bot_id == bot_group_id
        print(names[i])
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
            if environ.get("ENV") != "DEV" and access_token is not None:
                response = await http_client.post(
                    getStartUrl(str(location.name)),
                    headers={
                        'Authorization': f'Bearer {access_token}',
                    },
                    json=payload
                )
                response_json = await response.json()
                print(response_json)
                meta.append(response_json['metadata']['name'])
                response_list.append(response_json)
            location.value = location.value + 1
            location.last_modified = datetime.now(tz=timezone.utc).isoformat()
            if location not in changed_rows: changed_rows.append(location)

            break

    # create entry in bot groups table
    supabase_response = await supabase_client.schema("public").table('botgroups').insert({
        "meeting_url": meeting_url,
        "timeout": timeout,
        "number": number_of_bots,
        "alive": number_of_bots,
        "user_id": user_id,
        "id": bot_group_id,
        "name": group_name,
        "meta": meta,
    }).execute()

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
    request.ws_link = f"wss://backend-testing-514385437890.us-central1.run.app/ws/{bot_id}"
    payload = create_payload(
        meeting_url=request.meeting_url,
        ws_link=request.ws_link,
        timeout=request.timeout,
        bot_name=request.name,
        from_id=request.user_id,
        bot_id=bot_id
    )

    print(payload)
    # get credits and see if this bot group is runnable
    (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                       f'{request.user_id}').execute()

    total_credits_for_bot = request.timeout // 60  # timeout is specified in seconds
    if profile_data_list[0]["credits"] < total_credits_for_bot:
        return JSONResponse(status_code=410, content={"desc": "insufficient_credits"})

    if environ.get("ENV") != "DEV":
        # get cloud run access token
        r = await http_client.post(
            metadataUrl,
            headers={
                "Metadata-Flavor": "Google"
            }
        )
        r_json = await r.json()
        access_token = r_json['access_token']

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
        name = "test"
        if environ.get("ENV") != "DEV":
            response = await http_client.post(
                getStartUrl(str(location.name)),
                headers={
                    'Authorization': f'Bearer {access_token}',
                },
                json=payload
            )
            response_json = await response.json()
            name = response_json['metadata']['name']
        location.value = location.value + 1
        location.last_modified = datetime.now(tz=timezone.utc).isoformat()
        if location not in changed_rows: changed_rows.append(location)

        # create entry in bots table
        supabase_response = await supabase_client.schema("public").table('bots').insert({
            "meeting_url": request.meeting_url,
            "timeout": request.timeout,
            "user_id": request.user_id,
            "id": bot_id,
            "name": request.name,
            "meta": name
        }).execute()

        break

    if changed_rows:
        await supabase_client.table('locations').upsert(
            [l.model_dump() for l in changed_rows],
            on_conflict="name"
        ).execute()

    return supabase_response


@app.post("/test/kill/{id}",
          responses={
              200: {"model": ZoomResponse}
          })
async def kill_specific_individual(id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    # await ws_manager.kill(id)
    (__, bots_data_list), _ = await (supabase_client.table("bots")
                                     .select("*")
                                     .eq("id", id)
                                     .execute()
                                     )
    endpoint = bots_data_list[0]["meta"]

    if environ.get("ENV") != "DEV":
        # get cloud run access token
        r = await http_client.post(
            metadataUrl,
            headers={
                "Metadata-Flavor": "Google"
            }
        )
        r_json = await r.json()
        access_token = r_json['access_token']
        await http_client.post(
            f"https://run.googleapis.com/v2/{endpoint}:cancel",
            headers={
                'Authorization': f'Bearer {access_token}',
            },
        )
    return True


@app.post("/test/batch/kill/{id}",
          responses={
              200: {"model": ZoomBatchResponse}
          })
async def kill_specific_batch(id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    # await ws_manager.kill_group(id)
    (__, botgroup_data_list), _ = await (supabase_client.table("botgroups")
                                         .select("*")
                                         .eq("id", id)
                                         .execute()
                                         )
    endpoints = botgroup_data_list[0]['meta']
    print(endpoints)

    if environ.get("ENV") != "DEV":
        # get cloud run access token
        r = await http_client.post(
            metadataUrl,
            headers={
                "Metadata-Flavor": "Google"
            }
        )
        r_json = await r.json()
        access_token = r_json['access_token']
        for endpoint in endpoints:
            await http_client.post(
                f"https://run.googleapis.com/v2/{endpoint}:cancel",
                headers={
                    'Authorization': f'Bearer {access_token}',
                },
            )
    return True


@app.post("/eventarc/bot-cancelled")
async def cancelled_bot(request: EventArcRequest):
    try:
        lg.info("Got cancelled event")
        print("Got cancelled event")
        lg.info(request.json())

        (cancelled_bots_list, _) = await (
            supabase_client.rpc("search_in_meta", {"target_value": request.protoPayload.resourceName}).execute())
        
        print(cancelled_bots_list)
        cancelled_bots_list = cancelled_bots_list[1]

        id = cancelled_bots_list[0]['id']
        user_id = cancelled_bots_list[0]['user_id']
        source_table = cancelled_bots_list[0]['source_table']

        (__, profile_data_list), _ = await supabase_client.table("profiles").select("user_id, credits").eq("user_id",
                                                                                                           f'{user_id}').execute()

        # calculating leftover credits
        credit = profile_data_list[0]["credits"]
        started_time = datetime.fromisoformat(cancelled_bots_list[0]["created_at"])
        time_now = datetime.now(timezone.utc)
        delta = time_now - started_time
        used_creds = delta.seconds // 60

        credit = max(0, credit - used_creds)

        updated_credit_data, _ = await supabase_client.table("profiles").update({"credits": credit}).eq("user_id",
                                                                                                        f"{user_id}").execute()
        if source_table == "bots":
            updated_bot_data, _ = await (supabase_client.table("bots").update({"completed": True})
                                         .eq("id", f"{id}")
                                         .eq("user_id", f"{user_id}")
                                         .execute())
        elif source_table == "botgroups":
            updated_bot_data, _ = await (supabase_client.table("botgroups").update({"alive": 0})
                                         .eq("id", f"{id}")
                                         .eq("user_id", f"{user_id}")
                                         .execute())

        return True
    except Exception as e:
        print(f"Error cancelled-bot: {e}")
        # Need to return true no matter what. Otherwise eventarc resends the same 
        return True


@app.post("/test/killall")
async def kill_all(request: KillAllRequest):
    r = await (supabase_client.table("bots")
               .update({"completed": True})
               .eq("user_id", request.user_id)
               .execute()
               )
    return r


@app.post("/test/batch/killall")
async def kill_all_batch(request: KillAllRequest):
    r = await (supabase_client.table("botgroups")
               .update({"alive": 0})
               .eq("user_id", request.user_id)
               .execute()
               )
    return r


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT') or 8000))
