FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create logs directory with proper ownership before copying application code
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Copy the rest of the application (excluding what's in .dockerignore)
COPY . .

# Ensure logs directory has proper permissions even if it gets overwritten
RUN chmod -R 777 /app/logs 

# Run as non-root user for better security
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# The command to run when the container starts
CMD ["python", "home_temperature_control.py"]
