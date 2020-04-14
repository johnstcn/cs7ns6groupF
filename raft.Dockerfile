FROM python:3
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./booking/ ./
EXPOSE 5000/tcp
WORKDIR ./
CMD ./raft_example.py --node_id $PEER_ID --port $PORT --host $HOST_NAME --peers $PEERS --random_seed $PEER_ID
