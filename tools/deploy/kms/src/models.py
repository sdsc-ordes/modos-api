"""Data models from Garage S3 API."""

from pydantic import BaseModel, Field
import datetime


class ApiBucketKeyPerm(BaseModel):
    owner: bool
    read: bool
    write: bool


class KeyInfoBucketResponse(BaseModel):
    id: str
    global_aliases: list[str] = Field(alias="globalAliases")
    local_aliases: list[str] = Field(alias="localAliases")
    permissions: list[ApiBucketKeyPerm] | None


class KeyInfoResponse(BaseModel):
    name: str
    expired: bool
    buckets: list[KeyInfoBucketResponse]
    access_key_id: str = Field(alias="accessKeyId")
    secret_access_key: str | None = Field(
        default=None, alias="secretAccessKey"
    )
    expiration: datetime.datetime | None
