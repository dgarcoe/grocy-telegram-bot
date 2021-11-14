FROM python:3.9.7-slim

COPY main.py service/
COPY app/ service/app
COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

WORKDIR service/

CMD ["python","main.py"]