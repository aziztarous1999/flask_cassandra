FROM python:3.9
ADD . /todo
WORKDIR /todo
RUN pip install -r requirements.txt