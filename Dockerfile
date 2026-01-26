# Stage 1: Build the React frontend
FROM node:18-alpine AS builder

WORKDIR /app/frontend

# Copy package files and install dependencies to leverage Docker cache
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the static files
RUN npm run build

# ---

# Stage 2: Build the final image with Python backend and static frontend
FROM python:3.12-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python backend code
COPY main.py .
COPY yfinance_client.py .
COPY config.py .
COPY indicators.py .

# Copy the built frontend from the builder stage
COPY --from=builder /app/frontend/build ./static

# Expose port 8000 to allow communication to the app
EXPOSE 8000

# Command to run the application when the container launches.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]