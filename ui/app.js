// UI State Management
let currentUser = null;
let selectedSlot = null;

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    setupDateInputs();
    setupMessageSystem();
    checkAuthStatus();
});

function setupDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        input.min = today;
        // Prevent selecting weekends: if user picks a weekend, clear and show message
        input.addEventListener('change', (e) => {
            const val = e.target.value;
            if (!val) return;
            const d = new Date(val + 'T00:00:00');
            const day = d.getDay(); // 0 = Sunday, 6 = Saturday
            if (day === 0 || day === 6) {
                showError('Weekends are disabled. Please select a weekday.');
                e.target.value = '';
            }
        });
    });
}

function setupMessageSystem() {
    if (!document.getElementById('messageContainer')) {
        const container = document.createElement('div');
        container.id = 'messageContainer';
        document.body.appendChild(container);
    }
}

function checkAuthStatus() {
    if (authToken) {
        showMainContent();
        loadUserData();
    } else {
        showLoginForm();
    }
}

// Auth UI Functions
function showLoginForm() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('adminPanel').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
}

function showRegisterForm() {
    document.getElementById('registerForm').style.display = 'block';
    document.getElementById('loginForm').style.display = 'none';
}

async function handleLogin(event) {
    event.preventDefault();
    try {
        await login(
            document.getElementById('loginUsername').value,
            document.getElementById('loginPassword').value
        );
        showMainContent();
        loadUserData();
    } catch (error) {
        showError('Login failed: ' + error.message);
    }
}

async function handleRegister(event) {
    event.preventDefault();
    try {
        await register(
            document.getElementById('regEmail').value,
            document.getElementById('regSapId').value,
            document.getElementById('regPassword').value
        );
        showLoginForm();
        showSuccess('Registration successful! Please login.');
    } catch (error) {
        showError('Registration failed: ' + error.message);
    }
}

function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showLoginForm();
}

// Main Content UI Functions
function showMainContent() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
    
    // Hide login/register buttons, show logout
    document.querySelectorAll('#nav-buttons button').forEach(btn => {
        if (btn.id === 'logoutBtn') {
            btn.style.display = 'inline-block';
        } else {
            btn.style.display = 'none';
        }
    });
    
    // Setup event listeners for game and date selection
    const gameSelect = document.getElementById('gameSelect');
    const dateSelect = document.getElementById('dateSelect');
    const viewSlotsBtn = document.getElementById('viewSlotsBtn');

    if (gameSelect && dateSelect && viewSlotsBtn) {
        gameSelect.addEventListener('change', () => {
            if (gameSelect.value && dateSelect.value) {
                loadSlots();
            }
        });

        dateSelect.addEventListener('change', () => {
            if (gameSelect.value && dateSelect.value) {
                loadSlots();
            }
        });

        viewSlotsBtn.addEventListener('click', loadSlots);
    }
    
    loadGames();
    loadBookingHistory();
}

async function loadUserData() {
    try {
        const user = await apiRequest('/users/me');
        currentUser = user;
        if (user.role === 'admin') {
            document.getElementById('adminPanel').style.display = 'block';
            loadAdminData();
        }
    } catch (error) {
        console.error('Failed to load user data:', error);
    }
}

async function loadGames() {
    try {
        const games = await getGames();
        const gameSelect = document.getElementById('gameSelect');
        const adminGameSelect = document.getElementById('adminGameSelect');
        
        // Clear and initialize game selects
        gameSelect.innerHTML = '<option value="">Select Game</option>';
        if (adminGameSelect) {  // Admin select might not exist for regular users
            adminGameSelect.innerHTML = '<option value="">Select Game</option>';
        }
        
        const activeGames = games.filter(game => 
            game.status === 'active' || currentUser?.role === 'admin'
        );

        if (activeGames.length === 0) {
            showMessage('No games are currently available', 'info');
            return;
        }
        
        // Add games to select elements
        activeGames.forEach(game => {
            const status = game.status === 'active' ? '' : ' (Inactive)';
            const maxPlayers = game.max_players ? ` (Max: ${game.max_players})` : '';
            const option = `<option value="${game.id}">${game.name} - ${game.type}${maxPlayers}${status}</option>`;
            gameSelect.insertAdjacentHTML('beforeend', option);
            if (adminGameSelect) {
                adminGameSelect.insertAdjacentHTML('beforeend', option);
            }
        });

        showSuccess(`Loaded ${activeGames.length} available games`);
    } catch (error) {
        showError('Failed to load games: ' + error.message);
    }
}

async function loadSlots() {
    const gameId = document.getElementById('gameSelect').value;
    const date = document.getElementById('dateSelect').value;
    const slotsContainer = document.getElementById('availableSlots');
    
    if (!gameId || !date) {
        slotsContainer.innerHTML = '<div class="message-info">Please select both game and date to view available slots.</div>';
        return;
    }

    try {
        slotsContainer.innerHTML = '<div class="loading">Loading available slots...</div>';
        const formattedDate = await formatDateForAPI(date);
        const slots = await getGameSlots(gameId, formattedDate);
        displaySlots(slots, gameId, formattedDate);
    } catch (error) {
        let errorMessage = error.message;
        if (typeof error === 'object' && error !== null) {
            errorMessage = error.detail || error.message || 'Unknown error occurred';
        }
        showError('Failed to load slots: ' + errorMessage);
        slotsContainer.innerHTML = '<div class="message-error">Failed to load slots. Please try again.</div>';
    }
}

function displaySlots(slots, gameId, date) {
    const slotsContainer = document.getElementById('availableSlots');
    slotsContainer.innerHTML = '';

    if (!slots || slots.length === 0) {
        const selectedDate = new Date(date);
        const isWeekend = selectedDate.getDay() === 0 || selectedDate.getDay() === 6;
        
        let message = isWeekend ? 
            'Slots are not available on weekends. Please select a weekday.' :
            'No slots available for the selected date.';

        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `<p>${message}</p>`;
        
        if (currentUser?.role === 'admin') {
            emptyState.innerHTML += `
                <button class="admin-action" onclick="generateSlotsForDate('${gameId}', '${date}')">
                    Generate Slots for this Date
                </button>
            `;
        }
        
        slotsContainer.appendChild(emptyState);
        return;
    }

    const slotsGrid = document.createElement('div');
    slotsGrid.className = 'slots-grid';

    slots.forEach((slot, idx) => {
        const startTime = new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const endTime = new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const slotCard = document.createElement('div');
        slotCard.className = 'slot-card' + 
            (slot.is_cancelled ? ' cancelled' : '') +
            (!slot.is_available ? ' unavailable' : '');
        
        let status = 'Available';
        if (slot.is_cancelled) {
            status = `Cancelled${slot.cancellation_reason ? ': ' + slot.cancellation_reason : ''}`;
        } else if (!slot.is_available) {
            status = 'Booked';
        }
        
        const isBookable = !slot.is_cancelled && slot.is_available;
        
        // Show a human-friendly slot number starting from 1 (index-based)
        const slotNumber = idx + 1;
        slotCard.innerHTML = `
            <div class="slot-number">Slot #${slotNumber}</div>
            <div class="slot-time">${startTime} - ${endTime}</div>
            <div class="slot-status ${isBookable ? 'available' : ''}">${status}</div>
            ${isBookable ? `
                <button class="book-button" onclick="showBookingModal(${slot.id})">Book Now</button>
            ` : ''}
        `;
        slotsGrid.appendChild(slotCard);
    });

    slotsContainer.appendChild(slotsGrid);
    
    const availableCount = slots.filter(s => s.is_available).length;
    showMessage(`Found ${slots.length} slots, ${availableCount} available`, 'info');
}

async function loadBookingHistory() {
    const bookingsList = document.getElementById('bookingsList'); // Changed from bookingHistory to bookingsList
    if (!bookingsList) {
        console.error('Booking history element not found');
        return;
    }
    
    try {
        bookingsList.innerHTML = '<div class="loading">Loading your booking history...</div>';
        
        const bookings = await getBookingHistory();
        displayBookingHistory(bookings);
    } catch (error) {
        let errorMessage = error.message;
        if (typeof error === 'object' && error !== null) {
            errorMessage = error.detail || error.message || 'Unknown error occurred';
        }
        showError('Failed to load booking history: ' + errorMessage);
        bookingsList.innerHTML = '<div class="message-error">Failed to load booking history. Please try again.</div>';
    }
}

function displayBookingHistory(bookings) {
    const bookingsList = document.getElementById('bookingsList'); // Changed from bookingHistory to bookingsList
    if (!bookingsList) {
        console.error('Booking history element not found');
        return;
    }
    bookingsList.innerHTML = '';

    if (!bookings || bookings.length === 0) {
        bookingsList.innerHTML = `
            <div class="empty-state">
                <p>You don't have any bookings yet.</p>
                <p>Select a game and date above to make your first booking!</p>
            </div>
        `;
        return;
    }

    const historyContainer = document.createElement('div');
    historyContainer.className = 'booking-history';

    // Sort bookings by date, most recent first
    bookings.sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

    bookings.forEach(booking => {
        const startTime = new Date(booking.start_time);
        const endTime = new Date(booking.end_time);
        const isUpcoming = startTime > new Date();
        
        const card = document.createElement('div');
        card.className = `booking-card ${isUpcoming ? 'upcoming' : 'past'}`;
        
        const formattedDate = startTime.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        const formattedTime = `${startTime.toLocaleTimeString()} - ${endTime.toLocaleTimeString()}`;
        
        card.innerHTML = `
            <h3>${booking.game_name}</h3>
            <p class="booking-date">${formattedDate}</p>
            <p class="booking-time">${formattedTime}</p>
            ${isUpcoming ? `
                <button class="cancel-button" onclick="window.handleCancelBooking(${booking.id})">Cancel Booking</button>
            ` : '<span class="past-booking">Past Booking</span>'}
        `;
        historyContainer.appendChild(card);
    });

    bookingsList.appendChild(historyContainer);
    showMessage(`Showing ${bookings.length} bookings`, 'info');
}

// Booking Modal Functions
function showBookingModal(slotId) {
    selectedSlot = slotId;
    document.getElementById('bookingModal').style.display = 'block';
    document.getElementById('bookingDetails').textContent = `Booking slot: ${slotId}`;
}

function closeBookingModal() {
    document.getElementById('bookingModal').style.display = 'none';
    selectedSlot = null;
}

async function confirmBooking() {
    if (!selectedSlot) return;

    const otherPlayers = document.getElementById('otherPlayersSapIds').value;
    try {
        await createBooking(selectedSlot, otherPlayers);
        closeBookingModal();
        loadSlots();
        loadBookingHistory();
        showSuccess('Booking created successfully!');
    } catch (error) {
        showError('Failed to create booking: ' + error.message);
    }
}

// Admin Functions
async function loadAdminData() {
    await loadGames();
    loadAdminGames();
}

function showGameForm() {
    const form = document.getElementById('gameForm');
    if (!form) return;
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function handleCreateGame() {
    const name = document.getElementById('newGameName').value;
    const type = document.getElementById('newGameType').value;
    const maxPlayers = parseInt(document.getElementById('newGameMaxPlayers').value, 10) || 2;

    if (!name || !type) {
        showError('Please provide game name and type');
        return;
    }

    try {
        await createGame(name, type, maxPlayers);
        showSuccess('Game created successfully');
        document.getElementById('newGameName').value = '';
        document.getElementById('newGameMaxPlayers').value = 2;
        // Refresh game lists
        await loadGames();
        loadAdminGames();
    } catch (err) {
        showError('Failed to create game: ' + (err.message || err.detail || 'Unknown'));
    }
}

async function loadAdminGames() {
    try {
        const games = await getGames();
        const list = document.getElementById('gamesList');
        if (!list) return;
        list.innerHTML = '';

        if (!games || games.length === 0) {
            list.innerHTML = '<div class="message-info">No games found</div>';
            return;
        }

        games.forEach(game => {
            const div = document.createElement('div');
            div.className = 'admin-game-item';
            div.innerHTML = `
                <strong>${game.name}</strong> (${game.type}) - Max: ${game.max_players} - Status: ${game.status}
                <button onclick="toggleGameStatus(${game.id}, '${game.status}')">Toggle Status</button>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        console.error('Failed to load admin games', err);
    }
}

async function toggleGameStatus(gameId, currentStatus) {
    try {
        const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
        await updateGameStatus(gameId, newStatus);
        showSuccess('Game status updated');
        await loadGames();
        loadAdminGames();
    } catch (err) {
        showError('Failed to update game status: ' + (err.message || err.detail || 'Unknown'));
    }
}

async function formatDateForAPI(date) {
    // Convert date to YYYY-MM-DD format
    return new Date(date).toISOString().split('T')[0];
}

async function generateSlotsForDate(gameId, date) {
    try {
        const formattedDate = await formatDateForAPI(date);
        await generateSlotsForGame(gameId, formattedDate);
        showSuccess('Slots generated successfully!');
        await loadSlots(); // Refresh the slots display
    } catch (error) {
        let errorMessage = error.message;
        if (typeof error === 'object' && error !== null) {
            errorMessage = error.detail || error.message || 'Unknown error occurred';
        }
        showError('Failed to generate slots: ' + errorMessage);
    }
}

async function generateSlots() {
    const gameId = document.getElementById('adminGameSelect').value;
    const date = document.getElementById('adminDateSelect').value;
    
    if (!gameId || !date) {
        showError('Please select both game and date');
        return;
    }

    await generateSlotsForDate(gameId, date);
}

// Make the function available in the global scope
window.handleCancelBooking = async function(bookingId) {
    console.log('Attempting to cancel booking:', bookingId);

    if (!confirm('Are you sure you want to cancel this booking?')) {
        console.log('Cancellation cancelled by user');
        return;
    }

    try {
        console.log('Making API call to cancel booking via apiRequest');
        // Call the backend directly using the shared apiRequest helper
        const result = await apiRequest(`/bookings/${bookingId}`, { method: 'DELETE' });
        console.log('Booking cancelled successfully:', result);

        showSuccess('Booking cancelled successfully');
        console.log('Refreshing booking history and slots');

        await loadBookingHistory(); // Refresh booking list
        await loadSlots(); // Refresh available slots
    } catch (error) {
        console.error('Error cancelling booking:', error);
        let errorMessage = error.message;
        if (typeof error === 'object' && error !== null) {
            errorMessage = error.detail || error.message || 'Unknown error occurred';
        }
        showError('Failed to cancel booking: ' + errorMessage);
    }
}

async function cancelSlots() {
    const gameId = document.getElementById('adminGameSelect').value;
    const date = document.getElementById('adminDateSelect').value;
    const reason = prompt('Enter reason for cancellation:');
    
    if (!gameId || !date || !reason) return;

    try {
        await cancelGameSlots(gameId, date, reason);
        showSuccess('Slots cancelled successfully!');
    } catch (error) {
        showError('Failed to cancel slots: ' + error.message);
    }
}

// Message Display Functions
window.showMessage = function(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    container.appendChild(messageDiv);
    setTimeout(() => messageDiv.remove(), 5000);
};

window.showError = function(message) {
    window.showMessage(message, 'error');
};

window.showSuccess = function(message) {
    window.showMessage(message, 'success');
};