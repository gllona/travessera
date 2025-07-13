"""
Pet-Veterinary Appointment Client

A client application using Travessera to interact with the pet-veterinary service.
Provides business logic for finding and booking veterinary appointments.
"""

import asyncio
import math
import sys
from datetime import datetime, timedelta

from pydantic import BaseModel

from travessera import Service, Travessera


# Models (matching server models)
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
    preferred_date: str
    reason: str


class Appointment(BaseModel):
    id: str
    pet_id: str
    veterinarian_id: str
    scheduled_date: str
    reason: str
    status: str
    created_at: str


# Configure Travessera
vet_service = Service(
    name="vet-service",
    base_url="http://vet-server:8000",
    timeout=30.0,
    headers={"X-Client": "pet-appointment-client"},
)

travessera = Travessera(
    services=[vet_service], default_headers={"User-Agent": "Travessera-PetClient/1.0"}
)


# Define API endpoints using Travessera decorators
@travessera.get("vet-service", "/pets")
async def get_pets(
    species: str | None = None, district: str | None = None
) -> list[Pet]:
    """Get list of pets with optional filtering"""
    pass


@travessera.get("vet-service", "/pets/{pet_id}")
async def get_pet(pet_id: str) -> Pet:
    """Get a specific pet by ID"""
    pass


@travessera.get("vet-service", "/veterinarians")
async def get_veterinarians(
    specialty: str | None = None,
    district: str | None = None,
    min_rating: float | None = None,
) -> list[Veterinarian]:
    """Get list of veterinarians with optional filtering"""
    pass


@travessera.get("vet-service", "/veterinarians/{vet_id}")
async def get_veterinarian(vet_id: str) -> Veterinarian:
    """Get a specific veterinarian by ID"""
    pass


@travessera.post("vet-service", "/appointments")
async def create_appointment(appointment: AppointmentRequest) -> Appointment:
    """Create a new appointment"""
    pass


@travessera.get("vet-service", "/appointments")
async def get_appointments(
    pet_id: str | None = None, vet_id: str | None = None
) -> list[Appointment]:
    """Get list of appointments with optional filtering"""
    pass


@travessera.get("vet-service", "/locations/districts")
async def get_districts() -> dict:
    """Get available Barcelona districts"""
    pass


# Business logic functions
def calculate_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate distance between two locations using Haversine formula.
    Returns distance in kilometers.
    """
    # Convert to radians
    lat1, lon1 = math.radians(loc1.latitude), math.radians(loc1.longitude)
    lat2, lon2 = math.radians(loc2.latitude), math.radians(loc2.longitude)

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in kilometers
    r = 6371
    return c * r


async def find_nearest_vets(
    pet: Pet, specialty: str | None = None, max_distance: float = 10.0
) -> list[tuple[Veterinarian, float]]:
    """
    Find veterinarians near a pet's location.

    Returns list of (veterinarian, distance) tuples sorted by distance.
    """
    # Get veterinarians, optionally filtered by specialty
    vets = await get_veterinarians(specialty=specialty)

    # Calculate distances and filter by max_distance
    vet_distances = []
    for vet in vets:
        distance = calculate_distance(pet.location, vet.location)
        if distance <= max_distance:
            vet_distances.append((vet, distance))

    # Sort by distance
    vet_distances.sort(key=lambda x: x[1])
    return vet_distances


async def find_best_vet_for_pet(
    pet: Pet, reason: str = "general checkup"
) -> tuple[Veterinarian, float] | None:
    """
    Find the best veterinarian for a pet based on:
    1. Species specialty match
    2. Distance from pet
    3. Veterinarian rating
    """
    print(f"\n🔍 Finding best veterinarian for {pet.name} ({pet.species})...")

    # First, try to find vets specializing in the pet's species
    species_vets = await find_nearest_vets(
        pet, specialty=pet.species, max_distance=15.0
    )

    if species_vets:
        print(f"✅ Found {len(species_vets)} {pet.species} specialists within 15km")
        # Sort by combination of distance and rating (weighted)
        species_vets.sort(
            key=lambda x: x[1] - (x[0].rating * 2)
        )  # Favor higher ratings
        return species_vets[0]

    # If no species specialists, look for general vets
    print(
        f"⚠️  No {pet.species} specialists found nearby, looking for general practitioners..."
    )
    general_vets = await find_nearest_vets(pet, specialty="general", max_distance=20.0)

    if general_vets:
        print(f"✅ Found {len(general_vets)} general practitioners within 20km")
        # Sort by combination of distance and rating
        general_vets.sort(key=lambda x: x[1] - (x[0].rating * 2))
        return general_vets[0]

    # Last resort: any vet within reasonable distance
    print("⚠️  No general practitioners found, expanding search...")
    all_nearby_vets = await find_nearest_vets(pet, max_distance=25.0)

    if all_nearby_vets:
        print(f"✅ Found {len(all_nearby_vets)} veterinarians within 25km")
        all_nearby_vets.sort(key=lambda x: x[1] - (x[0].rating * 1.5))
        return all_nearby_vets[0]

    print("❌ No veterinarians found within reasonable distance")
    return None


async def book_appointment_for_pet(
    pet_name: str, reason: str = "general checkup", days_ahead: int = 7
) -> Appointment | None:
    """
    Complete business logic: find pet by name and book appointment with best available vet.
    """
    print(f"\n🐾 Starting appointment booking process for '{pet_name}'...")

    # 1. Find the pet by name
    print(f"📋 Looking up pet '{pet_name}'...")
    all_pets = await get_pets()
    pet = next((p for p in all_pets if p.name.lower() == pet_name.lower()), None)

    if not pet:
        print(f"❌ Pet '{pet_name}' not found in our system")
        available_pets = [p.name for p in all_pets]
        print(f"Available pets: {', '.join(available_pets)}")
        return None

    print(f"✅ Found {pet.name} - {pet.breed} {pet.species}, owned by {pet.owner_name}")
    print(f"📍 Location: {pet.location.neighborhood}, {pet.location.district}")

    # 2. Find the best veterinarian
    best_match = await find_best_vet_for_pet(pet, reason)

    if not best_match:
        print("❌ No suitable veterinarian found")
        return None

    vet, distance = best_match
    print(f"\n🏥 Best match: Dr. {vet.name}")
    print(f"   📍 Location: {vet.location.neighborhood}, {vet.location.district}")
    print(f"   📏 Distance: {distance:.1f} km from {pet.name}")
    print(f"   🌟 Rating: {vet.rating}/5.0")
    print(f"   🕒 Hours: {vet.available_hours}")
    print(f"   🎯 Specialties: {', '.join(vet.specialties)}")

    # 3. Schedule appointment for specified days ahead
    appointment_date = datetime.now() + timedelta(days=days_ahead)
    appointment_date_str = appointment_date.isoformat()

    print(
        f"\n📅 Scheduling appointment for {appointment_date.strftime('%Y-%m-%d at %H:%M')}"
    )
    print(f"📝 Reason: {reason}")

    # 4. Create the appointment
    appointment_request = AppointmentRequest(
        pet_id=pet.id,
        veterinarian_id=vet.id,
        preferred_date=appointment_date_str,
        reason=reason,
    )

    try:
        appointment = await create_appointment(appointment_request)
        print("\n✅ Appointment successfully created!")
        print(f"   🆔 Appointment ID: {appointment.id}")
        print(f"   📅 Scheduled: {appointment.scheduled_date}")
        print(f"   📊 Status: {appointment.status}")
        return appointment

    except Exception as e:
        print(f"❌ Failed to create appointment: {e}")
        return None


async def show_pet_info(pet_name: str):
    """Display detailed information about a pet"""
    all_pets = await get_pets()
    pet = next((p for p in all_pets if p.name.lower() == pet_name.lower()), None)

    if not pet:
        print(f"❌ Pet '{pet_name}' not found")
        return

    print("\n🐾 Pet Information:")
    print(f"   Name: {pet.name}")
    print(f"   Species: {pet.species}")
    print(f"   Breed: {pet.breed}")
    print(f"   Age: {pet.age} years old")
    print(f"   Owner: {pet.owner_name}")
    print(f"   Location: {pet.location.neighborhood}, {pet.location.district}")


async def list_available_pets():
    """List all available pets in the system"""
    print("\n📋 Available pets in our system:")
    pets = await get_pets()

    for pet in pets:
        print(f"   • {pet.name} ({pet.species}) - {pet.location.district}")


async def list_veterinarians_by_district():
    """List veterinarians grouped by district"""
    print("\n🏥 Available veterinarians by district:")
    vets = await get_veterinarians()

    # Group by district
    districts = {}
    for vet in vets:
        district = vet.location.district
        if district not in districts:
            districts[district] = []
        districts[district].append(vet)

    for district, district_vets in sorted(districts.items()):
        print(f"\n   📍 {district}:")
        for vet in district_vets:
            specialties = ", ".join(vet.specialties)
            print(f"      • Dr. {vet.name} - {specialties} (⭐ {vet.rating})")


async def list_all_appointments():
    """List all appointments in the system"""
    print("\n📋 All appointments in the system:")
    try:
        appointments = await get_appointments()

        if not appointments:
            print("   No appointments found in the system.")
            return

        # Group appointments by status
        appointments_by_status = {}
        for appointment in appointments:
            status = appointment.status
            if status not in appointments_by_status:
                appointments_by_status[status] = []
            appointments_by_status[status].append(appointment)

        for status, status_appointments in sorted(appointments_by_status.items()):
            print(
                f"\n   📊 {status.upper()} Appointments ({len(status_appointments)}):"
            )

            for appointment in sorted(
                status_appointments, key=lambda x: x.scheduled_date
            ):
                # Get pet and vet info for better display
                try:
                    pet = await get_pet(appointment.pet_id)
                    vet = await get_veterinarian(appointment.veterinarian_id)

                    # Format the appointment info
                    scheduled_date = appointment.scheduled_date[:16].replace(
                        "T", " at "
                    )  # Format datetime
                    print(f"      🆔 {appointment.id}")
                    print(
                        f"         🐾 Pet: {pet.name} ({pet.species}) - Owner: {pet.owner_name}"
                    )
                    print(f"         🏥 Vet: Dr. {vet.name} - {vet.location.district}")
                    print(f"         📅 Date: {scheduled_date}")
                    print(f"         📝 Reason: {appointment.reason}")
                    print()

                except Exception:
                    # Fallback if we can't get pet/vet details
                    print(
                        f"      🆔 {appointment.id} - Pet: {appointment.pet_id} - Vet: {appointment.veterinarian_id}"
                    )
                    print(
                        f"         📅 {appointment.scheduled_date} - 📝 {appointment.reason}"
                    )
                    print()

    except Exception as e:
        print(f"❌ Error retrieving appointments: {e}")


async def list_all_districts():
    """List all available districts/locations"""
    print("\n📍 Available districts and locations:")
    try:
        districts_data = await get_districts()

        if not districts_data or "districts" not in districts_data:
            print("   No district information available.")
            return

        districts = districts_data["districts"]
        print(
            f"\n   🏙️  Barcelona has {len(districts)} districts available for veterinary services:"
        )

        for i, district in enumerate(sorted(districts), 1):
            print(f"      {i:2d}. {district}")

        # Also show some location statistics
        print("\n   📊 Location Statistics:")

        # Get all pets and vets to show distribution
        pets = await get_pets()
        vets = await get_veterinarians()

        # Count pets by district
        pet_districts = {}
        for pet in pets:
            district = pet.location.district
            pet_districts[district] = pet_districts.get(district, 0) + 1

        # Count vets by district
        vet_districts = {}
        for vet in vets:
            district = vet.location.district
            vet_districts[district] = vet_districts.get(district, 0) + 1

        print(f"      🐾 Total pets: {len(pets)} across {len(pet_districts)} districts")
        print(
            f"      🏥 Total veterinarians: {len(vets)} across {len(vet_districts)} districts"
        )

        print("\n   📍 District breakdown:")
        all_districts = set(pet_districts.keys()) | set(vet_districts.keys())
        for district in sorted(all_districts):
            pets_count = pet_districts.get(district, 0)
            vets_count = vet_districts.get(district, 0)
            print(f"      • {district}: {pets_count} pets, {vets_count} veterinarians")

    except Exception as e:
        print(f"❌ Error retrieving district information: {e}")


async def interactive_demo():
    """Interactive demonstration of the pet appointment system"""
    print("🌟 Welcome to the Pet-Veterinary Appointment System!")
    print("📍 Serving pets and veterinarians across Barcelona, Catalunya")

    while True:
        print("\n" + "=" * 60)
        print("What would you like to do?")
        print("1. Book appointment for a pet")
        print("2. Show pet information")
        print("3. List all available pets")
        print("4. List veterinarians by district")
        print("5. List all appointments")
        print("6. List all districts/locations")
        print("7. Exit")
        print("=" * 60)

        try:
            choice = input("\nEnter your choice (1-7): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if choice == "1":
            try:
                pet_name = input("Enter pet name: ").strip()
                if not pet_name:
                    print("❌ Pet name cannot be empty")
                    continue

                reason = input("Reason for visit (default: general checkup): ").strip()
                if not reason:
                    reason = "general checkup"

                days_str = input("Days ahead to schedule (default: 7): ").strip()
                try:
                    days_ahead = int(days_str) if days_str else 7
                except ValueError:
                    days_ahead = 7

                await book_appointment_for_pet(pet_name, reason, days_ahead)

            except Exception as e:
                print(f"❌ Error booking appointment: {e}")

        elif choice == "2":
            try:
                pet_name = input("Enter pet name: ").strip()
                if pet_name:
                    await show_pet_info(pet_name)
            except Exception as e:
                print(f"❌ Error showing pet info: {e}")

        elif choice == "3":
            try:
                await list_available_pets()
            except Exception as e:
                print(f"❌ Error listing pets: {e}")

        elif choice == "4":
            try:
                await list_veterinarians_by_district()
            except Exception as e:
                print(f"❌ Error listing veterinarians: {e}")

        elif choice == "5":
            try:
                await list_all_appointments()
            except Exception as e:
                print(f"❌ Error listing appointments: {e}")

        elif choice == "6":
            try:
                await list_all_districts()
            except Exception as e:
                print(f"❌ Error listing districts: {e}")

        elif choice == "7":
            print("👋 Thank you for using the Pet-Veterinary Appointment System!")
            break

        else:
            print("❌ Invalid choice. Please enter 1-7.")


async def demo_scenario():
    """Run a pre-defined demo scenario"""
    print("🎬 Running Demo Scenario: Finding vet for Mimi the cat")
    print("=" * 60)

    # Show available pets first
    await list_available_pets()

    # Demo booking for Mimi
    appointment = await book_appointment_for_pet("Mimi", "annual vaccination", 5)

    if appointment:
        print("\n🎉 Demo completed successfully!")
        print(f"Appointment {appointment.id} created for Mimi")


async def main():
    """Main application entry point"""
    # Use async context manager to ensure proper cleanup
    async with travessera:
        if len(sys.argv) > 1 and sys.argv[1] == "--demo":
            await demo_scenario()
        else:
            await interactive_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Application interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
