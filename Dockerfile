# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# # Collect static files
# RUN python manage.py collectstatic --noinput

# Expose the port the app runs on
EXPOSE 443

# Set the entrypoint for the container
CMD ["gunicorn", "--bind", "0.0.0.0:443", "--workers", "2", "abroad.wsgi:application"]
