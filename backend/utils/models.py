from pydantic import BaseModel, Field


class MeetingRequest(BaseModel):
    meeting_url: str
    timeout: int = Field(default=None, description="Timeout of the bot in seconds")
    bot_name: str
    bot_id: str
    from_id: str
    ws_link: str
    user_id: str


class BatchMeetingRequest(BaseModel):
    meeting_url: str
    timeout: int
    bot_name: str
    bot_id: str
    from_id: str
    ws_link: str
    number_of_bots: int
    user_id: str


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
    group_name: str


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
