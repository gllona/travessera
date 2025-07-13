"""
Pet-Veterinary Appointment Service

A FastAPI server that manages pets, veterinarians, and appointments
in Barcelona, Catalunya.
"""

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Models
class Location(BaseModel):
    district: str
    neighborhood: str
    latitude: float
    longitude: float


class Pet(BaseModel):
    id: str
    name: str
    species: str
    breed: str
    age: int
    owner_name: str
    location: Location


class Veterinarian(BaseModel):
    id: str
    name: str
    specialties: list[str]
    location: Location
    available_hours: str
    rating: float


class AppointmentRequest(BaseModel):
    pet_id: str
    veterinarian_id: str
    preferred_date: str  # ISO format
    reason: str


class Appointment(BaseModel):
    id: str
    pet_id: str
    veterinarian_id: str
    scheduled_date: str
    reason: str
    status: str
    created_at: str


# Sample data for Barcelona locations
BARCELONA_LOCATIONS = [
    Location(
        district="Eixample",
        neighborhood="Dreta de l'Eixample",
        latitude=41.3851,
        longitude=2.1734,
    ),
    Location(
        district="Gràcia",
        neighborhood="Vila de Gràcia",
        latitude=41.4036,
        longitude=2.1585,
    ),
    Location(
        district="Sarrià-Sant Gervasi",
        neighborhood="Sarrià",
        latitude=41.4007,
        longitude=2.1186,
    ),
    Location(
        district="Sant Martí",
        neighborhood="Poblenou",
        latitude=41.4036,
        longitude=2.1967,
    ),
    Location(
        district="Ciutat Vella",
        neighborhood="Barri Gòtic",
        latitude=41.3825,
        longitude=2.1769,
    ),
    Location(
        district="Sants-Montjuïc",
        neighborhood="Sants",
        latitude=41.3785,
        longitude=2.1404,
    ),
]

# Sample pets
PETS = [
    Pet(
        id="pet-1",
        name="Mimi",
        species="cat",
        breed="Persian",
        age=3,
        owner_name="Maria García",
        location=BARCELONA_LOCATIONS[0],
    ),
    Pet(
        id="pet-2",
        name="Rex",
        species="dog",
        breed="Golden Retriever",
        age=5,
        owner_name="Josep Martínez",
        location=BARCELONA_LOCATIONS[1],
    ),
    Pet(
        id="pet-3",
        name="Luna",
        species="cat",
        breed="Siamese",
        age=2,
        owner_name="Anna Fernández",
        location=BARCELONA_LOCATIONS[2],
    ),
    Pet(
        id="pet-4",
        name="Max",
        species="dog",
        breed="German Shepherd",
        age=4,
        owner_name="David López",
        location=BARCELONA_LOCATIONS[3],
    ),
    Pet(
        id="pet-5",
        name="Whiskers",
        species="cat",
        breed="Maine Coon",
        age=6,
        owner_name="Elena Rodríguez",
        location=BARCELONA_LOCATIONS[4],
    ),
]

# Sample veterinarians
VETERINARIANS = [
    Veterinarian(
        id="vet-1",
        name="Dr. Carles Puig",
        specialties=["general", "surgery"],
        location=BARCELONA_LOCATIONS[0],
        available_hours="9:00-18:00",
        rating=4.8,
    ),
    Veterinarian(
        id="vet-2",
        name="Dr. Montserrat Vila",
        specialties=["cats", "exotic pets"],
        location=BARCELONA_LOCATIONS[1],
        available_hours="10:00-19:00",
        rating=4.9,
    ),
    Veterinarian(
        id="vet-3",
        name="Dr. Jordi Camps",
        specialties=["dogs", "orthopedics"],
        location=BARCELONA_LOCATIONS[2],
        available_hours="8:00-16:00",
        rating=4.7,
    ),
    Veterinarian(
        id="vet-4",
        name="Dr. Núria Soler",
        specialties=["general", "dentistry"],
        location=BARCELONA_LOCATIONS[4],
        available_hours="11:00-20:00",
        rating=4.6,
    ),
    Veterinarian(
        id="vet-5",
        name="Dr. Marc Ribas",
        specialties=["emergency", "surgery"],
        location=BARCELONA_LOCATIONS[5],
        available_hours="24/7",
        rating=4.9,
    ),
]

# In-memory appointments storage
appointments_db: list[Appointment] = []

app = FastAPI(
    title="Pet-Veterinary Service",
    description="A service for managing pets, veterinarians, and appointments in Barcelona",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Pet-Veterinary Service is running",
        "location": "Barcelona, Catalunya",
    }


@app.get("/pets", response_model=list[Pet])
async def get_pets(species: str | None = None, district: str | None = None):
    """
    Get list of pets with optional filtering.

    - **species**: Filter by pet species (cat, dog, etc.)
    - **district**: Filter by Barcelona district
    """
    pets = PETS.copy()

    if species:
        pets = [pet for pet in pets if pet.species.lower() == species.lower()]

    if district:
        pets = [
            pet for pet in pets if pet.location.district.lower() == district.lower()
        ]

    return pets


@app.get("/pets/{pet_id}", response_model=Pet)
async def get_pet(pet_id: str):
    """Get a specific pet by ID"""
    pet = next((p for p in PETS if p.id == pet_id), None)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


@app.get("/veterinarians", response_model=list[Veterinarian])
async def get_veterinarians(
    specialty: str | None = None,
    district: str | None = None,
    min_rating: float | None = None,
):
    """
    Get list of veterinarians with optional filtering.

    - **specialty**: Filter by specialty (general, surgery, cats, dogs, etc.)
    - **district**: Filter by Barcelona district
    - **min_rating**: Filter by minimum rating
    """
    vets = VETERINARIANS.copy()

    if specialty:
        vets = [
            vet
            for vet in vets
            if specialty.lower() in [s.lower() for s in vet.specialties]
        ]

    if district:
        vets = [
            vet for vet in vets if vet.location.district.lower() == district.lower()
        ]

    if min_rating:
        vets = [vet for vet in vets if vet.rating >= min_rating]

    return vets


@app.get("/veterinarians/{vet_id}", response_model=Veterinarian)
async def get_veterinarian(vet_id: str):
    """Get a specific veterinarian by ID"""
    vet = next((v for v in VETERINARIANS if v.id == vet_id), None)
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinarian not found")
    return vet


@app.post("/appointments", response_model=Appointment)
async def create_appointment(appointment_request: AppointmentRequest):
    """
    Create a new appointment between a pet and veterinarian.

    Validates that both pet and veterinarian exist before creating the appointment.
    """
    # Validate pet exists
    pet = next((p for p in PETS if p.id == appointment_request.pet_id), None)
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    # Validate veterinarian exists
    vet = next(
        (v for v in VETERINARIANS if v.id == appointment_request.veterinarian_id), None
    )
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinarian not found")

    # Validate date format
    try:
        datetime.fromisoformat(
            appointment_request.preferred_date.replace("Z", "+00:00")
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO format."
        ) from e

    # Create appointment
    appointment = Appointment(
        id=str(uuid4()),
        pet_id=appointment_request.pet_id,
        veterinarian_id=appointment_request.veterinarian_id,
        scheduled_date=appointment_request.preferred_date,
        reason=appointment_request.reason,
        status="scheduled",
        created_at=datetime.now().isoformat(),
    )

    appointments_db.append(appointment)
    return appointment


@app.get("/appointments", response_model=list[Appointment])
async def get_appointments(pet_id: str | None = None, vet_id: str | None = None):
    """
    Get list of appointments with optional filtering.

    - **pet_id**: Filter by pet ID
    - **vet_id**: Filter by veterinarian ID
    """
    appointments = appointments_db.copy()

    if pet_id:
        appointments = [apt for apt in appointments if apt.pet_id == pet_id]

    if vet_id:
        appointments = [apt for apt in appointments if apt.veterinarian_id == vet_id]

    return appointments


@app.get("/appointments/{appointment_id}", response_model=Appointment)
async def get_appointment(appointment_id: str):
    """Get a specific appointment by ID"""
    appointment = next((a for a in appointments_db if a.id == appointment_id), None)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@app.get("/locations/districts")
async def get_districts():
    """Get list of available Barcelona districts"""
    districts = list({loc.district for loc in BARCELONA_LOCATIONS})
    return {"districts": sorted(districts)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
