// Bootstrap modal instances
let addRoomModal;
let editRoomModal;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap modals
    addRoomModal = new bootstrap.Modal(document.getElementById('addRoomModal'));
    editRoomModal = new bootstrap.Modal(document.getElementById('editRoomModal'));
    
    // Load initial data
    loadTopology();
});

// Load and display topology
async function loadTopology() {
    try {
        const response = await fetch('/topology');
        const topology = await response.json();
        displayRooms(topology);
        updateStatistics(topology);
    } catch (error) {
        console.error('Error loading topology:', error);
        alert('Error loading topology. Please try again.');
    }
}

// Display rooms in the UI
function displayRooms(topology) {
    const roomsList = document.getElementById('roomsList');
    roomsList.innerHTML = '';

    Object.entries(topology.rooms).forEach(([roomType, rooms]) => {
        rooms.forEach(room => {
            const roomCard = createRoomCard(room, roomType);
            roomsList.appendChild(roomCard);
        });
    });
}

// Create a room card element
function createRoomCard(room, roomType) {
    const div = document.createElement('div');
    div.className = 'room-card';
    div.innerHTML = `
        <div class="room-header">
            <div>
                <h3 class="room-title">${room.name}</h3>
                <span class="room-type-badge room-type-${roomType.replace('_rooms', '')}">${roomType.replace('_', ' ')}</span>
            </div>
            <div class="room-actions">
                <button class="btn btn-sm btn-outline-primary" onclick="showEditRoomModal('${room.id}', '${room.name}', ${room.floor})">
                    Edit
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteRoom('${room.id}')">
                    Delete
                </button>
            </div>
        </div>
        <div class="room-info">
            <div>ID: ${room.id}</div>
            <div>Floor: ${room.floor}</div>
        </div>
    `;
    return div;
}

// Update statistics display
function updateStatistics(topology) {
    const totalRooms = Object.values(topology.rooms).reduce((acc, rooms) => acc + rooms.length, 0);
    document.getElementById('totalRooms').textContent = totalRooms;

    // Update rooms by type
    const roomsByType = document.getElementById('roomsByType');
    roomsByType.innerHTML = Object.entries(topology.rooms)
        .map(([type, rooms]) => `<li>${type.replace('_', ' ')}: ${rooms.length}</li>`)
        .join('');

    // Update rooms by floor
    const roomsByFloor = document.getElementById('roomsByFloor');
    const floorCounts = {};
    Object.values(topology.rooms).flat().forEach(room => {
        floorCounts[room.floor] = (floorCounts[room.floor] || 0) + 1;
    });
    roomsByFloor.innerHTML = Object.entries(floorCounts)
        .sort(([a], [b]) => a - b)
        .map(([floor, count]) => `<li>Floor ${floor}: ${count}</li>`)
        .join('');
}

// Show add room modal
function showAddRoomModal() {
    document.getElementById('addRoomForm').reset();
    addRoomModal.show();
}

// Add a new room
async function addRoom() {
    const roomType = document.getElementById('roomType').value;
    const name = document.getElementById('roomName').value;
    const id = document.getElementById('roomId').value;
    const floor = parseInt(document.getElementById('roomFloor').value);

    try {
        const response = await fetch(`/topology/rooms/${roomType}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, id, floor }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add room');
        }

        addRoomModal.hide();
        loadTopology();
    } catch (error) {
        console.error('Error adding room:', error);
        alert(error.message);
    }
}

// Show edit room modal
function showEditRoomModal(roomId, roomName, roomFloor) {
    document.getElementById('editRoomId').value = roomId;
    document.getElementById('editRoomName').value = roomName;
    document.getElementById('editRoomFloor').value = roomFloor;
    editRoomModal.show();
}

// Update an existing room
async function updateRoom() {
    const roomId = document.getElementById('editRoomId').value;
    const name = document.getElementById('editRoomName').value;
    const floor = parseInt(document.getElementById('editRoomFloor').value);

    try {
        const response = await fetch(`/topology/rooms/${roomId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, floor }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update room');
        }

        editRoomModal.hide();
        loadTopology();
    } catch (error) {
        console.error('Error updating room:', error);
        alert(error.message);
    }
}

// Delete a room
async function deleteRoom(roomId) {
    if (!confirm('Are you sure you want to delete this room?')) {
        return;
    }

    try {
        const response = await fetch(`/topology/rooms/${roomId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete room');
        }

        loadTopology();
    } catch (error) {
        console.error('Error deleting room:', error);
        alert(error.message);
    }
}
