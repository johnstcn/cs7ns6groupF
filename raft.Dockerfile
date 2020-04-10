FROM python:3
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./raft /app/raft
EXPOSE 5000/tcp
WORKDIR /app/raft
CMD ./example.py --node_id $PEER_ID --port $PORT --host $HOST_NAME --peers $PEERS
