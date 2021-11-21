FROM python:3.10.0-slim

WORKDIR /berit

RUN /bin/bash -c "if [[ "$(uname -m)" =~ arm ]]; then apt-get update -y && apt-get install -y gcc; fi"
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY berit.py .

ENTRYPOINT ["python", "berit.py"]
