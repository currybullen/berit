FROM python:3.9.2-slim

WORKDIR /berit

COPY requirements.txt .

RUN /bin/bash -c "if [[ "$(uname -m)" =~ arm ]]; then apt-get update -y && apt-get install -y gcc; fi"
RUN pip install -r requirements.txt

COPY berit.py .

# Needs token env variable or arg
# Needs --channel argument
ENTRYPOINT ["python", "berit.py"]
