from fastapi import Header, HTTPException


async def get_basic_header(x_token):
    print(x_token)
    if x_token != "fake-super-secret-token":
        raise HTTPException(status_code=400, detail="X-Token header invalid")

