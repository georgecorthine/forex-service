#!/usr/bin/env python3
import uvicorn

if __name__ == "__main__":
    # Run the FastAPI application using Uvicorn with auto-reload enabled
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)