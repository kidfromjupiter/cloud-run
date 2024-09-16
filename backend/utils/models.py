from pydantic import BaseModel, Field


class MeetingRequest(BaseModel):
    meetingUrl: str
    timeout: int = Field(default=None, description="Timeout of the bot in seconds")
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


class Location(BaseModel):
    name: str
    last_modified: str
    value: int


class InsufficientFunds(BaseModel):
    desc: str

class MalformedRequest(BaseModel):
    desc: str

class ZoomSBResponse(BaseModel):
    id: str
    created_at: str
    meeting_url: str
    timeout: int = Field(default=None, description="Timeout of the bot in seconds")
    completed: bool
    user_id: str
    name: str


class ZoomBatchSBResponse(BaseModel):
    id: str
    created_at: str
    meeting_url: str
    timeout: int = Field(default=None, description="Timeout of the bot in seconds")
    number: int
    alive: int
    name: str


class ProfileInfo(BaseModel):
    userId: str


class ZoomBatchResponse(BaseModel):
    data: list[ZoomBatchSBResponse]
    count: None | int


class ZoomResponse(BaseModel):
    data: list[ZoomSBResponse]
    count: None | int
