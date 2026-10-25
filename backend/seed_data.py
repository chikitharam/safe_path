from database import SessionLocal, engine
import models
from geoalchemy2.elements import WKTElement
from datetime import datetime

def seed_database():
    db = SessionLocal()
    print("🌱 Starting database seeding...")

    try:
        # ---------------------------------------------------------
        # 1. USERS
        # ---------------------------------------------------------
        print("Creating Users...")
        demo_user = models.User(
            name="Demo User",
            email="demo@safepath.com",
            password_hash="hashed_password_123"
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)

        # ---------------------------------------------------------
        # 2. ROAD SEGMENTS (Spatial Data)
        # ---------------------------------------------------------
        print("Creating Road Segments...")
        # WKTElement converts a string like "POINT(lng lat)" into a true spatial POINT
        segment_1 = models.RoadSegment(
            name="MG Road - Main Stretch",
            start_location=WKTElement('POINT(78.4867 17.3850)', srid=4326),
            end_location=WKTElement('POINT(78.4900 17.3900)', srid=4326)
        )
        segment_2 = models.RoadSegment(
            name="Park Lane - Dark Alley",
            start_location=WKTElement('POINT(78.4950 17.3950)', srid=4326),
            end_location=WKTElement('POINT(78.4980 17.3980)', srid=4326)
        )
        db.add_all([segment_1, segment_2])
        db.commit()
        db.refresh(segment_1)
        db.refresh(segment_2)

        # ---------------------------------------------------------
        # 3. FACILITIES (Spatial Data)
        # ---------------------------------------------------------
        print("Creating Facilities...")
        facility_1 = models.Facility(
            facility_type="Police Station",
            name="Central Police HQ",
            location=WKTElement('POINT(78.4800 17.3800)', srid=4326)
        )
        facility_2 = models.Facility(
            facility_type="CCTV Camera",
            name="CCTV on MG Road",
            location=WKTElement('POINT(78.4880 17.3870)', srid=4326)
        )
        db.add_all([facility_1, facility_2])
        db.commit()

        # ---------------------------------------------------------
        # 4. SAFETY REPORTS
        # ---------------------------------------------------------
        print("Creating Safety Reports...")
        report_1 = models.SafetyReport(
            user_id=demo_user.id,
            segment_id=segment_1.id,
            report_type="Harassment",
            description="Group of men catcalling near the bus stop."
        )
        report_2 = models.SafetyReport(
            user_id=demo_user.id,
            segment_id=segment_2.id,
            report_type="Theft",
            description="Phone was snatched while walking down this alley."
        )
        db.add_all([report_1, report_2])
        db.commit()

        # ---------------------------------------------------------
        # 5. LIGHTING OBSERVATIONS
        # ---------------------------------------------------------
        print("Creating Lighting Observations...")
        lighting_1 = models.LightingObservation(
            segment_id=segment_2.id,
            is_broken=True,
            notes="Two street lights are out, very dark at night."
        )
        db.add(lighting_1)
        db.commit()

        # ---------------------------------------------------------
        # 6. JOURNEYS (Spatial Data)
        # ---------------------------------------------------------
        print("Creating Journeys...")
        journey_1 = models.Journey(
            user_id=demo_user.id,
            start_location=WKTElement('POINT(78.4867 17.3850)', srid=4326),
            end_location=WKTElement('POINT(78.4980 17.3980)', srid=4326),
            status="completed"
        )
        db.add(journey_1)
        db.commit()

        # ---------------------------------------------------------
        # 7. ALERTS
        # ---------------------------------------------------------
        print("Creating Alerts...")
        alert_1 = models.Alert(
            user_id=demo_user.id,
            message="Warning: High number of theft reports on Park Lane."
        )
        db.add(alert_1)
        db.commit()

        print("✅ Database seeding completed successfully!")
        print(f"-> Inserted User ID: {demo_user.id}")
        print(f"-> Inserted Segment IDs: {segment_1.id}, {segment_2.id}")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()