# Gunakan image Python resmi
FROM python:3.11

# Set tempat kerja di dalam server
WORKDIR /code

# Copy daftar library dan instal
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy semua file kodingan Anda ke server
COPY . .

# Jalankan FastAPI di port 7860 (Port standar Hugging Face)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]