from database import SessionLocal
from services import calculate_route_safety

db = SessionLocal()

# A route that passes directly through MG Road (where you saved the Harassment report)
# and then continues to Park Lane (where you saved the broken light).
real_route = [
    {"lat": 17.3850, "lng": 78.4867},  # MG Road start
    {"lat": 17.3875, "lng": 78.4883},  # midpoint
    {"lat": 17.3900, "lng": 78.4900},  # MG Road end
    {"lat": 17.3950, "lng": 78.4950},  # Park Lane start
    {"lat": 17.3980, "lng": 78.4980},  # Park Lane end
]

print("Calculating safety for test route...")
result = calculate_route_safety(real_route, db)
print("\n=== RESULT ===")
print(f"Safety Score: {result['safety_score']}")
print(f"Reasons: {result['reasons']}")
print(f"Warnings: {result['data_warnings']}")