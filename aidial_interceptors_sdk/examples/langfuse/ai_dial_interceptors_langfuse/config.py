from pydantic import BaseModel


class LangfuseConfig(BaseModel):
    secret_key: str
    public_key: str
    host: str


class Config(BaseModel):
    track_user_data: bool
    langfuse: LangfuseConfig
