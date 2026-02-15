# Deployment Plan: Forex Intelligence Service to Google Cloud Platform (GCP)


## 1. Dockerize the Application


### Prerequisites


- Docker installed locally
- The `main.py` application and related files.


### Steps


1.  Create a `Dockerfile` (if one doesn't already exist) in the root directory of your project:


    ```dockerfile
    FROM python:3.9-slim-buster


    WORKDIR /app


    COPY requirements.txt requirements.txt
    RUN pip3 install -r requirements.txt --no-cache-dir


    COPY . .


    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    ```


2.  Build the Docker image:


    ```bash
    docker build -t forex-service .
    ```


3.  Run the Docker image locally to test:


    ```bash
    docker run -d --name forex-engine -p 8000:8000 forex-service
    ```


4.  Verify the application is running by accessing it in your browser at `http://localhost:8000/docs`.


5.  Stop the Docker container:


    ```bash
    docker stop forex-engine
    ```


## 2. Set up Google Cloud Platform (GCP)


### Prerequisites


- A Google Cloud Platform account.
- A GCP project.
- Google Cloud SDK (gcloud CLI) installed and configured.


### Steps


1.  Install the Google Cloud SDK: Follow the instructions on the [Google Cloud SDK documentation](https://cloud.google.com/sdk/docs/install).


2.  Initialize the gcloud CLI:


    ```bash
    gcloud init
    ```


3.  Set the project:


    ```bash
    gcloud config set project YOUR_PROJECT_ID
    ```


4.  Enable the necessary APIs:


    ```bash
    gcloud services enable containerregistry.googleapis.com compute.googleapis.com container.googleapis.com
    ```


## 3. Push Docker Image to Google Container Registry (GCR)


### Steps


1.  Tag the Docker image with the GCR repository URL:


    ```bash
    docker tag forex-service gcr.io/YOUR_PROJECT_ID/forex-service
    ```


2.  Authenticate Docker to GCR:


    ```bash
    gcloud auth configure-docker
    ```


3.  Push the tagged image to GCR:


    ```bash
    docker push gcr.io/YOUR_PROJECT_ID/forex-service
    ```


## 4. Deploy to Google Compute Engine (GCE)


### Steps


1.  Create a GCE instance:


    ```bash
    gcloud compute instances create forex-engine-instance \
        --image-family=debian-10 \
        --image-project=debian-cloud \
        --machine-type=e2-medium \
        --zone=us-central1-a \
        --scopes=https://www.googleapis.com/auth/cloud-platform
    ```


2.  Configure the instance to pull and run the Docker image from GCR:


    - SSH into the instance:


      ```bash
      gcloud compute ssh forex-engine-instance --zone=us-central1-a
      ```


    - Run the following commands:


      ```bash
      docker run -d -p 8000:8000 gcr.io/YOUR_PROJECT_ID/forex-service
      ```


3.  Set up firewall rules to allow traffic to the application:


    ```bash
    gcloud compute firewall-rules create allow-8000 --allow=tcp:8000
    ```


4.  Verify the application is running by accessing it in your browser at `http://EXTERNAL_IP:8000/docs`.  You can find the external IP in the GCE instance details in the GCP console.


## 5. Configure Monitoring and Logging


### Steps


1.  Go to the Stackdriver Monitoring and Logging dashboards in the GCP console.


2.  Configure metrics and alerts as needed.


## 6. Set up CI/CD (Optional)


### Steps


1.  Set up Cloud Build to automatically build and push the Docker image to GCR whenever changes are made to the code repository.


2.  Configure the GCE instance to pull the latest image on startup.


Replace `YOUR_PROJECT_ID` with your actual Google Cloud Project ID.


This detailed plan should help you containerize and deploy your Forex Intelligence Service to GCP!
