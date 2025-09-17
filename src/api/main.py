# src/api/main.py

from fastapi import FastAPI
from .routers import purchase_orders

app = FastAPI(
    title="Procurement SKU Analysis API",
    description="An API to serve insights from the procurement data analysis.",
    version="1.0.0"
)

# Include the router from our purchase_orders file
app.include_router(purchase_orders.router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Procurement Analysis API. Visit /docs for documentation."}


