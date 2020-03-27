FROM python:3
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY booking/ipc.py ./ipc.py
EXPOSE 5000/tcp
CMD ./ipc.py --id $PEER_ID --peers $PEERS
