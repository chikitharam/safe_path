from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, EmailStr

# ==========================================
# USER & SEGMENT SCHEMAS
# ==========================================
class UserCreate(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6)

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime
    is_verified: bool = False
    model_config = ConfigDict(from_attributes=True)

class RoadSegmentCreate(BaseModel):
    name: str
    start_location: str = Field(..., examples=["POINT(78.4867 17.3850)"])
    end_location: str = Field(..., examples=["POINT(78.4900 17.3900)"])

class RoadSegmentResponse(RoadSegmentCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# FACILITY SCHEMAS
# ==========================================
class FacilityCreate(BaseModel):
    facility_type: str = Field(..., examples=["Police Station"])
    name: str = Field(..., examples=["Central Police HQ"])
    location: str = Field(..., examples=["POINT(78.4867 17.3850)"])

class FacilityResponse(FacilityCreate):
    id: int
    verification_status: str
    address: str | None = None
    phone_number: str | None = None
    verification_date: str | None = None
    model_config = ConfigDict(from_attributes=True)

class FacilityNearbyRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, examples=[17.3850])
    lng: float = Field(..., ge=-180, le=180, examples=[78.4867])
    radius_km: float = Field(default=5.0, gt=0, le=50, examples=[5.0])

class NearbyFacilityResponse(BaseModel):
    id: int
    facility_type: str
    name: str
    lat: float
    lng: float
    distance_meters: float
    verification_status: str

class PoliceStationResponse(BaseModel):
    id: int
    name: str
    address: str | None
    phone_number: str | None
    lat: float
    lng: float
    distance_meters: float
    verification_date: str | None
    source: str | None

# ==========================================
# SAFETY REPORT SCHEMAS
# ==========================================
class SafetyReportCreate(BaseModel):
    segment_id: int
    report_type: Literal[
        "Harassment", "Stalking", "Suspicious Behaviour", 
        "Poor Lighting", "Isolated Road", "Theft", "Accident", "Other"
    ] = Field(..., examples=["Harassment"])
    description: str | None = Field(default=None, max_length=500)
    incident_time: datetime | None = Field(default=None)
    evidence_url: str | None = Field(default=None, max_length=500)
    source: str = Field(default="mobile_app")

class SafetyReportResponse(BaseModel):
    id: int
    segment_id: int
    report_type: str
    description: str | None
    incident_time: datetime | None
    evidence_url: str | None
    created_at: datetime
    status: str
    verification_status: str
    source: str
    is_own_report: bool = Field(default=False)
    model_config = ConfigDict(from_attributes=True)

class ReportStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"] = Field(...)

class ReportDeleteResponse(BaseModel):
    message: str
    report_id: int

# ==========================================
# LIGHTING SCHEMAS
# ==========================================
class LightingObservationCreate(BaseModel):
    segment_id: int
    is_broken: bool
    notes: str | None = None

class LightingObservationResponse(LightingObservationCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# JOURNEY SCHEMAS
# ==========================================
class JourneyStartRequest(BaseModel):
    start_lat: float = Field(..., ge=-90, le=90)
    start_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    safety_monitoring_enabled: bool = Field(default=False)
    check_in_interval_minutes: int = Field(default=15, gt=0)

class JourneyResponse(BaseModel):
    id: int
    user_id: int
    status: str
    started_at: datetime
    last_check_in_at: datetime | None
    last_known_lat: float | None
    last_known_lng: float | None
    destination_lat: float | None
    destination_lng: float | None
    safety_monitoring_enabled: bool
    check_in_interval_minutes: int
    consecutive_deviations: int
    model_config = ConfigDict(from_attributes=True)

class JourneyEndResponse(BaseModel):
    message: str
    journey_id: int
    status: str
    duration_minutes: float

class LocationPingRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class LocationPingResponse(BaseModel):
    message: str
    journey_id: int
    current_status: str
    last_known_lat: float
    last_known_lng: float
    deviation_detected: bool = False

class SafetyCheckResponse(BaseModel):
    journey_id: int
    status: str
    is_overdue: bool
    is_deviated: bool
    consecutive_deviations: int
    distance_from_route_meters: float | None
    alert_created: bool
    message: str

# ==========================================
# ALERT & EMERGENCY SCHEMAS
# ==========================================
class AlertCreate(BaseModel):
    user_id: int
    message: str

class AlertResponse(AlertCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EmergencyContactCreate(BaseModel):
    name: str = Field(..., max_length=100)
    phone_number: str = Field(..., max_length=100)
    relationship_type: str = Field(..., max_length=50)

class EmergencyContactResponse(EmergencyContactCreate):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class TriggerAlertResponse(BaseModel):
    message: str
    alert_id: int
    status: str
    journey_status: str
    triggered_at: datetime

class EmergencyTriggerRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, examples=[17.3850])
    lng: float = Field(..., ge=-180, le=180, examples=[78.4867])

class AlertStatusResponse(BaseModel):
    alert_id: int
    delivery_status: str
    delivery_details: str | None
    contacts_notified: int
    triggered_at: datetime
    model_config = ConfigDict(from_attributes=True)

class EmergencyHealthResponse(BaseModel):
    status: str
    message: str

class EmergencyAlertRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    user_id: int | None = Field(default=None, description="Optional: Only provide if logged in")

class EmergencyAlertResponse(BaseModel):
    alert_id: int
    status: str
    message: str
    contacts_notified: int = 0

# ==========================================
# ROUTING SCHEMAS
# ==========================================
class RouteRequest(BaseModel):
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    preference: str = Field(default="car")
    priority: str = Field(default="safety")

class GeometryPoint(BaseModel):
    lat: float
    lng: float

class CandidateRoute(BaseModel):
    route_id: str
    distance_km: float
    duration_min: float
    geometry: list[GeometryPoint]
    safety_score: float
    safety_rating: str
    reasons: list[str]
    data_warnings: list[str]

class RouteResponse(BaseModel):
    status: str = Field(default="success")
    origin: GeometryPoint
    destination: GeometryPoint
    routes: list[CandidateRoute]
    recommended_route_id: str
    model_version: str = Field(default="v1.0")
    calculation_time_ms: float
    disclaimer: str = Field(default="Safety scores are based on community reports...")

# ==========================================
# AUTHENTICATION SCHEMAS
# ==========================================
class UserSignup(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_name: str
    user_id: str  # <-- REQUIRED for dashboard to identify the user

class VerifyEmailRequest(BaseModel):
    token: str

# ==========================================
# DASHBOARD SCHEMAS (Module 5)
# ==========================================
class CheckInResponse(BaseModel):
    message: str
    status: str
    last_check_in_at: datetime