from typing import Optional

from pydantic import BaseModel, ConfigDict


# Shared properties
class JobBase(BaseModel):
    name: Optional[str] = None
    output: Optional[str] = None


# Properties to receive on item creation
class JobCreate(JobBase):
    pass


# Properties to receive on item update
class JobUpdate(JobBase):
    pass


# Properties shared by models stored in DB
class JobInDBBase(JobBase):
    id: int
    name: str
    owner_id: int

    model_config = ConfigDict(from_attributes=True)


# Properties to return to client
class Job(JobInDBBase):
    pass


# Properties properties stored in DB
class JobInDB(JobInDBBase):
    pass
