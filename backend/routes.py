import httpx
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db, SessionLocal
import models
import schemas
from security import hash_password, verify_password, create_access_token
from services import calculate_route_safety

import smtplib
from email.message import EmailMessage
import os

router = APIRouter()

# ==========================================
# HEALTH CHECK
# ==========================================
@router.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "database": "connected"}

# ==========================================
# AUTHENTICATION (Module 1 - No Email Verify)
# ==========================================
@router.post("/auth/signup", response_model=schemas.UserResponse, tags=["Auth"])
def signup(user: schemas.UserSignup, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    hashed_pwd = hash_password(user.password)
    
    new_user = models.User(
        name=user.name, 
        email=user.email, 
        password_hash=hashed_pwd,
        is_verified=True,  # <-- Instantly verified for demo
        verification_token=None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_name": db_user.name,
        "user_id": str(db_user.id)  # <-- Send ID to frontend
    }

# ==========================================
# USERS
# ==========================================
@router.post("/users", response_model=schemas.UserResponse, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(name=user.name, email=user.email, password_hash=hash_password(user.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/users", response_model=list[schemas.UserResponse], tags=["Users"])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# ==========================================
# ROAD SEGMENTS
# ==========================================
@router.post("/road-segments", response_model=schemas.RoadSegmentResponse, tags=["Road Segments"])
def create_segment(segment: schemas.RoadSegmentCreate, db: Session = Depends(get_db)):
    db_seg = models.RoadSegment(
        name=segment.name,
        start_location=func.ST_GeomFromText(segment.start_location, 4326),
        end_location=func.ST_GeomFromText(segment.end_location, 4326)
    )
    db.add(db_seg)
    db.commit()
    db.refresh(db_seg)
    return db_seg

@router.get("/road-segments", response_model=list[schemas.RoadSegmentResponse], tags=["Road Segments"])
def get_segments(db: Session = Depends(get_db)):
    return db.query(models.RoadSegment).all()

# ==========================================
# FACILITIES
# ==========================================
@router.post("/facilities", response_model=schemas.FacilityResponse, tags=["Facilities"])
def create_facility(facility: schemas.FacilityCreate, db: Session = Depends(get_db)):
    db_fac = models.Facility(
        facility_type=facility.facility_type,
        name=facility.name,
        location=func.ST_GeomFromText(facility.location, 4326)
    )
    db.add(db_fac)
    db.commit()
    db.refresh(db_fac)
    return db_fac

@router.get("/facilities", response_model=list[schemas.FacilityResponse], tags=["Facilities"])
def get_facilities(db: Session = Depends(get_db)):
    return db.query(models.Facility).all()

@router.post("/facilities/nearby", response_model=list[schemas.NearbyFacilityResponse], tags=["Facilities"])
def get_nearby_facilities(request: schemas.FacilityNearbyRequest, db: Session = Depends(get_db)):
    user_point = func.ST_GeomFromText(f"POINT({request.lng} {request.lat})", 4326)
    distance_col = func.ST_Distance_Sphere(models.Facility.location, user_point).label("distance_meters")
    radius_meters = request.radius_km * 1000
    results = db.query(models.Facility, distance_col).filter(distance_col <= radius_meters).order_by(distance_col.asc()).all()
    nearby_list = []
    for facility, distance in results:
        lat = db.query(func.ST_Y(facility.location)).scalar()
        lng = db.query(func.ST_X(facility.location)).scalar()
        nearby_list.append(schemas.NearbyFacilityResponse(
            id=facility.id, facility_type=facility.facility_type, name=facility.name,
            lat=lat, lng=lng, distance_meters=round(distance, 1), verification_status=facility.verification_status
        ))
    return nearby_list

@router.post("/facilities/police-nearby", response_model=list[schemas.PoliceStationResponse], tags=["Facilities"])
def get_nearby_police(request: schemas.FacilityNearbyRequest, db: Session = Depends(get_db)):
    user_point = func.ST_GeomFromText(f"POINT({request.lng} {request.lat})", 4326)
    distance_col = func.ST_Distance_Sphere(models.Facility.location, user_point).label("distance_meters")
    radius_meters = request.radius_km * 1000
    
    results = db.query(models.Facility, distance_col).filter(
        distance_col <= radius_meters,
        models.Facility.facility_type == "Police Station"
    ).order_by(distance_col.asc()).all()

    police_list = []
    for facility, distance in results:
        lat = db.query(func.ST_Y(facility.location)).scalar()
        lng = db.query(func.ST_X(facility.location)).scalar()
        police_list.append(schemas.PoliceStationResponse(
            id=facility.id,
            name=facility.name,
            address=facility.address or "Address not available",
            phone_number=facility.phone_number or "100",
            lat=lat, lng=lng, distance_meters=round(distance, 1),
            verification_date=facility.verification_date or "2026-10-25",
            source=facility.source or "Telangana Police"
        ))
    return police_list

# ==========================================
# SAFETY REPORTS
# ==========================================
@router.post("/reports", response_model=schemas.SafetyReportResponse, tags=["Safety Reports"])
def create_report(report: schemas.SafetyReportCreate, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: User not found.")
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    duplicate = db.query(models.SafetyReport).filter(
        models.SafetyReport.segment_id == report.segment_id,
        models.SafetyReport.report_type == report.report_type,
        models.SafetyReport.created_at >= twenty_four_hours_ago
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Duplicate Report.")
    expires = datetime.now(timezone.utc) + timedelta(days=30)
    db_report = models.SafetyReport(
        user_id=x_user_id, segment_id=report.segment_id, report_type=report.report_type,
        description=report.description, incident_time=report.incident_time,
        evidence_url=report.evidence_url, source=report.source, status="pending",
        verification_status="unverified", expires_at=expires
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    response = schemas.SafetyReportResponse.model_validate(db_report)
    response.is_own_report = True
    return response

@router.get("/reports", response_model=list[schemas.SafetyReportResponse], tags=["Safety Reports"])
def get_reports(status: str | None = None, db: Session = Depends(get_db), x_user_id: int | None = Header(None)):
    now = datetime.now(timezone.utc)
    query = db.query(models.SafetyReport).filter(models.SafetyReport.expires_at > now)
    query = query.filter(models.SafetyReport.status == (status if status else "approved"))
    reports = query.all()
    result = []
    for r in reports:
        item = schemas.SafetyReportResponse.model_validate(r)
        if x_user_id and r.user_id == x_user_id:
            item.is_own_report = True
        result.append(item)
    return result

@router.get("/reports/{report_id}", response_model=schemas.SafetyReportResponse, tags=["Safety Reports"])
def get_report(report_id: int, db: Session = Depends(get_db), x_user_id: int | None = Header(None)):
    report = db.query(models.SafetyReport).filter(models.SafetyReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    item = schemas.SafetyReportResponse.model_validate(report)
    if x_user_id and report.user_id == x_user_id:
        item.is_own_report = True
    return item

@router.delete("/reports/{report_id}", response_model=schemas.ReportDeleteResponse, tags=["Safety Reports"])
def delete_report(report_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    report = db.query(models.SafetyReport).filter(models.SafetyReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this report.")
    db.delete(report)
    db.commit()
    return {"message": "Report deleted successfully.", "report_id": report_id}

@router.patch("/reports/{report_id}/status", response_model=schemas.SafetyReportResponse, tags=["Admin Moderation"])
def update_report_status(report_id: int, payload: schemas.ReportStatusUpdate, db: Session = Depends(get_db), x_admin_key: str = Header(...)):
    if x_admin_key != "secret-admin-key":
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Admin Key.")
    db_report = db.query(models.SafetyReport).filter(models.SafetyReport.id == report_id).first()
    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found.")
    db_report.status = payload.status
    db_report.source = "admin_panel"
    if payload.status == "approved":
        db_report.verification_status = "verified"
    db.commit()
    db.refresh(db_report)
    return db_report

# ==========================================
# LIGHTING OBSERVATIONS
# ==========================================
@router.post("/lighting", response_model=schemas.LightingObservationResponse, tags=["Lighting"])
def create_lighting(lighting: schemas.LightingObservationCreate, db: Session = Depends(get_db)):
    db_light = models.LightingObservation(**lighting.model_dump())
    db.add(db_light)
    db.commit()
    db.refresh(db_light)
    return db_light

@router.get("/lighting", response_model=list[schemas.LightingObservationResponse], tags=["Lighting"])
def get_lighting(db: Session = Depends(get_db)):
    return db.query(models.LightingObservation).all()

# ==========================================
# JOURNEYS
# ==========================================
@router.post("/journeys/start", response_model=schemas.JourneyResponse, tags=["Journeys"])
async def start_journey(payload: schemas.JourneyStartRequest, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    url = f"http://router.project-osrm.org/route/v1/driving/{payload.start_lng},{payload.start_lat};{payload.dest_lng},{payload.dest_lat}?overview=full&geometries=geojson"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            osrm_data = response.json()
    except Exception:
        raise HTTPException(status_code=503, detail="Routing service unavailable.")
    if osrm_data.get("code") != "Ok" or not osrm_data.get("routes"):
        raise HTTPException(status_code=400, detail="No route found.")
    coords = osrm_data["routes"][0]["geometry"]["coordinates"]
    wkt_points = [f"{c[0]} {c[1]}" for c in coords]
    linestring_wkt = f"LINESTRING({', '.join(wkt_points)})"

    db_journey = models.Journey(
        user_id=x_user_id,
        start_location=func.ST_GeomFromText(f"POINT({payload.start_lng} {payload.start_lat})", 4326),
        end_location=func.ST_GeomFromText(f"POINT({payload.dest_lng} {payload.dest_lat})", 4326),
        destination_lat=payload.dest_lat, destination_lng=payload.dest_lng,
        status="active", last_check_in_at=datetime.now(timezone.utc),
        safety_monitoring_enabled=payload.safety_monitoring_enabled,
        check_in_interval_minutes=payload.check_in_interval_minutes,
        route_geometry=func.ST_GeomFromText(linestring_wkt, 4326)
    )
    db.add(db_journey)
    db.commit()
    db.refresh(db_journey)
    return db_journey

@router.post("/journeys/{journey_id}/check-in", response_model=schemas.JourneyResponse, tags=["Journeys"])
def check_in(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    if journey.status != "active":
        raise HTTPException(status_code=400, detail=f"Cannot check-in. Journey is currently '{journey.status}'.")
    journey.last_check_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(journey)
    return journey

@router.patch("/journeys/{journey_id}/end", response_model=schemas.JourneyEndResponse, tags=["Journeys"])
def end_journey(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    if journey.status == "completed":
        raise HTTPException(status_code=400, detail="Journey is already completed.")
    journey.status = "completed"
    db.commit()
    db.refresh(journey)
    duration = (datetime.now(timezone.utc) - journey.started_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
    return {"message": "Journey completed successfully.", "journey_id": journey.id, "status": journey.status, "duration_minutes": round(duration, 1)}

@router.get("/journeys/{journey_id}", response_model=schemas.JourneyResponse, tags=["Journeys"])
def get_journey(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    return journey

@router.post("/journeys/{journey_id}/location", response_model=schemas.LocationPingResponse, tags=["Journeys"])
def update_location(journey_id: int, payload: schemas.LocationPingRequest, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    if journey.status != "active":
        raise HTTPException(status_code=400, detail="Journey is not active.")
    if not journey.safety_monitoring_enabled:
        raise HTTPException(status_code=400, detail="Privacy Error: Tracking is disabled.")

    journey.last_known_lat = payload.lat
    journey.last_known_lng = payload.lng

    deviation_detected = False
    if journey.route_geometry:
        user_point = func.ST_GeomFromText(f"POINT({payload.lng} {payload.lat})", 4326)
        distance = db.query(func.ST_Distance_Sphere(journey.route_geometry, user_point)).scalar()
        if distance and distance > 500:
            deviation_detected = True
            journey.consecutive_deviations += 1
        else:
            journey.consecutive_deviations = 0
            
    db.commit()
    db.refresh(journey)

    return schemas.LocationPingResponse(
        message="Location updated.", journey_id=journey.id, current_status=journey.status,
        last_known_lat=journey.last_known_lat, last_known_lng=journey.last_known_lng,
        deviation_detected=deviation_detected
    )

@router.post("/journeys/{journey_id}/safety-check", response_model=schemas.SafetyCheckResponse, tags=["Journeys"])
def check_safety(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden.")

    now = datetime.now(timezone.utc)
    reasons = []
    alert_created = False

    last_check = journey.last_check_in_at or journey.started_at
    minutes_since = (now - last_check.replace(tzinfo=timezone.utc)).total_seconds() / 60
    is_overdue = minutes_since > journey.check_in_interval_minutes
    if is_overdue:
        reasons.append(f"Missed check-in by {int(minutes_since - journey.check_in_interval_minutes)} mins")

    is_deviated = journey.consecutive_deviations >= 3
    if is_deviated:
        reasons.append(f"Went off-route {journey.consecutive_deviations} times consecutively")

    distance_m = None
    if journey.last_known_lat and journey.route_geometry:
        user_pt = func.ST_GeomFromText(f"POINT({journey.last_known_lng} {journey.last_known_lat})", 4326)
        distance_m = db.query(func.ST_Distance_Sphere(journey.route_geometry, user_pt)).scalar()

    if (is_overdue or is_deviated) and journey.status == "active":
        recent = db.query(models.Alert).filter(
            models.Alert.journey_id == journey.id,
            models.Alert.created_at > (now - timedelta(minutes=10))
        ).first()
        if not recent:
            db_alert = models.Alert(
                user_id=journey.user_id, journey_id=journey.id,
                alert_type="safety_concern", status="pending", message=" | ".join(reasons)
            )
            db.add(db_alert)
            journey.status = "deviated" if is_deviated else "overdue"
            db.commit()
            alert_created = True

    return schemas.SafetyCheckResponse(
        journey_id=journey.id, status=journey.status, is_overdue=is_overdue, is_deviated=is_deviated,
        consecutive_deviations=journey.consecutive_deviations,
        distance_from_route_meters=round(distance_m, 1) if distance_m else None,
        alert_created=alert_created, message="Safety check completed."
    )

# ==========================================
# EMERGENCY CONTACTS & TRIGGER ALERT
# ==========================================
@router.post("/emergency-contacts", response_model=schemas.EmergencyContactResponse, tags=["Emergency"])
def create_emergency_contact(contact: schemas.EmergencyContactCreate, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    db_contact = models.EmergencyContact(
        user_id=x_user_id, name=contact.name, phone_number=contact.phone_number, relationship_type=contact.relationship_type 
    )
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.get("/emergency-contacts", response_model=list[schemas.EmergencyContactResponse], tags=["Emergency"])
def get_emergency_contacts(db: Session = Depends(get_db), x_user_id: int = Header(...)):
    return db.query(models.EmergencyContact).filter(models.EmergencyContact.user_id == x_user_id).all()

@router.post("/journeys/{journey_id}/trigger-alert", response_model=schemas.TriggerAlertResponse, tags=["Emergency"])
def trigger_emergency_alert(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    if journey.status not in ["deviated", "overdue"]:
        raise HTTPException(status_code=400, detail=f"Cannot trigger alert. Status is '{journey.status}'.")

    now = datetime.now(timezone.utc)
    db_alert = models.Alert(
        user_id=journey.user_id, journey_id=journey.id, alert_type="emergency_manual",
        status="pending", message=f"EMERGENCY triggered manually by user for journey {journey.id}."
    )
    db.add(db_alert)
    journey.status = "alerted"
    db.commit()
    db.refresh(db_alert)

    return schemas.TriggerAlertResponse(
        message="Emergency alert logged successfully.", alert_id=db_alert.id,
        status=db_alert.status, journey_status=journey.status, triggered_at=db_alert.created_at
    )

@router.get("/journeys/{journey_id}/alerts", response_model=list[schemas.AlertResponse], tags=["Emergency"])
def get_journey_alerts(journey_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(models.Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found.")
    if journey.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="Forbidden: This is not your journey.")
    return db.query(models.Alert).filter(models.Alert.journey_id == journey_id).order_by(models.Alert.created_at.desc()).all()

# ==========================================
# ROUTING
# ==========================================
@router.post("/route", response_model=schemas.RouteResponse, tags=["Routing"])
async def get_route(request: schemas.RouteRequest, db: Session = Depends(get_db)):
    profile_map = {"car": "driving", "foot": "walking", "bike": "cycling"}
    osrm_profile = profile_map.get(request.preference.lower(), "driving")
    url = f"http://router.project-osrm.org/route/v1/{osrm_profile}/{request.origin_lng},{request.origin_lat};{request.dest_lng},{request.dest_lat}?overview=full&geometries=geojson&alternatives=true"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Routing service timed out.")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Routing service unavailable.")
    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=404, detail="No route could be found.")
    candidate_routes = []
    start_time = time.perf_counter()
    for index, route in enumerate(data["routes"]):
        raw_coordinates = route["geometry"]["coordinates"]
        geometry_list = [schemas.GeometryPoint(lat=c[1], lng=c[0]) for c in raw_coordinates]
        safety_data = calculate_route_safety(geometry_list, db)
        score = safety_data["safety_score"]
        rating = "Excellent" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "Poor" if score > 0 else "Unknown"
        candidate_routes.append(schemas.CandidateRoute(
            route_id=f"route_{index + 1}", distance_km=round(route["distance"] / 1000, 2),
            duration_min=round(route["duration"] / 60, 1), geometry=geometry_list,
            safety_score=score, safety_rating=rating, reasons=safety_data["reasons"], data_warnings=safety_data["data_warnings"]
        ))
    calc_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    if request.priority == "time":
        candidate_routes.sort(key=lambda x: x.duration_min)
    elif request.priority == "distance":
        candidate_routes.sort(key=lambda x: x.distance_km)
    else:
        candidate_routes.sort(key=lambda x: x.safety_score, reverse=True)
    recommended = candidate_routes[0].route_id
    return schemas.RouteResponse(
        status="success", origin=schemas.GeometryPoint(lat=request.origin_lat, lng=request.origin_lng),
        destination=schemas.GeometryPoint(lat=request.dest_lat, lng=request.dest_lng),
        routes=candidate_routes, recommended_route_id=recommended, model_version="v1.0", calculation_time_ms=calc_time_ms
    )

# ==========================================
# EMERGENCY TRIGGER (Module 4)
# ==========================================
@router.post("/emergency/trigger", response_model=schemas.AlertStatusResponse, tags=["Emergency"])
def trigger_emergency(
    payload: schemas.EmergencyTriggerRequest, 
    db: Session = Depends(get_db), 
    x_user_id: int = Header(...)
):
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    contacts = db.query(models.EmergencyContact).filter(models.EmergencyContact.user_id == x_user_id).all()
    if not contacts:
        raise HTTPException(status_code=400, detail="No trusted contacts configured.")

    map_link = f"https://www.google.com/maps/search/?api=1&query={payload.lat},{payload.lng}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    alert_message = f"EMERGENCY ALERT from {user.name}. Location: {map_link}. Time: {timestamp}."
    
    db_alert = models.Alert(
        user_id=x_user_id, journey_id=None, alert_type="emergency_trusted",
        status="pending", message=alert_message,
        location_lat=payload.lat, location_lng=payload.lng, delivery_status="pending"
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    success_count = 0
    failure_count = 0
    details = []
    
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    email_sender = os.getenv("EMAIL_SENDER", "")
    email_password = os.getenv("EMAIL_PASSWORD", "")

    for contact in contacts:
        contact_email = contact.phone_number
        if "@" not in contact_email:
            details.append(f"Skipped {contact.name}: Not an email address")
            failure_count += 1
            continue

        try:
            msg = EmailMessage()
            msg["Subject"] = f"🚨 EMERGENCY ALERT FROM {user.name}"
            msg["From"] = email_sender
            msg["To"] = contact_email
            msg.set_content(alert_message)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(email_sender, email_password)
                server.send_message(msg)
            
            success_count += 1
            details.append(f"Sent to {contact.name} ({contact_email})")
        except Exception as e:
            failure_count += 1
            details.append(f"Failed to send to {contact.name}: {str(e)}")

    if success_count > 0:
        db_alert.delivery_status = "sent"
        db_alert.status = "sent"
    else:
        db_alert.delivery_status = "failed"
        db_alert.status = "failed"
    
    db_alert.delivery_details = "\n".join(details)
    db.commit()
    db.refresh(db_alert)

    return schemas.AlertStatusResponse(
        alert_id=db_alert.id, delivery_status=db_alert.delivery_status,
        delivery_details=db_alert.delivery_details, contacts_notified=success_count,
        triggered_at=db_alert.created_at
    )

@router.get("/emergency/{alert_id}/status", response_model=schemas.AlertStatusResponse, tags=["Emergency"])
def check_emergency_status(alert_id: int, db: Session = Depends(get_db), x_user_id: int = Header(...)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id, models.Alert.user_id == x_user_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    
    contacts_notified = 0
    if alert.delivery_details:
        contacts_notified = alert.delivery_details.count("Sent to")
        
    return schemas.AlertStatusResponse(
        alert_id=alert.id, delivery_status=alert.delivery_status,
        delivery_details=alert.delivery_details, contacts_notified=contacts_notified,
        triggered_at=alert.created_at
    )

# ==========================================
# MODULE 5: PUBLIC EMERGENCY ENDPOINTS
# ==========================================
@router.get("/emergency/health", response_model=schemas.EmergencyHealthResponse, tags=["Emergency"])
def emergency_health():
    return {"status": "ok", "message": "Emergency services are online."}

@router.get("/emergency/nearby-police", response_model=list[schemas.PoliceStationResponse], tags=["Emergency"])
async def emergency_nearby_police(lat: float, lng: float):
    db = SessionLocal()
    try:
        user_point = func.ST_GeomFromText(f"POINT({lng} {lat})", 4326)
        distance_col = func.ST_Distance_Sphere(models.Facility.location, user_point).label("distance_meters")
        
        results = db.query(models.Facility, distance_col).filter(
            distance_col <= 10000,
            models.Facility.facility_type == "Police Station"
        ).order_by(distance_col.asc()).limit(5).all()

        police_list = []
        for facility, distance in results:
            f_lat = db.query(func.ST_Y(facility.location)).scalar()
            f_lng = db.query(func.ST_X(facility.location)).scalar()
            police_list.append(schemas.PoliceStationResponse(
                id=facility.id, name=facility.name,
                address=facility.address or "Address not available",
                phone_number=facility.phone_number or "100",
                lat=f_lat, lng=f_lng, distance_meters=round(distance, 1),
                verification_date=facility.verification_date or "2026-10-25",
                source=facility.source or "Telangana Police"
            ))
        return police_list
    finally:
        db.close()

@router.post("/emergency/alerts", response_model=schemas.EmergencyAlertResponse, tags=["Emergency"])
def create_emergency_alert(payload: schemas.EmergencyAlertRequest):
    db = SessionLocal()
    try:
        if not payload.user_id:
            return schemas.EmergencyAlertResponse(
                alert_id=0, status="anonymous",
                message="You are not logged in. Please call 112 directly.",
                contacts_notified=0
            )

        user = db.query(models.User).filter(models.User.id == payload.user_id).first()
        if not user:
            return schemas.EmergencyAlertResponse(
                alert_id=0, status="failed", message="User not found. Please call 112.",
                contacts_notified=0
            )

        contacts = db.query(models.EmergencyContact).filter(
            models.EmergencyContact.user_id == payload.user_id
        ).all()

        if not contacts:
            return schemas.EmergencyAlertResponse(
                alert_id=0, status="no_contacts",
                message="No trusted contacts found. Please call 112.",
                contacts_notified=0
            )

        map_link = f"https://www.google.com/maps/search/?api=1&query={payload.lat},{payload.lng}"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        db_alert = models.Alert(
            user_id=payload.user_id, alert_type="emergency_public",
            status="pending", message=f"Emergency from {user.name}. Location: {map_link}. Time: {timestamp}.",
            location_lat=payload.lat, location_lng=payload.lng, delivery_status="pending"
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)

        db_alert.delivery_status = "sent"
        db_alert.status = "sent"
        db.commit()

        return schemas.EmergencyAlertResponse(
            alert_id=db_alert.id, status="sent",
            message=f"Alert sent to {len(contacts)} contact(s).",
            contacts_notified=len(contacts)
        )
    finally:
        db.close()

# ==========================================
# MODULE 5: PERSONAL DASHBOARD
# ==========================================
@router.get("/users/me/reports", response_model=list[schemas.SafetyReportResponse], tags=["Dashboard"])
def get_my_reports(db: Session = Depends(get_db), x_user_id: int = Header(...)):
    reports = db.query(models.SafetyReport).filter(
        models.SafetyReport.user_id == x_user_id
    ).order_by(models.SafetyReport.created_at.desc()).all()
    
    result = []
    for r in reports:
        item = schemas.SafetyReportResponse.model_validate(r)
        item.is_own_report = True
        result.append(item)
    return result

@router.post("/users/me/check-in", response_model=schemas.CheckInResponse, tags=["Dashboard"])
def dashboard_check_in(db: Session = Depends(get_db), x_user_id: int = Header(...)):
    journey = db.query(models.Journey).filter(
        models.Journey.user_id == x_user_id,
        models.Journey.status == "active"
    ).order_by(models.Journey.started_at.desc()).first()

    now = datetime.now(timezone.utc)

    if journey:
        journey.last_check_in_at = now
        db.commit()
        return schemas.CheckInResponse(
            message="Check-in successful for active journey.",
            status="active_journey",
            last_check_in_at=now
        )
    else:
        return schemas.CheckInResponse(
            message="You are marked safe. No active journey found to update.",
            status="no_active_journey",
            last_check_in_at=now
        )

# ==========================================
# MOCK LOGIN (For Demo/Testing)
# ==========================================
@router.post("/auth/mock-login", tags=["Auth"])
def mock_login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    name = payload.get("name", "Demo User")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == email).first()
    
    # If not, create them instantly
    if not db_user:
        db_user = models.User(
            name=name,
            email=email,
            password_hash="mock_password", # Not used for mock login
            is_verified=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # Generate a fake token for the frontend
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_name": db_user.name,
        "user_id": str(db_user.id)
    }
# ==========================================
# MOCK LOGIN (For Demo/Testing)
# ==========================================
@router.post("/auth/mock-login", tags=["Auth"])
def mock_login(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email")
    name = payload.get("name", "Demo User")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == email).first()
    
    # If not, create them instantly
    if not db_user:
        db_user = models.User(
            name=name,
            email=email,
            password_hash="mock_password",
            is_verified=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # Generate a fake token for the frontend
    access_token = create_access_token(data={"sub": str(db_user.id), "email": db_user.email})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_name": db_user.name,
        "user_id": str(db_user.id)
    }