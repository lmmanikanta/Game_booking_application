// API Configuration
const API_URL = 'http://localhost:8001';
let authToken = localStorage.getItem('authToken');
let isAdmin = false;

// API Helper Functions
async function apiRequest(endpoint, options = {}) {
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    if (authToken) {
        defaultHeaders['Authorization'] = `Bearer ${authToken}`;
    }

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
        });

        if (!response.ok) {
            const errorData = await response.json();
            // Check for token expiration
            if (response.status === 401) {
                localStorage.removeItem('authToken');
                authToken = null;
                location.reload();
            }
            throw new Error(errorData.detail || 'Something went wrong');
        }

        return await response.json();
    } catch (error) {
        showError(error.message);
        throw error;
    }
}

// Authentication API Calls
async function login(username, password) {
    const response = await apiRequest('/users/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    authToken = response.access_token;
    localStorage.setItem('authToken', authToken);
    return response;
}

async function register(email, sapId, password) {
    return await apiRequest('/users/register', {
        method: 'POST',
        body: JSON.stringify({ email, sap_id: sapId, password }),
    });
}

// Game API Calls
async function getGames() {
    return await apiRequest('/games');
}

async function getGameSlots(gameId, date) {
    return await apiRequest(`/games/${gameId}/slots?date=${date}`);
}

// Booking API Calls
async function createBooking(slotId, otherPlayers) {
    return await apiRequest('/bookings', {
        method: 'POST',
        body: JSON.stringify({
            slot_id: slotId,
            other_players: otherPlayers,
        }),
    });
}

async function getBookingHistory() {
    return await apiRequest('/users/bookings/history');
}

async function checkInBooking(bookingId) {
    return await apiRequest(`/bookings/${bookingId}/check-in`, {
        method: 'POST',
    });
}

// Make cancelBooking function globally available
window.cancelBooking = async function(bookingId) {
    return await apiRequest(`/bookings/${bookingId}`, {
        method: 'DELETE',
    });
};

// Also expose a plain global function name to support inline handlers or cached scripts
// This ensures callers using `cancelBooking(...)` (without window.) still work.
function cancelBooking(bookingId) {
    return window.cancelBooking(bookingId);
}

// Admin API Calls
async function createGame(name, type, maxPlayers) {
    return await apiRequest('/admin/games', {
        method: 'POST',
        body: JSON.stringify({ name, type, max_players: maxPlayers }),
    });
}

async function updateGameStatus(gameId, status) {
    return await apiRequest(`/admin/games/${gameId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
    });
}

async function generateSlotsForGame(gameId, date) {
    return await apiRequest('/admin/slots/generate', {
        method: 'POST',
        body: JSON.stringify({
            game_id: gameId,
            date: date
        })
    });
}

async function cancelGameSlots(gameId, date, reason) {
    return await apiRequest('/admin/slots/cancel', {
        method: 'DELETE',
        body: JSON.stringify({ game_id: gameId, date, reason }),
    });
}