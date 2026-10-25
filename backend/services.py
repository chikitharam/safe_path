from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta, timezone
import models


def calculate_route_safety(route_coordinates: list, db: Session):
    """
    Calculates a safety score for a route based on nearby safety reports
    and broken street lights.
    
    Optimized: Uses a single SQL query with OR conditions instead of
    looping through every route point (reduces 500 queries to 1).
    """
    search_radius_meters = 50.0

    # 1. Build a list of POINT geometries from the route coordinates
    point_geoms = []
    for point in route_coordinates:
        # Support both dicts (from test scripts) and Pydantic objects (from API)
        if isinstance(point, dict):
            lng, lat = point['lng'], point['lat']
        else:
            lng, lat = point.lng, point.lat

        point_geoms.append(func.ST_GeomFromText(f"POINT({lng} {lat})", 4326))

    # If route has no points, return early with a warning
    if not point_geoms:
        return {
            "safety_score": 100.0,
            "reasons": ["No safety incidents reported nearby."],
            "data_warnings": ["Missing Data: Route geometry was empty."]
        }

    # 2. Build OR conditions: check every 5th point to reduce query size
    # (Route is dense enough that this doesn't miss reports)
    report_conditions = [
        func.ST_Distance_Sphere(models.RoadSegment.start_location, geom) <= search_radius_meters
        for geom in point_geoms[::5]
    ]

    # 3. Single query for safety reports
    nearby_reports = db.query(models.SafetyReport).join(
        models.RoadSegment, models.SafetyReport.segment_id == models.RoadSegment.id
    ).filter(or_(*report_conditions)).all()

    # 4. Single query for broken lighting
    nearby_lighting = db.query(models.LightingObservation).join(
        models.RoadSegment, models.LightingObservation.segment_id == models.RoadSegment.id
    ).filter(
        or_(*report_conditions),
        models.LightingObservation.is_broken == True
    ).all()

    # 5. Remove duplicates (a report might be near multiple points)
    nearby_reports = list({r.id: r for r in nearby_reports}.values())
    nearby_lighting = list({l.id: l for l in nearby_lighting}.values())

    # 6. Apply the Math Formula (with Freshness Check)
    score = 100.0
    reasons = []
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    def get_point_deduction(report_type, weight):
        deduction = 0
        for r in nearby_reports:
            if r.report_type == report_type:
                # If report is older than 6 months, only deduct half
                if r.created_at and r.created_at.replace(tzinfo=timezone.utc) < six_months_ago:
                    deduction += (weight * 0.5)
                else:
                    deduction += weight
        return deduction

    harassment_deduction = get_point_deduction("Harassment", 20)
    theft_deduction = get_point_deduction("Theft", 15)
    accident_deduction = get_point_deduction("Accident", 10)

    if harassment_deduction > 0:
        score -= harassment_deduction
        reasons.append(f"Harassment reports nearby (-{harassment_deduction} pts)")

    if theft_deduction > 0:
        score -= theft_deduction
        reasons.append(f"Theft reports nearby (-{theft_deduction} pts)")

    if accident_deduction > 0:
        score -= accident_deduction
        reasons.append(f"Accidents reported nearby (-{accident_deduction} pts)")

    if len(nearby_lighting) > 0:
        light_deduction = len(nearby_lighting) * 5
        score -= light_deduction
        reasons.append(f"{len(nearby_lighting)} broken street light(s) (-{light_deduction} pts)")

    # Ensure score doesn't drop below 0
    score = max(0.0, score)

    # 7. Data Completeness Warnings
    total_data_points = len(nearby_reports) + len(nearby_lighting)
    data_warnings = []

    if total_data_points == 0:
        data_warnings.append(
            "Missing Data: No safety reports or lighting observations found on this route. "
            "Score may be unreliable."
        )
    elif total_data_points < 3:
        data_warnings.append(
            "Low Data: Very few reports found. Score might not reflect the full picture."
        )

    # 8. Return Result
    return {
        "safety_score": round(score, 1),
        "reasons": reasons if reasons else ["No safety incidents reported nearby."],
        "data_warnings": data_warnings
    }