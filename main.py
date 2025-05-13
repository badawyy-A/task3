import uuid
import datetime
from typing import List, Dict, Tuple, Literal, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Body, Path, status
from pydantic import BaseModel, Field, validator
from geopy.distance import geodesic # type: ignore # geopy doesn't have great type hints yet

# --- Configuration ---
# Maximum distance in meters an employee can be from the organization to check in
MAX_CHECKIN_DISTANCE_METERS = 1000 # 1 km - adjust as needed

# --- In-Memory Storage (Replace with a database in a real application) ---
organizations_db: Dict[UUID, 'Organization'] = {}
employees_db: Dict[UUID, 'Employee'] = {}
attendance_db: Dict[UUID, 'Attendance'] = {}

# --- GeoJSON Point Model ---
# Q1: Part of the Organization model requirement
class GeoPoint(BaseModel):
    """Represents a GeoJSON Point."""
    type: Literal["Point"] = "Point"
    coordinates: Tuple[float, float] # (longitude, latitude)

    @validator('coordinates')
    def validate_coordinates(cls, v):
        longitude, latitude = v
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

# --- Model Definitions ---

# Q1: Organization Model
class OrganizationBase(BaseModel):
    name: str = Field(..., example="Example Corp")
    location: GeoPoint

class Organization(OrganizationBase):
    id: UUID = Field(default_factory=uuid.uuid4)

# Employee Model (Implicitly needed for Q4/Q5)
class EmployeeBase(BaseModel):
    name: str = Field(..., example="Jane Doe")
    organization_id: UUID = Field(...) # Link employee to an organization

class Employee(EmployeeBase):
    id: UUID = Field(default_factory=uuid.uuid4)

# Q2: Attendance Model
class AttendanceBase(BaseModel):
    employee_id: UUID
    location: GeoPoint # Employee's location at check-in

class Attendance(AttendanceBase):
    id: UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    organization_id: Optional[UUID] = None # Store which org they checked into (optional but useful)
    distance_meters: Optional[float] = None # Store calculated distance (optional but useful)

# Input Model for Check-in
# Q4: Part of the check-in requirement
class CheckInRequest(BaseModel):
    employee_id: UUID
    location: GeoPoint


# --- FastAPI Application ---
app = FastAPI(
    title="Employee Attendance API",
    description="API for managing organizations, employees, and attendance check-ins.",
    version="1.0.0"
)

# --- Helper Functions ---
def get_employee_or_404(employee_id: UUID) -> Employee:
    employee = employees_db.get(employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee with id {employee_id} not found")
    return employee

def get_organization_or_404(org_id: UUID) -> Organization:
    organization = organizations_db.get(org_id)
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organization with id {org_id} not found")
    return organization

def calculate_distance_meters(point1: GeoPoint, point2: GeoPoint) -> float:
    """Calculates geodesic distance between two GeoPoints in meters."""
    # geopy expects (latitude, longitude)
    coords1 = (point1.coordinates[1], point1.coordinates[0])
    coords2 = (point2.coordinates[1], point2.coordinates[0])
    return geodesic(coords1, coords2).meters

# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Employee Attendance API"}

# Q3: POST /organizations -> Create a new organization
@app.post(
    "/organizations",
    response_model=Organization,
    status_code=status.HTTP_201_CREATED,
    tags=["Organizations"],
    summary="Create a new organization"
)
async def create_organization(org_data: OrganizationBase = Body(...)):
    """
    Creates a new organization with a name and geographic location.

    - **name**: The name of the organization.
    - **location**: A GeoJSON Point object with 'type': 'Point' and 'coordinates': [longitude, latitude].
    """
    new_org = Organization(**org_data.dict())
    if new_org.id in organizations_db:
         # Extremely unlikely with UUID4, but good practice
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization ID conflict")
    organizations_db[new_org.id] = new_org
    return new_org

@app.get(
    "/organizations",
    response_model=List[Organization],
    tags=["Organizations"],
    summary="List all organizations"
)
async def list_organizations():
    """Retrieves a list of all registered organizations."""
    return list(organizations_db.values())


# Q4: POST /attendance/checkin -> Employee checks in
@app.post(
    "/attendance/checkin",
    response_model=Attendance,
    status_code=status.HTTP_201_CREATED,
    tags=["Attendance"],
    summary="Record an employee check-in"
)
async def check_in(check_in_data: CheckInRequest = Body(...)):
    """
    Allows an employee to check in by providing their ID and current location.
    Validates if the employee's location is within the allowed distance
    from their assigned organization's location.

    - **employee_id**: The UUID of the employee checking in.
    - **location**: The employee's current location as a GeoJSON Point.
    """
    # 1. Find the employee
    employee = get_employee_or_404(check_in_data.employee_id)

    # 2. Find the employee's organization
    organization = get_organization_or_404(employee.organization_id)

    # 3. Calculate distance
    distance = calculate_distance_meters(check_in_data.location, organization.location)

    # 4. Validate distance
    if distance > MAX_CHECKIN_DISTANCE_METERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Check-in location is too far from the organization. "
                f"Distance: {distance:.2f}m, Allowed: {MAX_CHECKIN_DISTANCE_METERS}m"
            )
        )

    # 5. Create and store attendance record
    attendance_record = Attendance(
        employee_id=employee.id,
        location=check_in_data.location,
        organization_id=organization.id, # Store org for context
        distance_meters=round(distance, 2) # Store distance for context
    )
    if attendance_record.id in attendance_db:
         # Extremely unlikely with UUID4, but good practice
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance record ID conflict")

    attendance_db[attendance_record.id] = attendance_record
    return attendance_record

@app.get(
    "/attendance",
    response_model=List[Attendance],
    tags=["Attendance"],
    summary="List all attendance records"
)
async def list_attendance():
    """Retrieves a list of all attendance check-in records."""
    return list(attendance_db.values())


# Q5: GET /employees/{employee_id} -> Get employee details
@app.get(
    "/employees/{employee_id}",
    response_model=Employee,
    tags=["Employees"],
    summary="Get details for a specific employee"
)
async def get_employee(
    employee_id: UUID = Path(..., description="The UUID of the employee to retrieve")
):
    """
    Retrieves the details of a specific employee by their UUID.
    """
    employee = get_employee_or_404(employee_id)
    return employee


# --- Additional Endpoint (Needed for Testing Q4/Q5) ---
@app.post(
    "/employees",
    response_model=Employee,
    status_code=status.HTTP_201_CREATED,
    tags=["Employees"],
    summary="Create a new employee"
)
async def create_employee(employee_data: EmployeeBase = Body(...)):
    """
    Creates a new employee and assigns them to an existing organization.

    - **name**: The name of the employee.
    - **organization_id**: The UUID of the organization the employee belongs to.
    """
    # Check if organization exists
    get_organization_or_404(employee_data.organization_id)

    new_employee = Employee(**employee_data.dict())
    if new_employee.id in employees_db:
         # Extremely unlikely with UUID4, but good practice
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee ID conflict")
    employees_db[new_employee.id] = new_employee
    return new_employee

@app.get(
    "/employees",
    response_model=List[Employee],
    tags=["Employees"],
    summary="List all employees"
)
async def list_employees():
    """Retrieves a list of all registered employees."""
    return list(employees_db.values())


# --- How to Run ---
# Save the code as main.py
# Run in terminal: uvicorn main:app --reload
# Open browser to http://127.0.0.1:8000/docs for interactive API documentation.