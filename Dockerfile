# 1. Small official Python image
FROM python:3.12-slim

# 2. Working directory inside the container
WORKDIR /app

# 3-4. Copy requirements first (Docker caches this layer) and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the application source (raw data included, cleaned data is rebuilt below)
COPY . .

# Build the cleaned tables + business report inside the image
RUN python run_pipeline.py

# 6. Streamlit port
EXPOSE 8501

# 7. Start the dashboard
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
