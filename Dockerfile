FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port (local_qa_app.py uses 8765)
EXPOSE 8765

# Run the local QA app
CMD ["python", "local_qa_app.py"]
