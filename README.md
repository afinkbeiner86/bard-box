# Bard Box

A web-based soundboard utilizing a Flask backend and Pygame-integrated mixer for real-time local audio playback and dynamic asset mapping.




## Technical Architecture
- **Backend:** Flask (Python) with `pygame.mixer` for local audio execution.
- **Frontend:** HTML5/JavaScript using Fetch API for asynchronous state updates.
- **Storage:** JSON-based persistent mapping for configuration.
- **Networking:** RESTful API endpoints for asset management.

## Setup with uv


```bash
# Install uv
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# Initialize environment and install dependencies
uv venv
uv pip install flask pygame

# Execute application
uv run src/app.py