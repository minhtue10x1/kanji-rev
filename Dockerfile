FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and datasets
COPY . .

# Set default production port
ENV PORT=8000
EXPOSE 8000

# Start production server
CMD ["python", "server.py"]
