# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching.
# This way, dependencies are only re-installed if requirements.txt changes.
COPY requirements.txt .

# Install any needed system dependencies and then the Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Expose the port that Chainlit runs on
EXPOSE 8000

# The command to run the application
# We use "--host 0.0.0.0" to make it accessible outside the container
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0"]