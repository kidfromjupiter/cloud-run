FROM python:3.11-alpine

WORKDIR /app

RUN pip install --upgrade pip
COPY . .
RUN pip install --no-cache-dir -r  requirements.txt

EXPOSE $PORT
CMD ["python","main.py"]
