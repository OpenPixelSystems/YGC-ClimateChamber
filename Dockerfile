FROM python:3.9-slim

WORKDIR /

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "run.py"]