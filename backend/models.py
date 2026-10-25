from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    reports = relationship("SafetyReport", back_populates="user")
    journeys = relationship("Journey", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    emergency_contacts = relationship("EmergencyContact", back_populates="user")

class RoadSegment(Base):
    __tablename__ = "road_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    start_location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    end_location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)

    safety_reports = relationship("SafetyReport", back_populates="segment")
    lighting_observations = relationship("LightingObservation", back_populates="segment")

class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    facility_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    
    # Module 3 Fields
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    verification_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")

class SafetyReport(Base):
    __tablename__ = "safety_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("road_segments.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Module 2 Fields
    incident_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="pending")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="mobile_app")
    verification_status: Mapped[str] = mapped_column(String(20), default="unverified")

    user = relationship("User", back_populates="reports")
    segment = relationship("RoadSegment", back_populates="safety_reports")

class LightingObservation(Base):
    __tablename__ = "lighting_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("road_segments.id"), nullable=False)
    is_broken: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    segment = relationship("RoadSegment", back_populates="lighting_observations")

class Journey(Base):
    __tablename__ = "journeys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    end_location: Mapped[str] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active") 
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    last_check_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_known_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_known_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_geometry: Mapped[str | None] = mapped_column(Geometry(geometry_type='LINESTRING', srid=4326), nullable=True)
    safety_monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    destination_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    consecutive_deviations: Mapped[int] = mapped_column(Integer, default=0)

    user = relationship("User", back_populates="journeys")

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    journey_id: Mapped[int | None] = mapped_column(ForeignKey("journeys.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), default="manual") 
    status: Mapped[str] = mapped_column(String(20), default="pending") 
    
    # Module 4 Fields
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(50), default="pending")
    delivery_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    user = relationship("User", back_populates="alerts")

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(100), nullable=False) # Can hold email or phone
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Module 5 Field
    verification_status: Mapped[str] = mapped_column(String(50), default="unverified")

    user = relationship("User", back_populates="emergency_contacts")