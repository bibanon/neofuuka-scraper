FROM python:3.10.5-bullseye
WORKDIR /neofuuka

RUN apt update && apt install libmariadb-dev
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD python scraper.py
