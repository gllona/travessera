# Pet-Veterinary Appointment System

A comprehensive Docker example demonstrating **Travessera** in action with a real-world microservices scenario. This example shows how to use Travessera to transform functions into HTTP API calls, handling complex business logic across distributed services.

## 🏗️ Architecture Overview

This example consists of two microservices communicating via Travessera:

### 🏥 Server Service (`vet-server`)
A **FastAPI** service managing pets, veterinarians, and appointments in Barcelona, Catalunya.

**Endpoints:**
- `GET /pets` - List pets with optional filtering (species, district)
- `GET /pets/{pet_id}` - Get specific pet details
- `GET /veterinarians` - List veterinarians with filtering (specialty, district, rating)
- `GET /veterinarians/{vet_id}` - Get specific veterinarian details
- `POST /appointments` - Create new appointments
- `GET /appointments` - List appointments with filtering
- `GET /locations/districts` - Get available Barcelona districts

### 🐾 Client Service (`vet-client`)
A **Travessera-powered** client providing intelligent appointment booking logic.

**Business Logic:**
1. **Pet Lookup** - Find pets by name
2. **Smart Vet Matching** - Find best veterinarian based on:
   - Species specialty (cats, dogs, etc.)
   - Geographic proximity (Barcelona districts)
   - Veterinarian ratings
   - Availability
3. **Appointment Booking** - Schedule appointments with optimal vet-pet matches

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 2GB available RAM

### 1. Clone and Navigate
```bash
git clone <repository>
cd travessera/examples/docker
```

### 2. Start the Services
```bash
# Start all services
docker compose up --build

# Or start in background
docker compose up --build -d
```

### 3. Wait for Health Checks
The server includes health checks. Wait for this message:
```
pet-vet-server    | INFO: Application startup complete.
```

## 🎮 Usage Examples

### Option 1: Interactive Client
Run the interactive client to manually book appointments:

```bash
# Connect to the interactive client
docker compose exec vet-client python client.py
```

**Interactive Menu:**
```
🌟 Welcome to the Pet-Veterinary Appointment System!
📍 Serving pets and veterinarians across Barcelona, Catalunya

What would you like to do?
1. Book appointment for a pet
2. Show pet information  
3. List all available pets
4. List veterinarians by district
5. Exit
```

### Option 2: Watch the Demo
The demo client runs automatically and shows a complete booking scenario:

```bash
# Watch the demo logs
docker compose logs -f vet-client-demo
```

### Option 3: Server API Explorer
Access the FastAPI automatic documentation:

```bash
# Open in your browser
http://localhost:8000/docs
```

## 📋 Sample Data

### Available Pets
- **Mimi** (Persian cat) - Eixample district
- **Rex** (Golden Retriever) - Gràcia district  
- **Luna** (Siamese cat) - Sarrià-Sant Gervasi district
- **Max** (German Shepherd) - Sant Martí district
- **Whiskers** (Maine Coon cat) - Ciutat Vella district

### Available Veterinarians
- **Dr. Carles Puig** - General/Surgery specialist in Eixample (⭐ 4.8)
- **Dr. Montserrat Vila** - Cat/Exotic specialist in Gràcia (⭐ 4.9)
- **Dr. Jordi Camps** - Dog/Orthopedics specialist in Sarrià (⭐ 4.7)
- **Dr. Núria Soler** - General/Dentistry specialist in Ciutat Vella (⭐ 4.6)
- **Dr. Marc Ribas** - Emergency/Surgery specialist in Sants (⭐ 4.9, 24/7)

### Barcelona Districts Covered
- Eixample (Dreta de l'Eixample)
- Gràcia (Vila de Gràcia)
- Sarrià-Sant Gervasi (Sarrià)
- Sant Martí (Poblenou)
- Ciutat Vella (Barri Gòtic)
- Sants-Montjuïc (Sants)

## 🔍 How Travessera Works in This Example

### 1. Service Configuration
```python
# Configure the veterinary service
vet_service = Service(
    name="vet-service",
    base_url="http://vet-server:8000",
    timeout=30.0,
    headers={"X-Client": "pet-appointment-client"}
)

travessera = Travessera(
    services=[vet_service],
    default_headers={"User-Agent": "Travessera-PetClient/1.0"}
)
```

### 2. Function Transformation
```python
# This function becomes an HTTP GET call automatically
@travessera.get("vet-service", "/pets")
async def get_pets(species: Optional[str] = None, district: Optional[str] = None) -> List[Pet]:
    pass  # No implementation needed!

# This function becomes an HTTP POST call
@travessera.post("vet-service", "/appointments")
async def create_appointment(appointment: AppointmentRequest) -> Appointment:
    pass  # Travessera handles serialization and HTTP communication
```

### 3. Business Logic Usage
```python
# Use the functions as if they were local
pets = await get_pets(species="cat", district="Gràcia")
appointment = await create_appointment(appointment_request)
```

## 🎯 Key Travessera Features Demonstrated

### ✅ Type Safety
- **Pydantic models** for request/response validation
- **Type hints** throughout the client
- **Automatic serialization/deserialization**

### ✅ Error Handling
- **HTTP status code mapping** to exceptions
- **Network error handling** with retries
- **Graceful degradation** when services are unavailable

### ✅ Configuration Hierarchy
- **Service-level** configuration (base URL, headers, timeout)
- **Global** configuration (default headers, user agent)
- **Request-level** parameter handling

### ✅ Async Support
- **Full async/await** support
- **Concurrent requests** for performance
- **Non-blocking I/O** operations

## 🛠️ Development Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f vet-server
docker compose logs -f vet-client
```

### Execute Commands in Containers
```bash
# Access server container
docker compose exec vet-server bash

# Access client container  
docker compose exec vet-client bash

# Run custom client commands
docker compose exec vet-client python client.py --demo
```

### Rebuild Services
```bash
# Rebuild all
docker compose build

# Rebuild specific service
docker compose build vet-client
```

### Stop Services
```bash
# Stop all
docker compose down

# Stop and remove volumes
docker compose down -v
```

## 🧪 Testing the Example

### 1. Manual API Testing
```bash
# Test server health
curl http://localhost:8000/

# Get all pets
curl http://localhost:8000/pets

# Get cats only
curl "http://localhost:8000/pets?species=cat"

# Get veterinarians in Gràcia
curl "http://localhost:8000/veterinarians?district=Gràcia"
```

### 2. Client Business Logic Testing
```bash
# Run interactive session
docker compose exec vet-client python client.py

# Try booking for each pet:
# - Mimi (should find Dr. Montserrat Vila - cat specialist)
# - Rex (should find Dr. Jordi Camps - dog specialist) 
# - Luna (should find Dr. Montserrat Vila - cat specialist)
```

### 3. Demo Scenario
```bash
# Watch automated demo
docker compose logs -f vet-client-demo

# Should show:
# 1. Pet lookup for "Mimi"
# 2. Finding cat specialists near Eixample
# 3. Booking with Dr. Montserrat Vila in Gràcia
# 4. Successful appointment creation
```

## 🔧 Troubleshooting

### Services Won't Start
```bash
# Check if ports are available
netstat -an | grep 8000

# Check Docker resources
docker system df
docker system prune  # if needed
```

### Client Can't Connect to Server
```bash
# Verify server is healthy
docker compose ps
curl http://localhost:8000/

# Check network connectivity
docker compose exec vet-client ping vet-server
```

### Permission Issues
```bash
# Rebuild with no cache
docker compose build --no-cache

# Check file permissions
ls -la examples/docker/
```

## 📚 Learning Outcomes

After running this example, you'll understand:

1. **How Travessera transforms functions** into HTTP API calls
2. **Service configuration** and connection management  
3. **Type-safe API interactions** with Pydantic models
4. **Complex business logic** using multiple API calls
5. **Error handling** and network resilience
6. **Microservices communication** patterns
7. **Docker containerization** of Travessera applications

## 🔮 Extensions

Ideas for extending this example:

1. **Add Authentication** - Implement API key authentication
2. **Add Caching** - Cache veterinarian data for performance
3. **Add Monitoring** - Implement health checks and metrics
4. **Add Database** - Replace in-memory storage with PostgreSQL
5. **Add WebSocket** - Real-time appointment notifications
6. **Add Geographic Search** - More sophisticated location matching
7. **Add Payment Processing** - Complete booking workflow

## 📖 Related Documentation

- [Travessera Main Documentation](../../README.md)
- [Design Document](../../docs/DESIGN.md)
- [CLAUDE.md Development Guide](../../CLAUDE.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**🎉 Enjoy exploring microservices with Travessera!**