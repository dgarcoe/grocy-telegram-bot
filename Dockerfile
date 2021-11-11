FROM python:3.9.7-slim

COPY app/ app/
COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

CMD ["python","main.py"]