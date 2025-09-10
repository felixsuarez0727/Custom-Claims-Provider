from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import time
import os
import jwt
import redis
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Custom Claims Provider", 
    version="1.0.0",
    description="Microsoft Entra Custom Claims Provider for injecting frontend data into tokens"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "your-client-id")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "your-tenant-id")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Redis connection
try:
    redis_client = redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        db=REDIS_DB, 
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except (redis.ConnectionError, redis.TimeoutError) as e:
    print(f"Redis connection failed: {e}")
    print("Falling back to in-memory storage")
    redis_client = None

# Fallback storage if Redis is not available
frontend_data_store = {}

# Helper functions for storage
def store_data(key: str, data: dict, expiration: int = 300):
    """Store data with expiration (default 5 minutes)"""
    try:
        if redis_client:
            redis_client.setex(key, expiration, json.dumps(data))
        else:
            # Fallback to memory with timestamp for manual expiration
            data['_timestamp'] = time.time()
            frontend_data_store[key] = data
        return True
    except Exception as e:
        print(f"Error storing data: {e}")
        return False

def get_data(key: str) -> Optional[dict]:
    """Get data from storage"""
    try:
        if redis_client:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        else:
            # Fallback with manual cleanup of expired data
            data = frontend_data_store.get(key)
            if data and time.time() - data.get('_timestamp', 0) > 300:
                del frontend_data_store[key]
                return None
            return data
    except Exception as e:
        print(f"Error getting data: {e}")
        return None

def delete_data(key: str):
    """Delete data from storage"""
    try:
        if redis_client:
            redis_client.delete(key)
        else:
            frontend_data_store.pop(key, None)
        return True
    except Exception as e:
        print(f"Error deleting data: {e}")
        return False

def get_storage_stats() -> dict:
    """Get storage statistics"""
    try:
        if redis_client:
            info = redis_client.info()
            return {
                "type": "redis",
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        else:
            # Clean expired data before counting
            current_time = time.time()
            expired_keys = [
                key for key, data in frontend_data_store.items()
                if current_time - data.get('_timestamp', 0) > 300
            ]
            for key in expired_keys:
                del frontend_data_store[key]
                
            return {
                "type": "memory",
                "connected": True,
                "stored_items": len(frontend_data_store),
                "cleaned_expired": len(expired_keys)
            }
    except Exception as e:
        return {
            "type": "unknown",
            "connected": False,
            "error": str(e)
        }

security = HTTPBearer()

# Data models
class FrontendData(BaseModel):
    user_id: str
    business_unit: str
    device_info: str
    custom_data: Optional[str] = None
    timestamp: float

class AuthenticationContext(BaseModel):
    user: Dict[str, Any]
    correlationId: str
    client: Dict[str, Any]
    protocol: str
    clientServicePrincipal: Dict[str, Any]
    resourceServicePrincipal: Dict[str, Any]

class TokenIssuanceEventData(BaseModel):
    authenticationContext: AuthenticationContext

class TokenIssuanceEvent(BaseModel):
    type: str
    data: TokenIssuanceEventData

class ClaimsResponse(BaseModel):
    data: Dict[str, Any]

# Endpoint for frontend to store data temporarily
@app.post("/api/store-frontend-data")
async def store_frontend_data(frontend_data: FrontendData):
    """
    Endpoint for frontend to store data before authentication
    """
    try:
        # Prepare data to store
        data_to_store = {
            "business_unit": frontend_data.business_unit,
            "device_info": frontend_data.device_info,
            "custom_data": frontend_data.custom_data,
            "timestamp": time.time()
        }
        
        # Store data with expiration (5 minutes)
        success = store_data(frontend_data.user_id, data_to_store, 300)
        
        if success:
            return {
                "success": True,
                "message": "Data stored successfully",
                "user_id": frontend_data.user_id,
                "expires_in": 300,
                "storage_type": "redis" if redis_client else "memory"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to store data")
            
    except Exception as e:
        print(f"Error in store_frontend_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error storing data: {str(e)}")

# Main endpoint that Entra will call
@app.post("/api/custom-claims")
async def custom_claims_provider(
    event: TokenIssuanceEvent,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Custom Claims Provider endpoint for Microsoft Entra
    """
    try:
        # Validate the Entra token (optional but recommended)
        # In production you should validate the JWT token here
        
        # Extract user information
        user_context = event.data.authenticationContext.user
        user_id = user_context.get("userPrincipalName") or user_context.get("id")
        
        print(f"[INFO] Processing claims for user: {user_id}")
        print(f"[DEBUG] Full event data: {json.dumps(event.dict(), indent=2)}")
        
        # Look for stored frontend data
        stored_data = get_data(user_id)
        
        # Create custom claims
        custom_claims = {
            "apiVersion": "1.0.0",
            "correlationId": event.data.authenticationContext.correlationId,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "custom-claims-provider",
            "storage_type": "redis" if redis_client else "memory"
        }
        
        # Add frontend data if available
        if stored_data:
            custom_claims.update({
                "businessUnit": stored_data.get("business_unit", "Unknown"),
                "deviceInfo": stored_data.get("device_info", "Unknown"),
                "customData": stored_data.get("custom_data", ""),
                "dataSource": "frontend",
                "dataAge": time.time() - stored_data.get("timestamp", time.time())
            })
            
            # Clean data after using
            delete_data(user_id)
            print(f"[INFO] Used and cleaned frontend data for {user_id}")
        else:
            # Default claims if no frontend data
            custom_claims.update({
                "businessUnit": "Default",
                "deviceInfo": "Server-Generated",
                "customData": "No frontend data available",
                "dataSource": "default"
            })
            print(f"[WARN] No frontend data found for {user_id}")
        
        # Response format required by Microsoft Entra
        response = {
            "data": {
                "actions": [{
                    "@odata.type": "microsoft.graph.tokenIssuanceStart.provideClaimsForToken",
                    "claims": custom_claims
                }]
            }
        }
        
        print(f"[INFO] Returning claims: {json.dumps(custom_claims, indent=2)}")
        return response
        
    except Exception as e:
        print(f"[ERROR] Error processing claims: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing claims: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    storage_stats = get_storage_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": ENVIRONMENT,
        "storage": storage_stats,
        "azure_config": {
            "tenant_id": AZURE_TENANT_ID,
            "client_id_configured": bool(AZURE_CLIENT_ID and AZURE_CLIENT_ID != "your-client-id")
        }
    }

# Debug endpoint to view stored data
@app.get("/debug/stored-data")
async def debug_stored_data():
    """
    Debug endpoint to see what data is stored
    """
    try:
        if redis_client:
            # For Redis, get all keys that are not system keys
            keys = redis_client.keys("*")
            stored_data = {}
            for key in keys:
                try:
                    data = redis_client.get(key)
                    if data:
                        stored_data[key] = json.loads(data)
                except json.JSONDecodeError:
                    stored_data[key] = data  # Raw data if not JSON
            
            return {
                "storage_type": "redis",
                "stored_data": stored_data,
                "count": len(stored_data),
                "redis_info": redis_client.info()
            }
        else:
            # For memory, clean expired data first
            current_time = time.time()
            expired_keys = [
                key for key, data in frontend_data_store.items()
                if current_time - data.get('_timestamp', 0) > 300
            ]
            
            for key in expired_keys:
                del frontend_data_store[key]
            
            return {
                "storage_type": "memory",
                "stored_data": frontend_data_store,
                "count": len(frontend_data_store),
                "cleaned_expired": len(expired_keys)
            }
    except Exception as e:
        return {
            "error": str(e),
            "storage_type": "unknown"
        }

# Middleware for logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    print(f"[REQUEST] {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, debug=True)