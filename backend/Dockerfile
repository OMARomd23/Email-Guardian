# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the files
COPY . .

# Expose port (Cloud Run uses PORT env var it sets itself)
ENV PORT=5000
EXPOSE 5000

# Entrypoint
CMD ["python", "app.py"]
