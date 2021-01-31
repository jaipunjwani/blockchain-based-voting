FROM python:3
RUN apt-get update
RUN apt-get install build-essential


WORKDIR /usr/local/blockchain-voting
RUN useradd -ms /bin/bash prototype

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "./main.py"]
