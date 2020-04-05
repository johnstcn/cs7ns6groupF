FROM python:3
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./booking /app/booking
EXPOSE 5000/tcp
ENV QUORUM_WRITE 3
ENV QUORUM_READ 1
WORKDIR /app/booking
CMD ./ipc.py --id $PEER_ID --peers $PEERS --quorum_write $QUORUM_WRITE --quorum_read $QUORUM_READ
