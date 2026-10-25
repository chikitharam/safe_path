const findButton = document.getElementById("findRoute");
const results = document.getElementById("results");
const routeCards = document.getElementById("routeCards");
const clearButton = document.getElementById("clearRoute");

const map = L.map("map").setView([12.9716, 77.5946], 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

let markers = [];
let routeLines = [];
let selectedPoints = [];

map.on("contextmenu", function(e) {
    e.originalEvent.preventDefault();
    if (!localStorage.getItem("user_id")) {
        alert("🔒 Please log in first.");
        return;
    }
    const typePrompt = prompt("1. Harassment\n2. Stalking\n3. Suspicious Behaviour\n4. Poor Lighting\n5. Isolated Road\n6. Theft\n7. Accident\n8. Other\n\nEnter a number (1-8):");
    if (!typePrompt) return;
    const categoryMap = { "1": "Harassment", "2": "Stalking", "3": "Suspicious Behaviour", "4": "Poor Lighting", "5": "Isolated Road", "6": "Theft", "7": "Accident", "8": "Other" };
    const category = categoryMap[typePrompt] || "Other";
    const description = prompt("Describe what happened:");
    const evidence = prompt("Link to evidence (optional):");

    fetch("http://127.0.0.1:8000/api/v1/reports", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-User-Id": localStorage.getItem("user_id") },
        body: JSON.stringify({ segment_id: 1, report_type: category, description, evidence_url: evidence, source: "web" })
    }).then(res => {
        if (res.ok) alert("✅ Report submitted!");
        else alert("❌ Failed to submit.");
    });
});

map.on("click", function (event) {
    if (selectedPoints.length >= 2) {
        markers.forEach(marker => map.removeLayer(marker));
        routeLines.forEach(line => map.removeLayer(line));
        markers = []; routeLines = []; selectedPoints = []; routeCards.innerHTML = ""; results.hidden = true;
    }
    const point = [event.latlng.lat, event.latlng.lng];
    selectedPoints.push(point);
    const marker = L.marker(point).addTo(map);
    if (selectedPoints.length === 1) {
        marker.bindPopup("Starting point").openPopup();
        document.getElementById("start").value = point[0].toFixed(5) + ", " + point[1].toFixed(5);
    } else {
        marker.bindPopup("Destination").openPopup();
        document.getElementById("destination").value = point[0].toFixed(5) + ", " + point[1].toFixed(5);
    }
    markers.push(marker);
});

async function getCoordinates(location) {
    const coordinateMatch = location.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (coordinateMatch) return [Number(coordinateMatch[1]), Number(coordinateMatch[2])];
    const response = await fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(location));
    const data = await response.json();
    if (!data.length) throw new Error('Location not found.');
    return [Number(data[0].lat), Number(data[0].lon)];
}

findButton.addEventListener("click", async function () {
    const startText = document.getElementById("start").value.trim();
    const destinationText = document.getElementById("destination").value.trim();
    if (!startText || !destinationText) { alert("Please enter both locations."); return; }

    findButton.disabled = true;
    document.getElementById("status").textContent = "Searching...";

    try {
        const start = await getCoordinates(startText);
        const destination = await getCoordinates(destinationText);
        const response = await fetch("http://127.0.0.1:8000/api/v1/route", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ origin_lat: start[0], origin_lng: start[1], dest_lat: destination[0], dest_lng: destination[1], preference: "car", priority: "safety" })
        });
        if (!response.ok) throw new Error("Backend error");
        const data = await response.json();

        markers.forEach(m => map.removeLayer(m));
        routeLines.forEach(l => map.removeLayer(l));
        markers = []; routeLines = []; selectedPoints = [];

        markers.push(L.marker(start).addTo(map).bindPopup("Start"));
        markers.push(L.marker(destination).addTo(map).bindPopup("End"));

        data.routes.forEach((route, index) => {
            const coords = route.geometry.map(p => [p.lat, p.lng]);
            const line = L.polyline(coords, { color: index === 0 ? "#147d64" : "#e49b32", weight: index === 0 ? 6 : 4 }).addTo(map);
            routeLines.push(line);

            const card = document.createElement("article");
            card.className = "route-card";
            card.innerHTML = `<h3>${index === 0 ? "⭐ Recommended" : "Alternative"}</h3><p>Distance: ${route.distance_km} km</p><p>Time: ${route.duration_min} mins</p><p style="color:${route.safety_score >= 60 ? '#147d64' : '#c0392b'}; font-weight:bold;">🛡️ Safety: ${route.safety_score}/100</p>`;
            routeCards.appendChild(card);
        });

        results.hidden = false;
        document.getElementById("status").textContent = "✅ Route found!";
    } catch (error) {
        document.getElementById("status").textContent = "❌ " + error.message;
    } finally {
        findButton.disabled = false;
    }
});

clearButton.addEventListener("click", function () {
    document.getElementById("start").value = "";
    document.getElementById("destination").value = "";
    markers.forEach(m => map.removeLayer(m));
    routeLines.forEach(l => map.removeLayer(l));
    markers = []; routeLines = []; selectedPoints = []; routeCards.innerHTML = "";
    results.hidden = true;
    document.getElementById("status").textContent = "";
});