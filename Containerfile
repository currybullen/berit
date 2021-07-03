FROM docker.io/python:3.10.0-slim

WORKDIR /berit

RUN apt-get update -y && apt-get install -y gcc
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY berit.py .

CMD ["python", "berit.py"]
