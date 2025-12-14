# Use Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/app.py .
COPY src/consumer.py .
COPY src/index.html .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
