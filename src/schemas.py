"""
schemas.py

Request / response models for the Weather Advisory REST API.

They live in their own module so the FastAPI endpoints (api.py) and the
Streamlit forms (views/weather.py) validate against exactly the same rules --
there is one definition of "a valid advisory", not two.

Which model is used where
-------------------------
POST   /advisories        AdvisoryCreate   weather readings optional (auto-fetched)
PUT    /advisories/{id}   AdvisoryReplace  every writable field required (full replace)
PATCH  /advisories/{id}   AdvisoryPatch    any subset of fields (partial update)
(responses)               AdvisoryOut, AdvisoryList, WeatherOut
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Severity = Literal["info", "watch", "warning"]
Status = Literal["active", "resolved"]

SEVERITIES = ("info", "watch", "warning")
STATUSES = ("active", "resolved")

# Ranges chosen to stay physically plausible for Indian farm locations.
TEMP_RANGE = (-50.0, 60.0)
CORE_READINGS = ("temperature", "humidity", "condition")


def _validate_tips(tips):
    if tips is None:
        return tips
    cleaned = [" ".join(t.split()) for t in tips if t and t.strip()]
    if not cleaned:
        raise ValueError("Provide at least one non-empty tip.")
    if len(cleaned) > 10:
        raise ValueError("At most 10 tips are allowed.")
    for t in cleaned:
        if len(t) > 300:
            raise ValueError("Each tip must be 300 characters or fewer.")
    return cleaned


class _Strict(BaseModel):
    """Trim whitespace and reject unknown fields (catches typos like 'temprature')."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


# --------------------------------------------------------------- requests ---

class AdvisoryCreate(_Strict):
    """POST body.

    Send only `city` and the server fetches current conditions (live if an
    OpenWeatherMap key is configured, otherwise simulated) and generates the
    tips and severity for you. Or send temperature + humidity + condition
    yourself to record your own readings.
    """
    city: str = Field(min_length=1, max_length=80, examples=["Belagavi"])
    temperature: Optional[float] = Field(default=None, ge=TEMP_RANGE[0], le=TEMP_RANGE[1], description="Degrees Celsius")
    humidity: Optional[float] = Field(default=None, ge=0, le=100, description="Relative humidity, %")
    condition: Optional[str] = Field(default=None, min_length=1, max_length=40, examples=["Light Rain"])
    rainfall_mm: Optional[float] = Field(default=None, ge=0, le=1000)
    wind_speed: Optional[float] = Field(default=None, ge=0, le=150, description="Metres per second")
    crop: Optional[str] = Field(default=None, max_length=60, examples=["Sugarcane"])
    severity: Optional[Severity] = Field(default=None, description="Derived from the readings when omitted")
    status: Status = "active"
    tips: Optional[List[str]] = Field(default=None, description="Generated from the readings when omitted")
    notes: Optional[str] = Field(default=None, max_length=500)

    _tips = field_validator("tips")(_validate_tips)

    @model_validator(mode="after")
    def _readings_all_or_nothing(self):
        supplied = [f for f in CORE_READINGS if getattr(self, f) is not None]
        if supplied and len(supplied) < len(CORE_READINGS):
            raise ValueError(
                "Send all of temperature, humidity and condition, or none of them "
                "(none = fetch current weather for the city)."
            )
        if not supplied and (self.rainfall_mm is not None or self.wind_speed is not None):
            raise ValueError("rainfall_mm and wind_speed can only be sent together with temperature, humidity and condition.")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"examples": [
            {"city": "Belagavi", "crop": "Sugarcane", "notes": "Auto-fetch current weather"},
            {"city": "Hubballi", "temperature": 27.5, "humidity": 84, "condition": "Light Rain",
             "rainfall_mm": 7.2, "wind_speed": 4.1, "crop": "Maize"},
        ]},
    )


class AdvisoryReplace(BaseModel):
    """PUT body: replaces the whole record. Read-only fields (id, timestamps) are ignored."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",
        json_schema_extra={"examples": [{
            "city": "Belagavi", "temperature": 31.0, "humidity": 48, "condition": "Clear",
            "rainfall_mm": 0, "wind_speed": 3.2, "crop": "Sugarcane", "severity": "info",
            "status": "active", "tips": ["Conditions are favorable for routine field operations."],
            "notes": "Reviewed by extension officer",
        }]},
    )

    city: str = Field(min_length=1, max_length=80)
    temperature: float = Field(ge=TEMP_RANGE[0], le=TEMP_RANGE[1])
    humidity: float = Field(ge=0, le=100)
    condition: str = Field(min_length=1, max_length=40)
    rainfall_mm: float = Field(default=0, ge=0, le=1000)
    wind_speed: float = Field(default=0, ge=0, le=150)
    crop: Optional[str] = Field(default=None, max_length=60)
    severity: Severity
    status: Status = "active"
    tips: List[str]
    notes: Optional[str] = Field(default=None, max_length=500)

    _tips = field_validator("tips")(_validate_tips)


class AdvisoryPatch(_Strict):
    """PATCH body: send only the fields you want to change."""
    city: Optional[str] = Field(default=None, min_length=1, max_length=80)
    temperature: Optional[float] = Field(default=None, ge=TEMP_RANGE[0], le=TEMP_RANGE[1])
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    condition: Optional[str] = Field(default=None, min_length=1, max_length=40)
    rainfall_mm: Optional[float] = Field(default=None, ge=0, le=1000)
    wind_speed: Optional[float] = Field(default=None, ge=0, le=150)
    crop: Optional[str] = Field(default=None, max_length=60, description="Send null to clear")
    severity: Optional[Severity] = None
    status: Optional[Status] = None
    tips: Optional[List[str]] = None
    notes: Optional[str] = Field(default=None, max_length=500, description="Send null to clear")

    _tips = field_validator("tips")(_validate_tips)

    @model_validator(mode="after")
    def _at_least_one_field(self):
        nullable = {"crop", "notes"}
        sent = self.model_fields_set
        if not sent:
            raise ValueError("Send at least one field to update.")
        for name in sent - nullable:
            if getattr(self, name) is None:
                raise ValueError(f"'{name}' cannot be null.")
        return self

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"examples": [
            {"status": "resolved"},
            {"severity": "warning", "notes": "Heavy rain expected tonight"},
        ]},
    )


# -------------------------------------------------------------- responses ---

class AdvisoryOut(BaseModel):
    id: int
    city: str
    temperature: float
    humidity: float
    condition: str
    rainfall_mm: float
    wind_speed: float
    crop: Optional[str] = None
    severity: Severity
    status: Status
    tips: List[str]
    notes: Optional[str] = None
    source: str = Field(description="Where the readings came from, e.g. 'OpenWeatherMap (live)' or 'manual'")
    created_at: str
    updated_at: str


class AdvisoryList(BaseModel):
    items: List[AdvisoryOut]
    total: int = Field(description="Records matching the filters, ignoring limit/offset")
    limit: int
    offset: int


class WeatherOut(BaseModel):
    city: str
    temperature: float
    humidity: float
    condition: str
    rainfall_mm: float
    wind_speed: float
    source: str
    severity: Severity
    tips: List[str]
