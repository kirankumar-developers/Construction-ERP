document.addEventListener('DOMContentLoaded', function () {
    // Sidebar Toggle
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });
    }

    // Auto-dismiss Flash Alerts
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            // Check if bootstrap is loaded to close gracefully
            if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } else {
                alert.style.display = 'none';
            }
        }, 5000);
    });

    // Dynamic Invoice Item Rows
    const addInvoiceItem = document.getElementById('addInvoiceItem');
    const invoiceItemsContainer = document.getElementById('invoiceItemsContainer');
    if (addInvoiceItem && invoiceItemsContainer) {
        addInvoiceItem.addEventListener('click', function () {
            const index = invoiceItemsContainer.children.length;
            const itemRow = document.createElement('div');
            itemRow.className = 'row g-3 mb-3 invoice-item-row align-items-end';
            itemRow.innerHTML = `
                <div class="col-md-6">
                    <label class="form-label small text-muted">Item Description</label>
                    <input type="text" name="description[]" class="form-control" placeholder="e.g. Standard labor rate, wiring materials" required>
                </div>
                <div class="col-md-2">
                    <label class="form-label small text-muted">Quantity</label>
                    <input type="number" name="quantity[]" class="form-control" min="1" value="1" required>
                </div>
                <div class="col-md-3">
                    <label class="form-label small text-muted">Unit Price ($)</label>
                    <input type="number" name="unit_price[]" class="form-control" step="0.01" min="0" placeholder="0.00" required>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger btn-sm w-100 remove-item-row" style="height: 38px;">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            invoiceItemsContainer.appendChild(itemRow);
            
            // Re-apply remove handlers
            itemRow.querySelector('.remove-item-row').addEventListener('click', function() {
                itemRow.remove();
            });
        });

        // Initialize first remove handler if present
        const firstRemove = invoiceItemsContainer.querySelector('.remove-item-row');
        if (firstRemove) {
            firstRemove.addEventListener('click', function() {
                firstRemove.closest('.invoice-item-row').remove();
            });
        }
    }
});

// Map helper using Leaflet.js
function initLeafletMap(containerId, lat, lng, editable = false, inputPrefix = '') {
    if (!document.getElementById(containerId)) return null;

    const defaultLat = lat ? parseFloat(lat) : 12.9716;
    const defaultLng = lng ? parseFloat(lng) : 77.5946;
    const zoomLevel = lat && lng ? 14 : 10;

    // Create Map
    const map = L.map(containerId).setView([defaultLat, defaultLng], zoomLevel);

    // Add Tile Layer (OpenStreetMap standard tiling)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Add Marker
    const marker = L.marker([defaultLat, defaultLng], {
        draggable: editable
    }).addTo(map);

    if (editable) {
        marker.on('dragend', function (event) {
            const position = marker.getLatLng();
            marker.setLatLng(position);
            
            const latInput = document.getElementById(inputPrefix + 'lat');
            const lngInput = document.getElementById(inputPrefix + 'lng');
            if (latInput) latInput.value = position.lat.toFixed(6);
            if (lngInput) lngInput.value = position.lng.toFixed(6);
            
            // Optional reverse geocoding to address text
            reverseGeocode(position.lat, position.lng, inputPrefix + 'address');
        });

        map.on('click', function(e) {
            marker.setLatLng(e.latlng);
            const latInput = document.getElementById(inputPrefix + 'lat');
            const lngInput = document.getElementById(inputPrefix + 'lng');
            if (latInput) latInput.value = e.latlng.lat.toFixed(6);
            if (lngInput) lngInput.value = e.latlng.lng.toFixed(6);
            reverseGeocode(e.latlng.lat, e.latlng.lng, inputPrefix + 'address');
        });

        // Auto-geocode map when address text changes
        const addrField = document.getElementById(inputPrefix + 'address');
        if (addrField) {
            addrField.addEventListener('change', function() {
                const query = addrField.value.trim();
                if (query.length > 3) {
                    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
                        .then(res => res.json())
                        .then(data => {
                            if (data && data.length > 0) {
                                const first = data[0];
                                const newLat = parseFloat(first.lat);
                                const newLng = parseFloat(first.lon);
                                
                                const latInput = document.getElementById(inputPrefix + 'lat');
                                const lngInput = document.getElementById(inputPrefix + 'lng');
                                if (latInput) latInput.value = newLat.toFixed(6);
                                if (lngInput) lngInput.value = newLng.toFixed(6);
                                
                                map.setView([newLat, newLng], 14);
                                marker.setLatLng([newLat, newLng]);
                            }
                        })
                        .catch(err => console.error("Geocoding lookup error:", err));
                }
            });
        }
    }

    return map;
}

function reverseGeocode(lat, lng, addressInputId) {
    const addressInput = document.getElementById(addressInputId);
    if (!addressInput) return;
    
    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`)
        .then(response => response.json())
        .then(data => {
            if (data && data.display_name) {
                addressInput.value = data.display_name;
            }
        })
        .catch(err => console.error("Reverse geocoding error:", err));
}

// Check-in and Check-out GPS logging flow
function trackAttendance(jobId, type) {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    const button = document.getElementById(type === 'checkin' ? 'checkinBtn' : 'checkoutBtn');
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Capturing Location...`;

    navigator.geolocation.getCurrentPosition(
        function (position) {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            // Get text address from coordinates
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18`)
                .then(res => res.json())
                .then(data => {
                    const address = data.display_name || `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
                    submitAttendanceRequest(jobId, type, lat, lng, address, button, originalText);
                })
                .catch(() => {
                    submitAttendanceRequest(jobId, type, lat, lng, `GPS (${lat.toFixed(4)}, ${lng.toFixed(4)})`, button, originalText);
                });
        },
        function (error) {
            button.disabled = false;
            button.innerHTML = originalText;
            alert(`Location access denied. Please allow GPS access: ${error.message}`);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}

function submitAttendanceRequest(jobId, type, lat, lng, address, button, originalText) {
    const formData = new FormData();
    formData.append('lat', lat);
    formData.append('lng', lng);
    formData.append('address', address);

    const url = `/employee/jobs/${jobId}/${type === 'checkin' ? 'check_in' : 'check_out'}`;

    fetch(url, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert(data.error || "An error occurred.");
            button.disabled = false;
            button.innerHTML = originalText;
        }
    })
    .catch(err => {
        console.error(err);
        alert("Server communication failure.");
        button.disabled = false;
        button.innerHTML = originalText;
    });
}
