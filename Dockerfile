# Stage 2: Build the final image with Python backend and static frontend
FROM python:3.12-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python backend code
COPY main.py .
COPY api ./api
COPY yfinance_client.py .
COPY config.py .
COPY indicators.py .

# Copy the main application
COPY main.py ./

# Expose port 8000 to allow communication to the app
EXPOSE 8000

# Command to run the application when the container launches.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]