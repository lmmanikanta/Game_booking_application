# moder_ui — Modern frontend for Game Booker

This small frontend is a single-page static UI that talks to the FastAPI backend located in `app/`.

Assumptions
- Backend is running at http://localhost:8000 (change `baseUrl` in `app.js` if different).

Files
- `index.html` — main page
- `styles.css` — styles (gradient, glass cards, canvas background)
- `app.js` — client logic: loads games, slots, booking, login/register

How to use
1. Start the backend (e.g. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`).
2. Serve `moder_ui` folder (open `moder_ui/index.html` in a browser or serve it with a static server).

Notes & next steps
- Small, self-contained UI. It provides basic flows: view games, select date, view slots, book a slot (requires login).
- Improvements: better error handling, pagination, admin flows, forms validation, and accessibility tweaks.
