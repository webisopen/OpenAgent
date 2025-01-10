import uvicorn


def run():
    uvicorn.run("openagent.router.server:app", host="0.0.0.0", reload=True)
