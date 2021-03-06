import os
import pathlib
import secrets
import time
from typing import Optional

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.param_functions import Cookie, Depends
from fastapi.params import Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

SECRET_KEY = os.environ.get("SECRET_KEY", "ef4ac4e2a33e4d9e0bb34200349e3544")

templates = Jinja2Templates(directory=pathlib.Path(__file__).parent / "templates")


fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}


class RequiresLoginException(Exception):
    pass


app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app.mount("/ws", socketio.ASGIApp(sio))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/static",
    StaticFiles(directory=pathlib.Path(__file__).parent / "templates"),
    name="static",
)

@app.exception_handler(RequiresLoginException)
async def exception_handler(*args, **kwargs) -> Response:
    return RedirectResponse(url="/", status_code=303)


def verify_session_id(request: Request, session_id: Optional[str] = Cookie(...)):
    username = request.session.get(session_id)
    if username not in fake_users_db:
        raise RequiresLoginException
    return username


@app.get("/view")
async def view(request: Request, username: str = Depends(verify_session_id)):
    await sio.emit("message", "hello universe")
    return templates.TemplateResponse(
        "view.html",
        {
            "request": request,
            "current_user": username,
            "start_time": request.session.get("start_time", int(time.time())),
            "PORT": os.environ.get("PORT", 8000),
        },
    )


@app.get("/")
def index(request: Request):
    # if there's some session, the user may likely be logged in
    # try redirecting to the /view
    if request.session:
        return RedirectResponse(url="/view", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username not in fake_users_db:
        response = RedirectResponse(url="/", status_code=303)
        return response
    response = RedirectResponse(url="/view", status_code=303)
    session_id = secrets.token_hex(16)
    request.session.update(
        {
            session_id: username,
            "start_time": int(time.time()),
            "username": username,
        }
    )
    response.set_cookie("session_id", session_id)
    return response


@app.get("/logout", name="logout")
async def logout(request: Request, username: str = Depends(verify_session_id)):
    """Logout and redirect to Login screen"""
    request.session.clear()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session_id", None)
    await sio.emit("logout", username)
    return response


@sio.event
async def connect(sid, environ):
    session = environ["asgi.scope"]["session"]
    await sio.emit("new user", session)


@sio.event
async def message(sid, data):
    await sio.emit("message", data, room=sid)
