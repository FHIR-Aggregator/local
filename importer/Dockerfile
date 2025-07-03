
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY import_fhir_data.py .
ENTRYPOINT ["python", "import_fhir_data.py"]
