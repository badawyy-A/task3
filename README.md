## Features

*   Create and list organizations with geographic locations (GeoJSON).
*   Create and list employees associated with organizations.
*   Allow employees to check-in with their current location.
*   Validate check-in location against their organization's location within a configurable distance.
*   Retrieve details for specific employees.
*   Track check-in timestamps.

## Prerequisites

*   Python 3.7+
*   pip (Python package installer)

## Setup & Installation

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Create a `requirements.txt` file with the following content:
    ```txt
    fastapi
    uvicorn[standard]
    pydantic
    geopy
    # python-jose[cryptography] # If you add auth
    # passlib[bcrypt]         # If you add auth
    # python-multipart        # If you use form data
    ```
    Then run:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatively, install them directly:
    ```bash
    pip install fastapi uvicorn pydantic geopy
    ```

## Running the Application

To run the FastAPI application, use Uvicorn:

```bash
uvicorn main:app --reload
