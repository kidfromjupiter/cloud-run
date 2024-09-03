from contextlib import asynccontextmanager
from os import environ

import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from .aiohttp_singleton import HttpClient
from supabase import AClient, acreate_client

load_dotenv(".env")

supabase_client: AClient = None
SUPABSE_SERVICE_KEY = environ.get("SUPABSE_SERVICE_KEY")
SUPABASE_URL = environ.get("SUPABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    supabase_client = await acreate_client(SUPABASE_URL, SUPABSE_SERVICE_KEY)
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


class BatchMeetingRequest(BaseModel):
    meetingUrl: str
    timeout: int
    botName: str
    botId: str
    fromId: str
    wsLink: str
    numberOfBots: int


http_client = HttpClient()


def create_payload(request: MeetingRequest) -> dict:
    return {
        'overrides': {
            "containerOverrides": [
                {
                    "env": [
                        {"name": "MEETING_URL", "value": request.meetingUrl},
                        {"name": "BOTNAME", "value": request.botName},
                        {"name": "TIMEOUT", "value": str(request.timeout)},
                        {"name": "BOT_ID", "value": request.botId},
                        {"name": "WS_LINK", "value": request.wsLink},
                        {"name": "FROM_ID", "value": request.fromId},
                    ]
                }
            ]
        }
    }


@app.on_event("startup")
async def startup():
    http_client.start()


@app.get("/", tags=["root"])
async def root():
    return {"message": "Hello World"}


@app.post("/done/{user_id}/{bot_id}")
async def done(user_id: str, bot_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    # TODO: Get bot status from db. get started time
    # TODO: Get user credits. Reduce appropriate amount
    # TODO: Set bot as completed
    pass


@app.post("/started/{user_id}/{bot_id}")
async def started(user_id: str, bot_id: str, http_client: aiohttp.ClientSession = Depends(http_client)):
    r = await http_client.post(
        f"{environ.get('SUPABASE_URL')}/rest/v1/bot?select"
    )
    # TODO: set bot as started in db. Set bot UUID. Set 
    pass



@app.post("/test/zoom")
async def launch_zoombot(request: MeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    await supabase_client.auth.sign_in_anonymously()
    await supabase_client.table('bot').insert({

        "start_time":datetime.now(timezone.utc),
        "meeting_url": request.meetingUrl,
        "timeout": request.timeout,
        "user_id": supabase_client.auth.get_user()['id']
    })
    
    payload = create_payload(request)
    r = await http_client.post(
        metadataUrl,
        headers={
            "Metadata-Flavor": "Google"
        }
    )
    access_token = r.json()['access_token']
    for i in range(request.numberOfBots):
        await http_client.post(
            zoombotTestingStartUrl,
            headers={
                'Authorization': f'Bearer {access_token}',
            },
            json=payload
        )
    return {"success": "true"}


@app.post("/test/batch/zoom")
async def launch_batch_zoombot(request: MeetingRequest, http_client: aiohttp.ClientSession = Depends(http_client)):
    payload = create_payload(request)
    r = await http_client.post(
        metadataUrl,
        headers={
            "Metadata-Flavor": "Google"
        }
    )
    access_token = r.json()['access_token']
    start_job = await http_client.post(
        zoombotTestingStartUrl,
        headers={
            'Authorization': f'Bearer {access_token}',
        },
        json=payload
    )
    return start_job.json()


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT') or 8000))
