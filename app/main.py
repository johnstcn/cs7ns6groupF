# !/usr/bin/env python3

from flask import Flask
app = Flask(__name__)

from utils import *

@app.route("/")
def handle_index():
    return "hello"

@app.route("/healthcheck")
def handle_healthcheck():
    return "ok"

@app.route("/unlock", methods=["POST"])
def handle_unlock():
    return "ok"


def main():
    # app.app.run(host="0.0.0.0", port=5000)
    list_of_rooms = setup_rooms()
    network_interface = setup_network_interface('10.10.10.10')
    add_connection(network_interface, '10.10.10.9')
    add_connection(network_interface, '10.10.10.8')
    add_connection(network_interface, '10.10.10.7')

    print("MY Network ID:", network_interface.net_id)
    print("My Connections:", network_interface.connections)

    list_all_bookings(list_of_rooms)
    book_room_at_time(list_of_rooms, 'Hamilton', '10')

    # print("BOOKED:", list_of_rooms['Hamilton'].get_booked_hours())
    # print(list_of_rooms['Hamilton'].book_time('10'))

    del_book_room_at_time(list_of_rooms, 'Hamilton', '10')
    del_book_room_at_time(list_of_rooms, 'Ussher 1', '10')


if __name__ == "__main__":
    main()

