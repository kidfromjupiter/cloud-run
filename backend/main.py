from fastapi import FastAPI
import uvicorn
from os import environ
from pydantic import BaseModel
import requests

app = FastAPI()
metadataUrl = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
zoombotTestingStartUrl = "https://run.googleapis.com/v2/projects/woven-arcadia-432212-a6/locations/us-central1/jobs/zoombot-testing:run"

class MeetingRequest(BaseModel):
    meetingUrl: str
    timeout: int
    botName: str
    botId: str
    fromId: str
    wsLink: str


@app.get("/", tags=["root"])
async def root():
    return {"message": "Hello World"}

@app.post("/test/zoom")
async def launch_zoombot(request:MeetingRequest):
    payload = {
        'overrides':{
            "containerOverrides":[
                {
                    "env":[
                        {"name":"MEETING_URL","value":request.meetingUrl},
                        {"name":"BOTNAME","value":request.botName},
                        {"name":"TIMEOUT","value":request.timeout},
                        {"name":"BOT_ID","value":request.botId},
                        {"name":"WS_LINK","value":request.wsLink},
                        {"name":"FROM_ID","value":request.fromId},
                    ]
                }
            ]
        }
    }
    r = requests.post(
        metadataUrl,
        headers={
            "Metadata-Flavor":"Google"
        }
    )
    access_token = r.json()['access_token']
    start_job = requests.post(
        zoombotTestingStartUrl,
        headers={
            'Authorization':f'Bearer {access_token}',
        },
        json=payload
    )
    return start_job.json()
     
if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT') or 8000))
