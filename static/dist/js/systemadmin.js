document.addEventListener('DOMContentLoaded', function() {
   

    // Initialize form handlers
    initAdminManagement();
    initLocationManagement();
    initPredictionForm();
});

function checkAdminSession() {
    fetch('/check-session')
        .then(response => response.json())
        .then(data => {
            if (!data.logged_in) {
                window.location.href = '/system-admin';
            } else {
                document.getElementById('username-display').textContent = data.username;
            }
        })
        .catch(error => {
            console.error('Session check error:', error);
            window.location.href = '/login';
        });
}

function initAdminManagement() {
    const adminForm = document.getElementById('add-admin-form');
    const adminListTable = document.getElementById('admin-list-table');

    // Load admin list
    function loadAdminList() {
        fetch('/get-admins')
            .then(response => response.json())
            .then(admins => {
                const tbody = adminListTable.querySelector('tbody');
                tbody.innerHTML = ''; // Clear existing rows
                admins.forEach((admin, index) => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${admin.username}</td>
                        <td>${admin.role}</td>
                        <td>
                            <button class="btn btn-danger btn-sm delete-admin" data-id="${admin.id}">
                                Delete
                            </button>
                        </td>
                    `;
                });

                // Add event listeners to delete buttons
                document.querySelectorAll('.delete-admin').forEach(button => {
                    button.addEventListener('click', function() {
                        const adminId = this.getAttribute('data-id');
                        if(confirm('Are you sure you want to delete this admin?')) {
                            fetch(`/delete-admin/${adminId}`, { method: 'DELETE' })
                                .then(response => response.json())
                                .then(result => {
                                    if(result.success) {
                                        loadAdminList(); // Reload the list
                                    } else {
                                        alert('Failed to delete admin');
                                    }
                                });
                        }
                    });
                });
            });
    }

    // Add admin form submission
    adminForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(adminForm);
        
        fetch('/add-admin', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if(result.success) {
                alert('Admin added successfully');
                adminForm.reset();
                loadAdminList();
            } else {
                alert(result.error || 'Failed to add admin');
            }
        });
    });

    // Initial load of admin list
    loadAdminList();
}

function initLocationManagement() {
    const locationForm = document.getElementById('add-location-form');
    const locationListTable = document.getElementById('location-list-table');
    const locationDropdown = document.getElementById('location-select');

    // Load location list
    function loadLocationList() {
        fetch('/get-locations')
            .then(response => response.json())
            .then(locations => {
                const tbody = locationListTable.querySelector('tbody');
                tbody.innerHTML = ''; // Clear existing rows
                locationDropdown.innerHTML = '<option value="">Select Location</option>'; // Reset dropdown

                locations.forEach((location, index) => {
                    // Populate location list table
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${location.nama_lokasi}</td>
                    `;

                    // Populate location dropdown
                    const option = document.createElement('option');
                    option.value = location.id;
                    option.textContent = location.nama_lokasi;
                    locationDropdown.appendChild(option);
                });
            });
    }

    // Add location form submission
    locationForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(locationForm);
        
        fetch('/add-location', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if(result.success) {
                alert('Location added successfully');
                locationForm.reset();
                loadLocationList();
            } else {
                alert(result.error || 'Failed to add location');
            }
        });
    });

    // Initial load of location list
    loadLocationList();
}

function initPredictionForm() {
    const predictionForm = document.getElementById('prediction-form');
    const predictionResult = document.getElementById('prediction-result');

    predictionForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(predictionForm);
        
        fetch('/predict', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            if(result.success) {
                // Display prediction result
                predictionResult.innerHTML = `
                    <div class="alert ${result.prediction === 'Berpotensi Banjir' ? 'alert-danger' : 'alert-success'}">
                        <h5>${result.prediction}</h5>
                        <p>Location: ${result.lokasi_name}</p>
                        <p>Flow Rate: ${result.flowmeter} L/minute</p>
                        <p>Rainfall: ${result.curah_hujan} mm/h</p>
                        <p>Land Slope: ${result.inclinometer} degrees</p>
                    </div>
                `;
            } else {
                predictionResult.innerHTML = `
                    <div class="alert alert-warning">
                        <h5>Prediction Error</h5>
                        <p>${result.error || 'Unable to generate prediction'}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            predictionResult.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Error</h5>
                    <p>Network or server error occurred</p>
                </div>
            `;
            console.error('Prediction error:', error);
        });
    });
}