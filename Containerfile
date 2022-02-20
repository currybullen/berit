FROM docker.io/python:3.10.0-slim

RUN useradd -m python
USER python
WORKDIR /home/python

COPY --chown=python:python requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=python:python berit.py .

ENTRYPOINT ["python", "berit.py"]
