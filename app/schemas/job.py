from typing import Optional

from pydantic import BaseModel


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

    class Config:
        orm_mode = True


# Properties to return to client
class Job(JobInDBBase):
    pass


# Properties properties stored in DB
class JobInDB(JobInDBBase):
    pass
