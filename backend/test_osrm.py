import requests
import json

# Coordinates: Longitude, Latitude
# Example: Hitech City to Gachibowli in Hyderabad
origin_lon, origin_lat = 78.3867, 17.4483
dest_lon, dest_lat = 78.3489, 17.4407

# Build the URL
url = f"http://router.project-osrm.org/route/v1/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson&alternatives=true"

print(f"Calling OSRM: {url}\n")

try:
    # Make the request
    response = requests.get(url, timeout=10)
    response.raise_for_status() # Throws an error if the request fails
    
    # Parse the JSON
    data = response.json()
    
    # Check if OSRM found any routes
    if data.get("code") == "Ok":
        routes = data.get("routes", [])
        print(f"✅ Success! Found {len(routes)} route(s).\n")
        
        for i, route in enumerate(routes):
            print(f"--- Route {i+1} ---")
            print(f"Distance: {route['distance']} meters ({route['distance'] / 1000:.2f} km)")
            print(f"Duration: {route['duration']} seconds ({route['duration'] / 60:.1f} mins)")
            
            # Look at the geometry (first 2 points only, so we don't flood the terminal)
            coordinates = route['geometry']['coordinates']
            print(f"Geometry points: {len(coordinates)}")
            print(f"First point (lon, lat): {coordinates[0]}")
            print(f"Last point (lon, lat):  {coordinates[-1]}\n")
    else:
        print(f"❌ OSRM Error: {data.get('code')} - {data.get('message')}")

except requests.exceptions.Timeout:
    print("❌ Error: The request timed out. OSRM might be down.")
except requests.exceptions.RequestException as e:
    print(f"❌ Network Error: {e}")