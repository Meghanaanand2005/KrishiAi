"""
api.py - KrishiAI Weather Advisory REST API

Run from the src/ folder:

    uvicorn api:app --reload --port 8000

Then open http://127.0.0.1:8000/docs for interactive Swagger documentation
(click "Authorize" and sign in with any KrishiAI account).

Endpoints (all under /api/v1, HTTP Basic auth with your KrishiAI login)
----------------------------------------------------------------------
GET     /advisories          list your advisories (filter + paginate)
POST    /advisories          create one
GET     /advisories/{id}     read one
PUT     /advisories/{id}     replace one (all writable fields)
PATCH   /advisories/{id}     update some fields
DELETE  /advisories/{id}     delete one
GET     /weather?city=...    current conditions + generated advice (not stored)

GET /health is public.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import advisory_service as service
import auth
import database
from schemas import (
    AdvisoryCreate, AdvisoryList, AdvisoryOut, AdvisoryPatch, AdvisoryReplace,
    Severity, Status, WeatherOut,
)

DESCRIPTION = """
Create, read, update and delete **weather advisories**: a saved snapshot of
weather readings for a location together with rule-based farming tips.

* **Authentication**: HTTP Basic, using the same username and password as the
  KrishiAI web app. Use the *Authorize* button above to try the endpoints.
* **Ownership**: you only ever see and change your own advisories. Asking for
  someone else's record returns `404`, the same as a record that doesn't exist.
* **Errors**: `401` bad credentials, `404` not found, `422` invalid body
  (the response lists which field failed and why).
"""

TAGS = [
    {"name": "Weather advisories", "description": "CRUD operations on saved advisories."},
    {"name": "Weather", "description": "Current conditions and generated advice (nothing is saved)."},
    {"name": "System", "description": "Service status."},
]


@asynccontextmanager
async def lifespan(_app):
    database.init_db()  # lets the API run on its own, before the web app has ever started
    yield


app = FastAPI(
    title="KrishiAI Weather Advisory API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS,
    lifespan=lifespan,
)

_basic = HTTPBasic(realm="KrishiAI", description="Your KrishiAI username and password")


def current_user(credentials: HTTPBasicCredentials = Depends(_basic)):
    user, _message = auth.login(credentials.username, credentials.password)
    if not user:
        # Deliberately vague: don't reveal whether the username exists.
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": 'Basic realm="KrishiAI"'},
        )
    return user


@app.exception_handler(service.AdvisoryNotFound)
async def _not_found_handler(_request: Request, exc: service.AdvisoryNotFound):
    return JSONResponse(status_code=404, content={"detail": f"Advisory {exc.args[0]} not found."})


AdvisoryId = Path(ge=1, description="Advisory id")
NOT_FOUND = {404: {"description": "Advisory not found (or it belongs to another user)."}}
UNAUTHORIZED = {401: {"description": "Missing or invalid credentials."}}

router = APIRouter(prefix="/api/v1", responses=UNAUTHORIZED)


# ------------------------------------------------------- advisories (CRUD) ---

@router.get("/advisories", response_model=AdvisoryList, tags=["Weather advisories"],
            summary="List advisories")
def list_advisories(
    city: Optional[str] = Query(None, description="Case-insensitive substring match"),
    severity: Optional[Severity] = None,
    status: Optional[Status] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
):
    return service.list_advisories(user["id"], city, severity, status, limit, offset)


@router.post("/advisories", response_model=AdvisoryOut, status_code=201, tags=["Weather advisories"],
             summary="Create an advisory")
def create_advisory(payload: AdvisoryCreate, response: Response, user=Depends(current_user)):
    created = service.create_advisory(user["id"], payload)
    response.headers["Location"] = f"/api/v1/advisories/{created['id']}"
    return created


@router.get("/advisories/{advisory_id}", response_model=AdvisoryOut, responses=NOT_FOUND,
            tags=["Weather advisories"], summary="Get one advisory")
def get_advisory(advisory_id: int = AdvisoryId, user=Depends(current_user)):
    return service.get_advisory(user["id"], advisory_id)


@router.put("/advisories/{advisory_id}", response_model=AdvisoryOut, responses=NOT_FOUND,
            tags=["Weather advisories"], summary="Replace an advisory",
            description="Replaces every writable field. Fields left out fall back to their defaults "
                        "(`rainfall_mm` and `wind_speed` to 0, `status` to `active`, `crop` and `notes` to empty). "
                        "To change only some fields, use PATCH.")
def replace_advisory(payload: AdvisoryReplace, advisory_id: int = AdvisoryId, user=Depends(current_user)):
    return service.replace_advisory(user["id"], advisory_id, payload)


@router.patch("/advisories/{advisory_id}", response_model=AdvisoryOut, responses=NOT_FOUND,
              tags=["Weather advisories"], summary="Update some fields of an advisory",
              description="Only the fields you send are changed. Send `null` for `crop` or `notes` to clear them.")
def patch_advisory(payload: AdvisoryPatch, advisory_id: int = AdvisoryId, user=Depends(current_user)):
    return service.patch_advisory(user["id"], advisory_id, payload)


@router.delete("/advisories/{advisory_id}", status_code=204, responses=NOT_FOUND,
               tags=["Weather advisories"], summary="Delete an advisory")
def delete_advisory(advisory_id: int = AdvisoryId, user=Depends(current_user)):
    service.delete_advisory(user["id"], advisory_id)
    return Response(status_code=204)


# ------------------------------------------------------------------ weather ---

@router.get("/weather", response_model=WeatherOut, tags=["Weather"],
            summary="Current conditions and advice for a city")
def current_weather(city: str = Query(..., min_length=1, max_length=80, examples=["Belagavi"]),
                    user=Depends(current_user)):
    return service.current_conditions(city.strip())


# ------------------------------------------------------------------- system ---

@app.get("/health", tags=["System"], summary="Service status")
def health():
    return {"status": "ok", "service": "krishiai-weather-advisory-api", "version": app.version}


app.include_router(router)
