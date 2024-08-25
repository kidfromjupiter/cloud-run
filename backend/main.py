from fastapi import FastAPI
import uvicorn
from os import environ
app = FastAPI()


@app.get("/", tags=["root"])
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=int(environ.get('PORT')))
