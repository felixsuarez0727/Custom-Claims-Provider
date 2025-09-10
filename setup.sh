#!/bin/bash

# Custom Claims Provider - Automated Setup Script
echo "🚀 Setting up Custom Claims Provider with Docker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_error "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    print_error "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

print_step "1. Verifying project structure..."

# Check if required directories exist
if [ ! -d "Custom-Claims-Back-end" ]; then
    print_error "Custom-Claims-Back-end directory not found!"
    print_error "Please ensure the project structure is correct."
    exit 1
fi

if [ ! -d "Custom-Claims-Front-end" ]; then
    print_error "Custom-Claims-Front-end directory not found!"
    print_error "Please ensure the project structure is correct."
    exit 1
fi

print_status "✅ Project structure verified"

print_step "2. Checking required files..."

# Check backend files
required_backend_files=("main.py" "requirements.txt" "Dockerfile")
for file in "${required_backend_files[@]}"; do
    if [ -f "Custom-Claims-Back-end/$file" ]; then
        print_status "✅ Backend: $file found"
    else
        print_error "❌ Backend: $file not found"
        exit 1
    fi
done

# Check frontend files
required_frontend_files=("test.html" "nginx.conf" "frontend-integration.js")
for file in "${required_frontend_files[@]}"; do
    if [ -f "Custom-Claims-Front-end/$file" ]; then
        print_status "✅ Frontend: $file found"
    else
        print_error "❌ Frontend: $file not found"
        exit 1
    fi
done

print_step "3. Creating additional directories..."

# Create logs directory if it doesn't exist
mkdir -p Custom-Claims-Back-end/logs
mkdir -p Custom-Claims-Front-end/static

print_status "✅ Directories created"

print_step "4. Checking environment configuration..."

# Check if .env exists and has required variables
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    
    cat > .env << 'EOF'
# Azure Configuration - REQUIRED
AZURE_CLIENT_ID=your-client-id-here
AZURE_TENANT_ID=b8e62cd3-6661-4faa-91f3-ffe016db96e8

# Ngrok Configuration - REQUIRED (get free token at ngrok.com)
NGROK_AUTHTOKEN=your-ngrok-token-here

# Application Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=your-secret-key-for-jwt-validation

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000

# Docker Network Configuration
COMPOSE_PROJECT_NAME=custom-claims-provider
EOF
    
    print_warning "⚠️  Please edit .env file with your configuration:"
    print_warning "   - Set AZURE_CLIENT_ID with your Azure app client ID"
    print_warning "   - Set NGROK_AUTHTOKEN (get free token at https://ngrok.com)"
    print_warning ""
    print_warning "Press Enter after configuring .env to continue..."
    read -r
else
    print_status "✅ .env file exists"
    
    # Check if critical variables are set
    if grep -q "your-client-id-here" .env; then
        print_warning "⚠️  AZURE_CLIENT_ID not configured in .env"
    fi
    
    if grep -q "your-ngrok-token-here" .env; then
        print_warning "⚠️  NGROK_AUTHTOKEN not configured in .env"
    fi
fi

print_step "5. Building Docker images..."

# Stop any existing containers
docker-compose down 2>/dev/null

# Build the application
docker-compose build

if [ $? -eq 0 ]; then
    print_status "✅ Docker images built successfully"
else
    print_error "❌ Failed to build Docker images"
    print_error "Check the logs above for details"
    exit 1
fi

print_step "6. Starting services..."

# Start services in detached mode
docker-compose up -d

if [ $? -eq 0 ]; then
    print_status "✅ Services started successfully!"
else
    print_error "❌ Failed to start services"
    print_error "Run 'docker-compose logs' to see error details"
    exit 1
fi

# Wait for services to start
print_status "Waiting for services to initialize..."
sleep 15

print_step "7. Checking service health..."

# Check backend API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "✅ Backend API is healthy and responding"
else
    print_warning "⚠️  Backend API might still be starting up"
    print_warning "   Check with: docker-compose logs custom-claims-api"
fi

# Check frontend
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_status "✅ Frontend is serving content"
else
    print_warning "⚠️  Frontend might still be starting up"
    print_warning "   Check with: docker-compose logs frontend"
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_status "✅ Redis is responding"
else
    print_warning "⚠️  Redis might be starting up"
    print_warning "   Check with: docker-compose logs redis"
fi

echo ""
print_status "🎉 Setup completed successfully!"
echo ""
echo "📁 Project structure:"
echo "   CUSTOM-CLAIMS-PROVIDER/"
echo "   ├── Custom-Claims-Back-end/    # FastAPI backend"
echo "   ├── Custom-Claims-Front-end/   # Nginx frontend"
echo "   ├── docker-compose.yml         # Services orchestration"
echo "   └── .env                       # Configuration"
echo ""
echo "🌐 Service URLs:"
echo "   - Frontend Application: http://localhost:3000"
echo "   - Backend API:          http://localhost:8000"
echo "   - API Documentation:    http://localhost:8000/docs"
echo "   - Health Check:         http://localhost:8000/health"
echo "   - Ngrok Dashboard:      http://localhost:4040"
echo ""
echo "📋 Next steps:"
echo "   1. ✅ Open http://localhost:3000 to test the application"
echo "   2. ✅ Check ngrok dashboard at http://localhost:4040 for public URL"
echo "   3. ✅ Configure Microsoft Entra with the ngrok URL"
echo "   4. ✅ Test the complete authentication flow"
echo ""
echo "🔧 Useful commands:"
echo "   - View all logs:        docker-compose logs -f"
echo "   - View backend logs:    docker-compose logs -f custom-claims-api"
echo "   - View frontend logs:   docker-compose logs -f frontend"
echo "   - Stop services:        docker-compose down"
echo "   - Restart services:     docker-compose restart"
echo "   - Rebuild everything:   docker-compose build --no-cache"
echo ""

# Show running containers
print_step "8. Running containers:"
docker-compose ps

echo ""
if command -v open &> /dev/null; then
    print_status "💡 Opening frontend application in browser..."
    open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
    print_status "💡 Opening frontend application in browser..."
    xdg-open http://localhost:3000
else
    print_status "💡 Open http://localhost:3000 in your browser to start testing!"
fi

echo ""
print_status "🚀 Ready to test Custom Claims Provider!"