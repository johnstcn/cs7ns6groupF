from room.room import Room
from network_interface.network_interface import Network

# from room import *
# from network_interface import *

room_config = {
    1: 'Hamilton',
    2: 'O\'Reily',
    3: 'Ussher 1',
    4: 'Ussher 2',
    5: 'Ussher 3'
}


def setup_rooms():
    print("|---* Intitisation Phase *---|")

    print("Loading Rooms...")
    room_list = {}
    for i in range(1, len(room_config)+1):
        room_list.update({room_config[i]: Room(room_config[i])})

    # print(room_list)

    return room_list

# def initialise_bookings(rooms):
#     print("Loading Bookings...")
#     hours_of_day = ['09', '10', '11', '12', '13', '14', '15', '16', '17', '18']
#     mapping_room_hour = {}
#     for room in rooms:
#         mapping_room_hour.update({room.room_name: hours_of_day})
#
#     return mapping_room_hour

def list_all_bookings(list_of_rooms):
    print("|---* ROOMS AVAILABLE *---|")
    for room in list_of_rooms:
        print("Room Name: ", list_of_rooms[room].room_name)
        print("Hours Available: ", list_of_rooms[room].available_hours)


def book_room_at_time(list_of_rooms, room, time):
    if room in list_of_rooms:
        print(list_of_rooms[room].book_time(time))
    else:
        print("Invalid Room")


def del_book_room_at_time(list_of_rooms, room, time):
    print(list_of_rooms[room].del_book_time(time))


def setup_network_interface(network_id):
    print("|---* Initialising Network *---|")
    return Network(network_id)


def add_connection(my_interface, connection_id):
    my_interface.add_connection(connection_id)

