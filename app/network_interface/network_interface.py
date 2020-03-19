

class Network:

    def __init__(self, id):
        self.net_id = id
        self.connections = []

    def add_connection(self, connection_id):
        self.connections.append(connection_id)

