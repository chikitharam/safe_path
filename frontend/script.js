// ==========================================
// GLOBAL VARIABLES & MAP SETUP
// ==========================================
const findButton = document.getElementById("findRoute");
const results = document.getElementById("results");
const routeCards = document.getElementById("routeCards");
const clearButton = document.getElementById("clearRoute");

// We check if the map exists (it won't on dashboard/index pages)
let map;
if (document.getElementById("map")) {
    map = L.map("map").setView([12.9716, 77.5946], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

let markers = [];
let routeLines = [];
let selectedPoints = [];

// ==========================================
// MODULE 1: AUTHENTICATION LOGIC (For index.html)
// ==========================================
const authSection = document.getElementById("auth-section");
const mainApp = document.getElementById("mainApp");
const globalLogoutBtn = document.getElementById("globalLogoutBtn");
const userNameDisplay = document.getElementById("userNameDisplay");
const authMessage = document.getElementById("authMessage");

function showApp() {
    if (authSection) authSection.style.display = "none";
    if (mainApp) mainApp.style.display = "block";
    if (globalLogoutBtn) globalLogoutBtn.style.display = "block";
    if (userNameDisplay) userNameDisplay.textContent = localStorage.getItem("user_name") || "User";
    loadDashboard(); // Load the data
}

function showLogin() {
    if (authSection) authSection.style.display = "block";
    if (mainApp) mainApp.style.display = "none";
    if (globalLogoutBtn) globalLogoutBtn.style.display = "none";
}

// Check login status on load
if (localStorage.getItem("user_id")) {
    showApp();
} else {
    showLogin();
}

// Login button
const loginBtn = document.getElementById("loginBtn");
if (loginBtn) {
    loginBtn.addEventListener("click", async function() {
        const name = document.getElementById("signupName").value || "Demo User";
        const email = document.getElementById("signupEmail").value;

        if (!email) {
            if (authMessage) {
                authMessage.style.color = "red";
                authMessage.textContent = "Please enter an email.";
            }
            return;
        }

        try {
            const response = await fetch("http://127.0.0.1:8000/api/v1/auth/mock-login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email })
            });
            const data = await response.json();
            if (response.ok) {
                localStorage.setItem("user_name", data.user_name);
                localStorage.setItem("user_id", data.user_id);
                showApp();
            } else {
                if (authMessage) {
                    authMessage.style.color = "red";
                    authMessage.textContent = "❌ " + (data.detail || "Login failed.");
                }
            }
        } catch (e) {
            if (authMessage) {
                authMessage.style.color = "red";
                authMessage.textContent = "❌ Network error.";
            }
        }
    });
}

// Logout button
const logoutBtn = document.getElementById("globalLogoutBtn");
if (logoutBtn) {
    logoutBtn.addEventListener("click", function() {
        localStorage.clear();
        window.location.reload();
    });
}

// ==========================================
// MODULE 4: EMERGENCY ALERT BUTTON (For emergency.html)
// ==========================================
const emergencyBtn = document.getElementById("emergencyBtn");
if (emergencyBtn) {
    emergencyBtn.addEventListener("click", async function() {
        if (!localStorage.getItem("user_id")) {
            alert("🔒 Please sign up or log in first to use the emergency feature.");
            return;
        }

        const confirmAlert = confirm("🚨 Are you sure you want to trigger an emergency alert? This will notify your trusted contacts.");
        if (!confirmAlert) return;

        const btn = document.getElementById("emergencyBtn");
        const originalText = btn.innerHTML;
        btn.innerHTML = "⏳ Getting location...";
        btn.disabled = true;

        if (!navigator.geolocation) {
            alert("❌ Geolocation is not supported by your browser.");
            btn.innerHTML = originalText;
            btn.disabled = false;
            return;
        }

        navigator.geolocation.getCurrentPosition(async function(position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            btn.innerHTML = "⏳ Sending alert...";

            try {
                const response = await fetch("http://127.0.0.1:8000/api/v1/emergency/trigger", {
                    method: "POST",
                    headers: { 
                        "Content-Type": "application/json",
                        "X-User-Id": localStorage.getItem("user_id")
                    },
                    body: JSON.stringify({ lat: lat, lng: lng })
                });

                const data = await response.json();

                if (response.ok) {
                    if (data.delivery_status === "sent") {
                        alert(`✅ Emergency alert SENT successfully!\n\n${data.contacts_notified} trusted contact(s) have been notified with your location.\n\nDetails:\n${data.delivery_details}`);
                    } else if (data.delivery_status === "failed") {
                        alert(`❌ Alert FAILED to send!\n\nDetails:\n${data.delivery_details}\n\nPlease call 112 directly.`);
                    } else {
                        alert(`⏳ Alert is PENDING. The system is still processing your request.`);
                    }
                } else {
                    alert("❌ Error: " + (data.detail || "Could not trigger the alert. Please call 112."));
                }
            } catch (e) {
                alert("❌ Network error. Please call 112 immediately.");
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }, function(error) {
            alert("❌ Could not get your location. Please allow location access in your browser. Error: " + error.message);
            btn.innerHTML = originalText;
            btn.disabled = false;
        });
    });
}

// ==========================================
// MODULE 3: HELPLINES & POLICE STATIONS (For help.html)
// ==========================================
const helplineGrid = document.getElementById("helplineGrid");
if (helplineGrid) {
    const helplines = [
        { name: "Emergency (ERSS)", number: "112", desc: "Police, Fire, Health" },
        { name: "Police Helpline", number: "100", desc: "Direct Police" },
        { name: "Women Helpline", number: "181", desc: "Domestic Violence" },
        { name: "Cyber Crime", number: "1930", desc: "Online Fraud" },
        { name: "Child Helpline", number: "1098", desc: "Child Safety" },
        { name: "Ambulance", number: "102", desc: "Medical Emergency" }
    ];

    helplines.forEach(h => {
        const card = document.createElement("div");
        card.style.background = "#f4f7f6";
        card.style.padding = "12px";
        card.style.borderRadius = "8px";
        card.style.borderLeft = "4px solid #c0392b";
        
        card.innerHTML = `
            <strong style="display:block; color:#18332d;">${h.name}</strong>
            <a href="tel:${h.number}" style="display:block; font-size:20px; color:#c0392b; font-weight:bold; text-decoration:none; margin: 5px 0;">
                📞 ${h.number}
            </a>
            <span style="font-size:12px; color:#60716b;">${h.desc}</span>
        `;
        helplineGrid.appendChild(card);
    });
}

async function loadNearbyPolice(lat, lng) {
    if (!map) return;
    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/facilities/police-nearby", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: lat, lng: lng, radius_km: 10 })
        });
        
        const stations = await response.json();
        
        stations.forEach(station => {
            const policeIcon = L.divIcon({
                className: 'police-marker',
                html: '🚓',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            const marker = L.marker([station.lat, station.lng], { icon: policeIcon }).addTo(map);
            
            marker.bindPopup(`
                <strong>🚓 ${station.name}</strong><br>
                <span style="font-size:12px;">${station.distance_meters}m away</span><br>
                <a href="tel:${station.phone_number}" style="color:#147d64; font-weight:bold; display:block; margin-top:5px;">
                    📞 Call Station
                </a>
                <a href="https://www.google.com/maps/dir/?api=1&destination=${station.lat},${station.lng}" target="_blank" style="color:#147d64; display:block; margin-top:3px;">
                    🧭 Get Directions
                </a>
                <small style="color:#888; display:block; margin-top:5px;">Source: ${station.source} (${station.verification_date})</small>
            `);
        });
    } catch (e) {
        console.log("Could not load police stations:", e);
    }
}

// ==========================================
// MODULE 2: RIGHT-CLICK TO REPORT (For route.html)
// ==========================================
if (map) {
    map.on("contextmenu", function(e) {
        e.originalEvent.preventDefault();
        if (!localStorage.getItem("user_id")) {
            alert("🔒 Please sign up or log in first to submit a report.");
            return;
        }

        const typePrompt = prompt(
            "Report an incident at this location:\n\n" +
            "1. Harassment\n2. Stalking\n3. Suspicious Behaviour\n" +
            "4. Poor Lighting\n5. Isolated Road\n6. Theft\n7. Accident\n8. Other\n\n" +
            "Enter a number (1-8):"
        );
        if (!typePrompt) return;

        const categoryMap = {
            "1": "Harassment", "2": "Stalking", "3": "Suspicious Behaviour",
            "4": "Poor Lighting", "5": "Isolated Road", "6": "Theft",
            "7": "Accident", "8": "Other"
        };
        const category = categoryMap[typePrompt] || "Other";
        const description = prompt("Describe what happened (optional):");
        const evidence = prompt("Paste a link to photo/video evidence (optional):");

        submitReport(e.latlng.lat, e.latlng.lng, category, description, evidence);
    });
}

async function submitReport(lat, lng, category, description, evidence) {
    const userId = localStorage.getItem("user_id");
    const payload = {
        segment_id: 1, report_type: category, description: description,
        incident_time: new Date().toISOString(), evidence_url: evidence, source: "web"
    };

    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/reports", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-User-Id": userId },
            body: JSON.stringify(payload)
        });
        if (response.ok) {
            alert("✅ Report submitted successfully!");
        } else {
            const err = await response.json();
            alert("❌ Failed: " + (err.detail || "Please try again."));
        }
    } catch (e) {
        alert("❌ Network error.");
    }
}

// ==========================================
// ROUTING LOGIC (For route.html)
// ==========================================
if (map) {
    map.on("click", function (event) {
        if (selectedPoints.length >= 2) {
            markers.forEach(marker => map.removeLayer(marker));
            routeLines.forEach(line => map.removeLayer(line));
            markers = [];
            routeLines = [];
            selectedPoints = [];
            if (routeCards) routeCards.innerHTML = "";
            if (results) results.hidden = true;
        }

        const point = [event.latlng.lat, event.latlng.lng];
        selectedPoints.push(point);
        const marker = L.marker(point).addTo(map);

        if (selectedPoints.length === 1) {
            marker.bindPopup("Starting point").openPopup();
            document.getElementById("start").value = point[0].toFixed(5) + ", " + point[1].toFixed(5);
            document.getElementById("mapStatus").textContent = "📍 Starting point selected!";
            loadNearbyPolice(point[0], point[1]);
        } else {
            marker.bindPopup("Destination").openPopup();
            document.getElementById("destination").value = point[0].toFixed(5) + ", " + point[1].toFixed(5);
            document.getElementById("mapStatus").textContent = "✅ Destination selected!";
        }
        markers.push(marker);
    });
}

async function getCoordinates(location) {
    const coordinateMatch = location.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (coordinateMatch) {
        return [Number(coordinateMatch[1]), Number(coordinateMatch[2])];
    }
    const response = await fetch("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + encodeURIComponent(location));
    const data = await response.json();
    if (!data.length) throw new Error('Location not found.');
    return [Number(data[0].lat), Number(data[0].lon)];
}

async function getRoutes(start, destination) {
    const response = await fetch("http://127.0.0.1:8000/api/v1/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            origin_lat: start[0], origin_lng: start[1],
            dest_lat: destination[0], dest_lng: destination[1],
            preference: "car", priority: "safety"
        })
    });
    if (!response.ok) {
        const error = new Error("Backend error");
        error.status = response.status; 
        throw error; 
    }
    const data = await response.json();
    if (data.status !== "success" || !data.routes) throw new Error("No route found.");
    return data;
}

function displayRoutes(routeData, start, destination) {
    if (!routeCards || !map) return;
    routeCards.innerHTML = "";
    const routes = routeData.routes;
    const recommendedId = routeData.recommended_route_id;

    routes.forEach(function (route, index) {
        const coordinates = route.geometry.map(p => [p.lat, p.lng]);
        const isRecommended = route.route_id === recommendedId;
        const line = L.polyline(coordinates, {
            color: isRecommended ? "#147d64" : "#e49b32",
            weight: isRecommended ? 6 : 4, opacity: 0.9
        }).addTo(map);
        routeLines.push(line);

        const card = document.createElement("article");
        card.className = "route-card";
        card.innerHTML = `
            <h3 style="color: ${isRecommended ? '#147d64' : '#333'}">
                ${isRecommended ? "⭐ Recommended Route" : "Alternative Route " + (index + 1)}
            </h3>
            <p>Distance: ${route.distance_km} km</p>
            <p>Time: ${route.duration_min} mins</p>
            <p style="font-weight:bold; color:${route.safety_score >= 60 ? '#147d64' : '#c0392b'}">
                🛡️ Safety Score: ${route.safety_score}/100 (${route.safety_rating})
            </p>
            <ul>${route.reasons.map(r => `<li style="color:#60716b">${r}</li>`).join('')}</ul>
        `;
        routeCards.appendChild(card);
    });

    if (results) results.hidden = false;
    map.fitBounds(L.latLngBounds(routeLines.map(l => l.getBounds()).flat()), { padding: [40, 40] });
}

if (findButton) {
    findButton.addEventListener("click", async function () {
        const startText = document.getElementById("start").value.trim();
        const destinationText = document.getElementById("destination").value.trim();

        if (!startText || !destinationText) {
            alert("Please enter both start and destination.");
            return;
        }

        findButton.disabled = true;
        document.getElementById("status").textContent = "Searching...";

        try {
            const start = await getCoordinates(startText);
            const destination = await getCoordinates(destinationText);
            const routeData = await getRoutes(start, destination);

            markers.forEach(m => map.removeLayer(m));
            routeLines.forEach(l => map.removeLayer(l));
            markers = []; routeLines = []; selectedPoints = [];

            markers.push(L.marker(start).addTo(map).bindPopup("Start"));
            markers.push(L.marker(destination).addTo(map).bindPopup("End"));

            displayRoutes(routeData, start, destination);
            document.getElementById("status").textContent = "✅ Route found!";
        } catch (error) {
            document.getElementById("status").textContent = "❌ " + (error.message || "Error.");
            document.getElementById("status").style.color = "#c0392b";
        } finally {
            findButton.disabled = false;
        }
    });
}

if (clearButton) {
    clearButton.addEventListener("click", function () {
        document.getElementById("start").value = "";
        document.getElementById("destination").value = "";
        markers.forEach(m => map.removeLayer(m));
        routeLines.forEach(l => map.removeLayer(l));
        markers = []; routeLines = []; selectedPoints = [];
        if (routeCards) routeCards.innerHTML = "";
        if (results) results.hidden = true;
        document.getElementById("status").textContent = "";
        if (map) map.setView([12.9716, 77.5946], 13);
    });
}

// ==========================================
// MODULE 5: PERSONAL SAFETY DASHBOARD (For index.html)
// ==========================================
async function loadDashboard() {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;

    // 1. Load My Reports
    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/users/me/reports", {
            headers: { "X-User-Id": userId }
        });
        const reports = await response.json();
        const list = document.getElementById("myReportsList");
        if (!list) return;

        if (reports.length === 0) {
            list.innerHTML = "<p style='color:#888;'>No reports submitted yet.</p>";
        } else {
            list.innerHTML = "";
            reports.forEach(r => {
                const item = document.createElement("div");
                item.style.borderBottom = "1px solid #ddd";
                item.style.padding = "8px 0";
                
                let statusColor = "#c47a18";
                if (r.status === "approved") statusColor = "#147d64";
                if (r.status === "rejected") statusColor = "#c0392b";

                item.innerHTML = `
                    <strong>${r.report_type}</strong> 
                    <span style="float:right; color:${statusColor}; font-weight:bold; font-size:12px; text-transform:uppercase;">${r.status}</span>
                    <br><small style="color:#60716b;">${new Date(r.created_at).toLocaleString()}</small>
                `;
                list.appendChild(item);
            });
        }
    } catch (e) { console.log("Could not load reports.", e); }

    // 2. Load Emergency Contacts
    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/emergency-contacts", {
            headers: { "X-User-Id": userId }
        });
        const contacts = await response.json();
        const contactList = document.getElementById("myContactsList");
        if (!contactList) return;

        if (contacts.length === 0) {
            contactList.innerHTML = "<p style='color:#c0392b;'>⚠️ No contacts added yet.</p>";
        } else {
            contactList.innerHTML = "";
            contacts.forEach(c => {
                const p = document.createElement("p");
                p.style.margin = "5px 0";
                p.innerHTML = `📞 <strong>${c.name}</strong> (${c.relationship_type}) - ${c.phone_number}`;
                contactList.appendChild(p);
            });
        }
    } catch (e) { console.log("Could not load contacts.", e); }
}

// Add Contact Button
const addContactBtn = document.getElementById("addContactBtn");
if (addContactBtn) {
    addContactBtn.addEventListener("click", async function() {
        const name = document.getElementById("contactName").value;
        const phone = document.getElementById("contactPhone").value;
        const relation = document.getElementById("contactRelation").value;
        const userId = localStorage.getItem("user_id");
        const status = document.getElementById("contactStatus");

        if (!name || !phone || !relation) {
            status.style.color = "red";
            status.textContent = "Please fill all fields.";
            return;
        }

        status.style.color = "#60716b";
        status.textContent = "Saving...";

        try {
            const response = await fetch("http://127.0.0.1:8000/api/v1/emergency-contacts", {
                method: "POST",
                headers: { 
                    "Content-Type": "application/json",
                    "X-User-Id": userId
                },
                body: JSON.stringify({
                    name: name,
                    phone_number: phone,
                    relationship_type: relation
                })
            });

            if (response.ok) {
                status.style.color = "#147d64";
                status.textContent = "✅ Contact added successfully!";
                document.getElementById("contactName").value = "";
                document.getElementById("contactPhone").value = "";
                document.getElementById("contactRelation").value = "";
                loadDashboard();
            } else {
                const err = await response.json();
                status.style.color = "red";
                status.textContent = "❌ " + (err.detail || "Failed to add contact.");
            }
        } catch (e) {
            status.style.color = "red";
            status.textContent = "❌ Network error.";
        }
    });
}

// Check-in Button
const dashboardCheckInBtn = document.getElementById("dashboardCheckInBtn");
if (dashboardCheckInBtn) {
    dashboardCheckInBtn.addEventListener("click", async function() {
        const userId = localStorage.getItem("user_id");
        const statusText = document.getElementById("checkInStatus");
        if (statusText) {
            statusText.style.color = "#60716b";
            statusText.textContent = "Checking in...";
        }

        try {
            const response = await fetch("http://127.0.0.1:8000/api/v1/users/me/check-in", {
                method: "POST",
                headers: { "X-User-Id": userId }
            });
            const data = await response.json();

            if (response.ok) {
                if (statusText) {
                    statusText.style.color = "#147d64";
                    statusText.textContent = "✅ Check-in recorded successfully at " + new Date().toLocaleTimeString();
                }
            } else {
                if (statusText) {
                    statusText.style.color = "#c0392b";
                    statusText.textContent = "❌ " + (data.detail || "Check-in failed.");
                }
            }
        } catch (e) {
            if (statusText) {
                statusText.style.color = "#c0392b";
                statusText.textContent = "❌ Network error.";
            }
        }
    });
}

// ==========================================
// REPORT FORM LOGIC (For report.html)
// ==========================================
const submitReportBtn = document.getElementById("submitReportBtn");
if (submitReportBtn) {
    // Ensure user is logged in before they submit
    if (!localStorage.getItem("user_id")) {
        window.location.href = "index.html";
    }

    submitReportBtn.addEventListener("click", async function() {
        const type = document.getElementById("reportType").value;
        const description = document.getElementById("reportDescription").value;
        const evidence = document.getElementById("reportEvidence").value;
        const status = document.getElementById("reportStatus");
        const userId = localStorage.getItem("user_id");

        if (!description) {
            status.style.color = "red";
            status.textContent = "Please provide a description.";
            return;
        }

        submitReportBtn.disabled = true;
        submitReportBtn.textContent = "Submitting...";
        status.textContent = "";

        try {
            const response = await fetch("http://127.0.0.1:8000/api/v1/reports", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-User-Id": userId },
                body: JSON.stringify({
                    segment_id: 1, // Default segment for demo
                    report_type: type,
                    description: description,
                    evidence_url: evidence,
                    source: "web"
                })
            });

            if (response.ok) {
                status.style.color = "#147d64";
                status.textContent = "✅ Report submitted successfully!";
                document.getElementById("reportDescription").value = "";
                document.getElementById("reportEvidence").value = "";
            } else {
                const err = await response.json();
                status.style.color = "red";
                status.textContent = "❌ " + (err.detail || "Failed to submit.");
            }
        } catch (e) {
            status.style.color = "red";
            status.textContent = "❌ Network error.";
        } finally {
            submitReportBtn.disabled = false;
            submitReportBtn.textContent = "Submit Report";
        }
    });
}