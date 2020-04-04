from multiprocessing import Process, Pipe
import os
import threading
import time
import numpy as np

process_number = 3
event_number = 3


def sending_events_thread(pid, event_queue, pipe_list_local, process_id, event_list, lamport_clock, event_total_number):
    print("P%s:PID%s " % (str(process_id), str(pid)))
    print("All the events in the list: ", event_list)

    sending_event_indicator_p1 = 0
    sending_event_indicator_p2 = 0
    sending_event_indicator_p3 = 0

    event_index_p_one = 0
    event_index_p_two = 0
    event_index_p_three = 0

    while True:
        if len(event_queue) == 0 and process_id == 1:
            sending_event_indicator_p1 = 1
            lamport_clock[0] += 1
        elif len(event_queue) == 0 and process_id == 2:
            sending_event_indicator_p2 = 1
            lamport_clock[0] += 1
        elif len(event_queue) == 0 and process_id == 3:
            sending_event_indicator_p3 = 1
            lamport_clock[0] += 1

        if process_id == 1:
            event_index = event_index_p_one
            if event_index < event_total_number:
                if sending_event_indicator_p1 == 1:
                    event_to_send = create_event(pid, event_list[event_index], lamport_clock, process_id)
                    event_with_mark = event_to_send + tuple("1", )
                    event_queue.append(event_with_mark)
                    # print("event_queue", event_queue)
                    # print("")
                    send_messages(pipe_list_local, process_id, event_to_send)
                    event_index_p_one = event_index_p_one + 1
                    sending_event_indicator_p1 = 0
        elif process_id == 2:
            event_index = event_index_p_two
            if event_index < event_total_number:
                if sending_event_indicator_p2 == 1:
                    event_to_send = create_event(pid, event_list[event_index], lamport_clock, process_id)
                    event_with_mark = event_to_send + tuple("1", )
                    event_queue.append(event_with_mark)
                    # print("event_queue", event_queue)
                    # print("")
                    send_messages(pipe_list_local, process_id, event_to_send)
                    sending_event_indicator_p2 = 0
                    event_index_p_two = event_index_p_two + 1
        elif process_id == 3:
            event_index = event_index_p_three
            if event_index < event_total_number:
                if sending_event_indicator_p3 == 1:
                    event_to_send = create_event(pid, event_list[event_index], lamport_clock, process_id)
                    event_with_mark = event_to_send + tuple("1", )
                    event_queue.append(event_with_mark)
                    # print("event_queue", event_queue)
                    # print("")
                    send_messages(pipe_list_local, process_id, event_to_send)
                    sending_event_indicator_p3 = 0
                    event_index_p_three = event_index_p_three + 1


def create_event(pid, event_message, lamport_clock, process_id):
    event = str(pid) + "." + str(event_message)
    timestamp = str(lamport_clock[0]) + "." + str(process_id)
    return event, timestamp


def send_messages(pipe_list_local, process_id, event):
    if process_id == 1:
        pipe_list_local[0][0].send(event)
        pipe_list_local[2][0].send(event)
    elif process_id == 2:
        pipe_list_local[0][1].send(event)
        pipe_list_local[1][0].send(event)
    elif process_id == 3:
        pipe_list_local[2][1].send(event)
        pipe_list_local[1][1].send(event)


def receive_messages(pipe_list_local, process_id):
    received_events = []
    received_acks = []
    received_indicator = []
    time.sleep(7)
    print("")
    print("process_id: ", process_id)

    if process_id == 1:
        received_event_21 = pipe_list_local[0][0].recv()
        # print("received_event_21: ", received_event_21)

        if len(received_event_21) == 1:
            received_indicator.append(received_event_21)
        elif len(received_event_21) == 2:
            received_event_21_list = received_event_21[0].split(".")
            if received_event_21_list[1] == "ack":
                received_acks.append(received_event_21)
            else:
                received_events.append(received_event_21)

        received_event_31 = pipe_list_local[2][0].recv()
        # print("received_event_31: ", received_event_31)

        if len(received_event_31) == 1:
            received_indicator.append(received_event_31)
        elif len(received_event_31) == 2:
            received_event_31_list = received_event_31[0].split(".")
            if received_event_31_list[1] == "ack":
                received_acks.append(received_event_31)
            else:
                received_events.append(received_event_31)
    elif process_id == 2:
        received_event_12 = pipe_list_local[0][1].recv()
        # print("received_event_12: ", received_event_12)

        if len(received_event_12) == 1:
            received_indicator.append(received_event_12)
        elif len(received_event_12) == 2:
            received_event_12_list = received_event_12[0].split(".")
            if received_event_12_list[1] == "ack":
                received_acks.append(received_event_12)
            else:
                received_events.append(received_event_12)
        received_event_32 = pipe_list_local[1][0].recv()
        # print("received_event_32: ", received_event_32)

        if len(received_event_32) == 1:
            received_indicator.append(received_event_32)
        elif len(received_event_32) == 2:
            received_event_32_list = received_event_32[0].split(".")
            if received_event_32_list[1] == "ack":
                received_acks.append(received_event_32)
            else:
                received_events.append(received_event_32)
    elif process_id == 3:
        received_event_13 = pipe_list_local[2][1].recv()
        # print("received_event_13: ", received_event_13)

        if len(received_event_13) == 1:
            received_indicator.append(received_event_13)
        elif len(received_event_13) == 2:
            received_event_13_list = received_event_13[0].split(".")
            if received_event_13_list[1] == "ack":
                received_acks.append(received_event_13)
            else:
                received_events.append(received_event_13)
        received_event_23 = pipe_list_local[1][1].recv()
        # print("received_event_23: ", received_event_23)

        if len(received_event_23) == 1:
            received_indicator.append(received_event_23)
        elif len(received_event_23) == 2:
            received_event_23_list = received_event_23[0].split(".")
            if received_event_23_list[1] == "ack":
                received_acks.append(received_event_23)
            else:
                received_events.append(received_event_23)
    return received_events, received_acks, received_indicator


def pipe_ack_send(pipe_list_local, pipe_send_id, pipe_receive_id, ack_message):
    if pipe_send_id == 1 and pipe_receive_id == 2:
        pipe_list_local[0][0].send(ack_message)
    elif pipe_send_id == 2 and pipe_receive_id == 1:
        pipe_list_local[0][1].send(ack_message)
    elif pipe_send_id == 2 and pipe_receive_id == 3:
        pipe_list_local[1][0].send(ack_message)
    elif pipe_send_id == 3 and pipe_receive_id == 2:
        pipe_list_local[1][1].send(ack_message)
    elif pipe_send_id == 1 and pipe_receive_id == 3:
        pipe_list_local[2][0].send(ack_message)
    elif pipe_send_id == 3 and pipe_receive_id == 1:
        pipe_list_local[2][1].send(ack_message)


def create_ack_message(pid, lamport_clock, process_id):
    ack_body = str(pid) + "." + "ack"
    timestamp = str(lamport_clock[0]) + "." + str(process_id)
    return ack_body, timestamp


def delivery_event(event_message, process_id):
    print("delivered event: ", event_message)
    current_procee_id = process_id
    sending_process_id = event_message[1].split(".")[1]
    event_id = event_message[0].split(".")[1]
    message_to_print = str(current_procee_id) + ":" + str(sending_process_id) + "." + str(event_id)
    print(message_to_print)


def send_sending_indicator(pipe_list_local, process_id):
    if process_id == 1:
        pipe_list_local[0][0].send(str(process_id))
        pipe_list_local[2][0].send(str(process_id))
    elif process_id == 2:
        pipe_list_local[0][1].send(str(process_id))
        pipe_list_local[1][0].send(str(process_id))
    elif process_id == 3:
        pipe_list_local[2][1].send(str(process_id))
        pipe_list_local[1][1].send(str(process_id))


def send_ack(pid, pipe_list_local, updated_event_queue, process_id, lamport_clock, full_ack):
    pop_queue = 0
    # total_ordered_queue = []
    if full_ack == 0:
        length_updated_event_queue = len(updated_event_queue)
        for queue_ack_i in range(length_updated_event_queue):
            queue_list = updated_event_queue[queue_ack_i][1].split(".")
            if int(queue_list[1]) < process_id:
                lamport_clock[0] += 1
                ack_message = create_ack_message(pid, lamport_clock, process_id)
                pipe_ack_send(pipe_list_local, process_id, int(queue_list[1]), ack_message)
                ack_num = str(int(updated_event_queue[queue_ack_i][-1]) + 1)
                switched_event = (updated_event_queue[queue_ack_i][0],) + (updated_event_queue[queue_ack_i][1],) + (
                    ack_num,)
                del updated_event_queue[queue_ack_i]
                updated_event_queue.insert(pop_queue, switched_event)
                pop_queue += 1
    elif full_ack == 1:
        for queue_full_ack_i in range(len(updated_event_queue)):
            queue_full_ack_list = updated_event_queue[queue_full_ack_i][1].split(".")
            lamport_clock[0] += 1
            full_ack_message = create_ack_message(pid, lamport_clock, process_id)
            pipe_ack_send(pipe_list_local, process_id, int(queue_full_ack_list[1]), full_ack_message)
            pop_queue += 1

    return pop_queue


def communication_thread(pid, event_queue, pipe_list_local, process_id, lamport_clock):
    while True:
        received_events, received_acks, _ = receive_messages(pipe_list_local, process_id)

        if len(received_events) == 0 and len(received_acks) == 0:
            continue

        print("received events " + str(pid), received_events)

        for event_i in range(len(received_events)):
            received_event_list = received_events[event_i][1].split(".")
            received_clock = int(received_event_list[0])
            if lamport_clock[0] < (received_clock + 1):
                lamport_clock[0] += 1
            lamport_clock[0] += 1
            new_event = (received_events[event_i][0],) + (str(lamport_clock[0]) + "." + received_event_list[1],) + (
            "0",)
            event_queue.append(new_event)

        print("event_queue: ", event_queue)

        pop_queue_del = send_ack(pid, pipe_list_local, event_queue, process_id, lamport_clock, 0)
        print("The number of acks should sent by P%s(PID:%s) is %d: " % (str(process_id), str(pid), pop_queue_del))
        print("event_queue: ", event_queue)

        while pop_queue_del:
            delivery_event(event_queue[0], process_id)
            del event_queue[0]
            pop_queue_del -= 1

        while len(event_queue):
            received_events, received_acks, _ = receive_messages(pipe_list_local, process_id)
            new_top_event_queue = tuple()
            if len(received_acks) != 0:
                for ack_index in range(len(received_acks)):
                    received_acks_list = received_acks[ack_index][0].split(".")
                    if received_acks_list[1] == "ack":
                        new_ack_number = int(event_queue[0][2]) + 1
                        new_top_event_queue = (event_queue[0][0],) + (event_queue[0][1],) + (str(new_ack_number),)
                        del event_queue[0]
                        event_queue.insert(0, new_top_event_queue)
            print("event_queue: ", event_queue)

            if int(event_queue[0][2]) == process_number:
                delivery_event(event_queue[0], process_id)
                del event_queue[0]
                length_of_event_queue = len(event_queue)
                lamport_clock[0] += 1
                _ = send_ack(pid, pipe_list_local, event_queue, process_id, lamport_clock, 1)

                for full_ack_index_del in range(length_of_event_queue):
                    delivery_event(event_queue[0], process_id)
                    del event_queue[0]


def process1(pipe_list_local):
    current_pid = os.getpid()
    process_id = 1

    event_list_process_1 = [x for x in range(0, event_number)]
    lamport_clock = [0]
    event_queue = []
    thread_send = threading.Thread(target=sending_events_thread, args=(
        current_pid, event_queue, pipe_list_local, process_id, event_list_process_1, lamport_clock, event_number))

    thread_communicate = threading.Thread(target=communication_thread,
                                          args=(current_pid, event_queue, pipe_list_local, process_id, lamport_clock))
    # time.sleep(15)
    thread_send.start()
    thread_communicate.start()

    thread_send.join()
    thread_communicate.join()


def process2(pipe_list_local):
    current_pid = os.getpid()
    event_list_process_2 = [x for x in range(20, 20 + event_number)]
    process_id = 2
    lamport_clock = [0]
    event_queue = []

    thread_send = threading.Thread(target=sending_events_thread, args=(
        current_pid, event_queue, pipe_list_local, process_id, event_list_process_2, lamport_clock, event_number))
    time.sleep(2)

    thread_communicate = threading.Thread(target=communication_thread,
                                          args=(current_pid, event_queue, pipe_list_local, process_id, lamport_clock))

    thread_send.start()
    thread_communicate.start()

    thread_send.join()
    thread_communicate.join()


def process3(pipe_list_local):
    current_pid = os.getpid()
    event_list_process_3 = [x for x in range(40, 40 + event_number)]
    process_id = 3
    lamport_clock = [0]
    event_queue = []

    thread_send = threading.Thread(target=sending_events_thread, args=(
        current_pid, event_queue, pipe_list_local, process_id, event_list_process_3, lamport_clock, event_number))
    time.sleep(4)

    thread_communicate = threading.Thread(target=communication_thread,
                                          args=(current_pid, event_queue, pipe_list_local, process_id, lamport_clock))

    thread_send.start()
    thread_communicate.start()

    thread_send.join()
    thread_communicate.join()


pipe_list = []

for pipe_index in range(process_number):
    (pipe_send, pipe_recv) = Pipe()
    pipe_list.append((pipe_send, pipe_recv))

print(pipe_list)

P1 = Process(target=process1, args=(pipe_list,))
P2 = Process(target=process2, args=(pipe_list,))
P3 = Process(target=process3, args=(pipe_list,))

P1.start()
P2.start()
P3.start()

P1.join()
P2.join()
P3.join()