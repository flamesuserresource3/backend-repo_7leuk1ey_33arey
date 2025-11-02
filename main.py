import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document
from schemas import Wish

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Wish API
class WishCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class WishOut(BaseModel):
    id: str
    text: str
    created_at: str


@app.post("/api/wishes", response_model=WishOut)
async def create_wish(payload: WishCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Validate using schema
    _ = Wish(text=payload.text)

    inserted_id = create_document("wish", {"text": payload.text})

    doc = db["wish"].find_one({"_id": __import__("bson").ObjectId(inserted_id)})
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create wish")

    return {
        "id": str(doc.get("_id")),
        "text": doc.get("text", ""),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else datetime.utcnow().isoformat(),
    }


@app.get("/api/wishes", response_model=List[WishOut])
async def list_wishes(limit: int = Query(default=60, ge=1, le=200)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    cursor = (
        db["wish"].find({}).sort("created_at", -1).limit(int(limit))
    )
    wishes = []
    for doc in cursor:
        wishes.append(
            {
                "id": str(doc.get("_id")),
                "text": doc.get("text", ""),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else datetime.utcnow().isoformat(),
            }
        )

    # Return newest first; frontend may reverse if desired
    return wishes


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
