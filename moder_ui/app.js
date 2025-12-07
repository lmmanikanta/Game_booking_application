
// --- UI State Management ---
let currentUser = null;
let selectedSlot = null;

// --- Initialize Application ---
document.addEventListener('DOMContentLoaded', () => {
    setupDateInputs();
    setupMessageSystem();
    checkAuthStatus();
});

function setupDateInputs() {
    const today = new Date().toISOString().split('T')[0];
    const dateInputs = document.querySelectorAll('input[type="date"]');
    console.log("setting up date inputs with min date:");
    dateInputs.forEach(input => {
        input.min = today;
        // Prevent selecting weekends: if user picks a weekend, clear and show message
        input.addEventListener('change', (e) => {
            const val = e.target.value;
            if (!val) return;
            // Add T00:00:00 to avoid timezone issues where it might become the previous day
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
    // This assumes `authToken` is defined elsewhere, e.g., in api.js
    if (authToken) {
        showMainContent();
        loadUserData();
    } else {
        showLoginForm();
    }
}


// --- Auth UI Functions ---
function showLoginForm() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('adminPanel').style.display = 'none';
    document.getElementById('logoutBtn').style.display = 'none';
    document.getElementById('loginBtn').style.display = 'inline-block';
    document.getElementById('signupBtn').style.display = 'inline-block';

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
    authToken = null; // Assuming authToken is a global variable from another script
    currentUser = null;
    showLoginForm();
}


// --- Main Content UI Functions ---
function showMainContent() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'none';
    document.getElementById('mainContent').style.display = 'block';
    document.getElementById('logoutBtn').style.display = 'inline-block';
    document.getElementById('loginBtn').style.display = 'none';
    document.getElementById('signupBtn').style.display = 'none';


    const gameSelect = document.getElementById('gameSelect');
    const dateSelect = document.getElementById('dateSelect');
    const viewSlotsBtn = document.getElementById('viewSlotsBtn');

    if (gameSelect && dateSelect && viewSlotsBtn) {
        const updateSlotsHandler = () => {
            if (gameSelect.value && dateSelect.value) {
                loadSlots();
            }
        };
        gameSelect.removeEventListener('change', updateSlotsHandler); // Prevent duplicate listeners
        dateSelect.removeEventListener('change', updateSlotsHandler);
        viewSlotsBtn.removeEventListener('click', loadSlots);

        gameSelect.addEventListener('change', updateSlotsHandler);
        dateSelect.addEventListener('change', updateSlotsHandler);
        viewSlotsBtn.addEventListener('click', loadSlots);
    }

    loadGames();
    loadBookingHistory();
}

async function loadUserData() {
    console.log('Loading user data');
    try {
        const user = await apiRequest('/users/me');
        currentUser = user;
        console.log('Logged in as:', user);
        if (user.role === 'admin') {
            document.getElementById('adminPanel').style.display = 'block';
            document.getElementById('mainContent').style.display = 'none'; // Hide main panel for admins
            loadAdminData();
        }
    } catch (error) {
        console.error('Failed to load user data:', error);
        showError('Session expired. Please log in again.');
        logout();
    }
}

async function loadGames() {
    try {
        const games = await getGames();
        const gameSelect = document.getElementById('gameSelect');
        const adminGameSelect = document.getElementById('adminGameSelect');

        gameSelect.innerHTML = '<option value="">Select Game</option>';
        if (adminGameSelect) {
            adminGameSelect.innerHTML = '<option value="">Select Game</option>';
        }

        const activeGames = games.filter(game =>
            game.status === 'active' || (currentUser?.role === 'admin')
        );

        if (activeGames.length === 0) {
            showMessage('No games are currently available.', 'info');
            return;
        }

        activeGames.forEach(game => {
            const status = game.status === 'active' ? '' : ' (Inactive)';
            const maxPlayers = game.max_players ? ` (Max: ${game.max_players})` : '';
            const option = `<option value="${game.id}">${game.name} - ${game.type}${maxPlayers}${status}</option>`;
            gameSelect.insertAdjacentHTML('beforeend', option);
            if (adminGameSelect) {
                adminGameSelect.insertAdjacentHTML('beforeend', option);
            }
        });
    } catch (error) {
        showError('Failed to load games: ' + error.message);
    }
}

async function loadSlots() {
    const gameId = document.getElementById('gameSelect').value;
    const date = document.getElementById('dateSelect').value;
    const slotsContainer = document.getElementById('availableSlots');

    if (!gameId || !date) {
        slotsContainer.innerHTML = '<div class="message-info">Please select both a game and a date to view slots.</div>';
        return;
    }

    try {
        slotsContainer.innerHTML = '<div class="loading">Loading available slots...</div>';
        const formattedDate = new Date(date).toISOString().split('T')[0];
        const slots = await getGameSlots(gameId, formattedDate);
        displaySlots(slots, gameId, formattedDate);
    } catch (error) {
        const errorMessage = error.detail || error.message || 'An unknown error occurred';
        showError('Failed to load slots: ' + errorMessage);
        slotsContainer.innerHTML = `<div class="message-error">Failed to load slots. Please try again.</div>`;
    }
}

function displaySlots(slots, gameId, date) {
    const slotsContainer = document.getElementById('availableSlots');
    slotsContainer.innerHTML = '';

    if (!slots || slots.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        emptyState.innerHTML = `<p>No slots available for the selected date.</p>`;
        
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

    slots.forEach(slot => {
        const startTime = new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const endTime = new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const slotCard = document.createElement('div');
        slotCard.className = 'slot-card';
        if (slot.is_cancelled) slotCard.classList.add('cancelled');
        if (!slot.is_available) slotCard.classList.add('unavailable');

        let status = 'Available';
        if (slot.is_cancelled) {
            status = `Cancelled${slot.cancellation_reason ? ': ' + slot.cancellation_reason : ''}`;
        } else if (!slot.is_available) {
            status = 'Booked';
        }

        const isBookable = !slot.is_cancelled && slot.is_available;
        slotCard.innerHTML = `
            <div class="slot-time">${startTime} - ${endTime}</div>
            <div class="slot-status ${isBookable ? 'status-available' : 'status-booked'}">${status}</div>
            ${isBookable ? `<button class="book-button" onclick="showBookingModal(${slot.id})">Book Now</button>` : ''}
        `;
        slotsGrid.appendChild(slotCard);
    });

    slotsContainer.appendChild(slotsGrid);
}

async function loadBookingHistory() {
    const bookingsList = document.getElementById('bookingsList');
    if (!bookingsList) return;

    try {
        bookingsList.innerHTML = '<div class="loading">Loading your booking history...</div>';
        const bookings = await getBookingHistory();
        displayBookingHistory(bookings);
    } catch (error) {
        const errorMessage = error.detail || error.message || 'An unknown error occurred';
        showError('Failed to load booking history: ' + errorMessage);
        bookingsList.innerHTML = '<div class="message-error">Failed to load booking history.</div>';
    }
}

function displayBookingHistory(bookings) {
    const bookingsList = document.getElementById('bookingsList');
    bookingsList.innerHTML = '';

    if (!bookings || bookings.length === 0) {
        bookingsList.innerHTML = `
            <div class="empty-state">
                <p>You have no bookings yet.</p>
                <p>Select a game and date above to book a slot!</p>
            </div>`;
        return;
    }

    const historyContainer = document.createElement('div');
    historyContainer.className = 'booking-history';

    bookings.sort((a, b) => new Date(b.start_time) - new Date(a.start_time)); // Most recent first

    bookings.forEach(booking => {
        const startTime = new Date(booking.start_time);
        const isUpcoming = startTime > new Date();

        const card = document.createElement('div');
        card.className = `booking-card ${isUpcoming ? 'upcoming' : 'past'}`;
        card.innerHTML = `
            <h3>${booking.game_name}</h3>
            <p class="booking-date">${startTime.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
            <p class="booking-time">${startTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
            ${isUpcoming ? `<button class="cancel-button" onclick="window.handleCancelBooking(${booking.id})">Cancel Booking</button>` : '<span class="past-booking">Past Booking</span>'}
        `;
        historyContainer.appendChild(card);
    });

    bookingsList.appendChild(historyContainer);
}


// --- Modal and Action Functions ---
function showBookingModal(slotId) {
    selectedSlot = slotId;
    document.getElementById('bookingModal').style.display = 'block';
    document.getElementById('bookingDetails').textContent = `Confirm booking for Slot ID: ${slotId}`;
}

function closeBookingModal() {
    document.getElementById('bookingModal').style.display = 'none';
    document.getElementById('otherPlayersSapIds').value = '';
    selectedSlot = null;
}

async function confirmBooking() {
    if (!selectedSlot) return;

    const otherPlayers = document.getElementById('otherPlayersSapIds').value;
    try {
        await createBooking(selectedSlot, otherPlayers);
        closeBookingModal();
        await loadSlots();
        await loadBookingHistory();
        showSuccess('Booking created successfully!');
    } catch (error) {
        showError('Failed to create booking: ' + (error.detail || error.message));
    }
}

// Make the function available in the global scope for the onclick handler
window.handleCancelBooking = async function(bookingId) {
    if (!confirm('Are you sure you want to cancel this booking?')) {
        return;
    }

    try {
        await apiRequest(`/bookings/${bookingId}`, { method: 'DELETE' });
        showSuccess('Booking cancelled successfully');
        await loadBookingHistory();
        await loadSlots(); // Refresh slots in case the current view is affected
    } catch (error) {
        const errorMessage = error.detail || error.message || 'An unknown error occurred';
        showError('Failed to cancel booking: ' + errorMessage);
    }
}


// --- Admin Panel Functions ---
async function loadAdminData() {
    await loadGames(); // Load games into the admin dropdown
    await loadAdminGames(); // Load the list of all games for management
}

function showGameForm() {
    const form = document.getElementById('gameForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function handleCreateGame() {
    const name = document.getElementById('newGameName').value;
    const type = document.getElementById('newGameType').value;
    const maxPlayers = parseInt(document.getElementById('newGameMaxPlayers').value, 10) || 2;

    if (!name || !type) {
        showError('Game name and type are required.');
        return;
    }

    try {
        await createGame(name, type, maxPlayers);
        showSuccess('Game created successfully.');
        // `gamesList` is a container element (div), not a form — `reset()` is only available on HTMLFormElement.
        // Clear the container so it can be repopulated by `loadAdminGames()` below.
        const gamesListEl = document.getElementById('gamesList');
        if (gamesListEl) gamesListEl.innerHTML = '';
        await loadGames();
        await loadAdminGames();
    } catch (err) {
        showError('Failed to create game: ' + (err.detail || err.message));
    }
}

async function loadAdminGames() {
    try {
        const games = await getGames();
        const list = document.getElementById('gamesList');
        list.innerHTML = '';

        if (!games || games.length === 0) {
            list.innerHTML = '<div class="message-info">No games found. Create one above.</div>';
            return;
        }

        games.forEach(game => {
            const div = document.createElement('div');
            div.className = 'admin-game-item';
            div.innerHTML = `
                <span><strong>${game.name}</strong> (${game.type}) - Max: ${game.max_players} - Status: <span class="status-${game.status}">${game.status}</span></span>
                <button class="btn btn-secondary btn-sm" onclick="window.toggleGameStatus(${game.id}, '${game.status}')">Toggle Status</button>
            `;
            list.appendChild(div);
        });
    } catch (err) {
        showError('Failed to load the list of games.');
        console.error('Failed to load admin games', err);
    }
}

/**
 * FIX: This function is attached to the `window` object to make it globally accessible
 * from the inline `onclick` handler. It is an `async` function to ensure that the UI
 * refresh calls (`loadGames` and `loadAdminGames`) only execute after the API call
 * to `updateGameStatus` has successfully completed.
 */
window.toggleGameStatus = async function(gameId, currentStatus) {
    try {
        const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
        await updateGameStatus(gameId, newStatus);
        showSuccess('Game status updated successfully.');
        await loadGames(); // Refresh dropdowns
        await loadAdminGames(); // Refresh admin list
    } catch (err) {
        showError('Failed to update game status: ' + (err.detail || err.message));
    }
}

async function generateSlotsForDate(gameId, date) {
    try {
        const formattedDate = new Date(date).toISOString().split('T')[0];
        await generateSlotsForGame(gameId, formattedDate);
        showSuccess('Slots generated successfully!');
        await loadSlots(); // Refresh the slots display on the main page
    } catch (error) {
        const errorMessage = error.detail || error.message || 'An unknown error occurred';
        showError('Failed to generate slots: ' + errorMessage);
    }
}

async function generateSlots() {
    const gameId = document.getElementById('adminGameSelect').value;
    const date = document.getElementById('adminDateSelect').value;
    
    if (!gameId || !date) {
        showError('Please select both a game and a date.');
        return;
    }
    await generateSlotsForDate(gameId, date);
}

async function cancelSlots() {
    const gameId = document.getElementById('adminGameSelect').value;
    const date = document.getElementById('adminDateSelect').value;
    const reason = prompt('Enter a reason for cancellation (this will be visible to users):');
    
    if (!gameId || !date) {
        showError('Please select a game and date to cancel slots.');
        return;
    }
    if (!reason) {
        showMessage('Cancellation aborted by user.', 'info');
        return;
    }

    try {
        await cancelGameSlots(gameId, date, reason);
        showSuccess('Slots for the selected date have been cancelled.');
    } catch (error) {
        showError('Failed to cancel slots: ' + (error.detail || error.message));
    }
}


// --- Message Display Functions (Globally Scoped) ---
window.showMessage = function(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    if (!container) return;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;
    container.appendChild(messageDiv);
    // Automatically remove the message after 5 seconds
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        setTimeout(() => messageDiv.remove(), 500);
    }, 5000);
};

window.showError = function(message) {
    window.showMessage(message, 'error');
};

window.showSuccess = function(message) {
    window.showMessage(message, 'success');
};