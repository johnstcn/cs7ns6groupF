
FIXED_HOURS = ['09', '10', '11', '12', '13', '14', '15', '16', '17', '18']

class Room:

    def __init__(self, room):
        self.room_name = room
        self.available_hours = FIXED_HOURS.copy()


    def get_booked_hours(self):
        return list(set(FIXED_HOURS) - set(self.available_hours))


    def book_time(self, time):
        print("|---* BOOKING A ROOM *---|")
        print("YOU ARE BOOKING", time, "in", str(self.room_name))
        if time in self.available_hours:
            index = self.available_hours.index(time)
            self.available_hours.pop(index)
            return "OK BOOKED: " + str(time) + " in " + str(self.room_name)
        else:
            return "SORRY THAT TIME IS UNAVAILABLE"


    def del_book_time(self, time):
        print("|---* DELETING BOOKING *---|")
        print("YOU ARE DELETING A BOOKING AT", time, "in", str(self.room_name))
        list_of_booked = self.get_booked_hours()
        if time in FIXED_HOURS:                            # If time is within our fixed hours lists
            if time in list_of_booked:                     # If time is in booked hours (that it is possible to delete)
                self.available_hours.append(time)
                self.available_hours.sort()
                print(self.available_hours)
                return "DELETED BOOKING"
            else:
                return "BOOKING IS AVAILABLE"
        else:
            return "invalid booking"
