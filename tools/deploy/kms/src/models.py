from pydantic import BaseModel
import datetime


class ApiBucketKeyPerm(BaseModel):
    owner: bool
    read: bool
    write: bool


class KeyInfoBucketResponse(BaseModel):
    id: str
    global_aliases: list[str]
    local_aliases: list[str]
    permissions: list[ApiBucketKeyPerm] | None


class KeyInfoResponse(BaseModel):
    name: str
    expired: bool
    buckets: list[KeyInfoBucketResponse]
    access_key_id: str
    secret_access_key: str | None
    expiration: datetime.datetime | None
