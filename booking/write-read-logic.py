from __future__ import print_function
from __future__ import with_statement
from __future__ import division
import argparse
import sys
import glob
import os
import time
import threading
import random
from random import randint
import sqlite3
import logging

sys.path.append('gen-py')
sys.path.insert(0, glob.glob('/home/yaoliu/src_code/thrift/lib/py/build/lib.*')[0])

from fileservice import FileStore
from fileservice.ttypes import SystemException, ParticipantID, Status, StatusReport, Transaction, RFile
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.protocol import TProtocol
from thrift.server import TServer

class Participant:
    def __init__(self, participant_name, participant_port, participant_timeout, coorIp, coorPort, Opt):
        self.name = participant_name
        self.port = participant_port
	self.timeout = participant_timeout
        self.isRecover = 0
	self.file = open(self.name + '.log', 'a+')
	self.startTime = time.time()
	self.endTime = time.time()
	self.coordinatorIp = coorIp
	self.coordinatorPort = coorPort
	self.option = Opt

        try:
            self.conn = sqlite3.connect(self.name + '.db')
            self.cur = self.conn.cursor()
            if(os.path.isfile( self.name + '.db') == True):
		self.file.flush()
                self.cur.execute('CREATE TABLE IF NOT EXISTS Info(filename TEXT PRIMARY KEY, content TEXT)')
		self.cur.execute('CREATE TABLE IF NOT EXISTS Backup(filename TEXT PRIMARY KEY, content TEXT)')
            	self.conn.commit()
                self.conn.close()
        except sqlite3.Error, e:
            print("Error %s" % e.args[0])
	    sys.exit(1)
    
    def recover(self):
	last_line = ""
	self.file = open(self.name + '.log', 'r+')
	for line in self.file:
		last_line = line

	para = last_line.split(" ")
	
	# when file is empty or when the coordinator is a clean state do not recover
	if( str(para[-1]) == "" or str(para[-1]) == "GLOBAL_COMMIT\n" or str(para[-1])=="GLOBAL_ABORT\n"):
		print("Participant >>> Do not need to recover")
		self.isRecover = 0
		return True
	
	self.isRecover = 1
	action = para[-1]
	# Participant Failure only if last line is VOTE_COMMIT or VOTE_ABORT
	# Request Coordinator for final decision and output here will be Global_Commit or Global_Abort
	if action == "VOTE_COMMIT\n" or action == "VOTE_ABORT\n":
	   lastState = StatusReport()
	   lastState = self.checkForLastState()
	   if lastState.status == Status.GLOBAL_COMMIT:
		self.doCommit()
	   elif lastState == Status.GLOBAL_ABORT:
		self.doAbort()

	self.isRecover = 0

    # Participant Failure
    def checkForLastState(self):
	response = StatusReport()
	try:
            transport = TSocket.TSocket(self.coordinatorIp, self.coordinatorPort)
            send_tran = TTransport.TBufferedTransport(transport)
            protocol = TBinaryProtocol.TBinaryProtocol(send_tran)
            send_tran.open()
       	    client = FileStore.Client(protocol)
	    response = client.lastRecordedState()
	    send_tran.close()
        except Thrift.TException, tx:
            print('%s' % tx.message)
	return response

    # writes file content to the database
    def writeFile(self, rFile):
	statusReport = StatusReport()
	statusReport.status = Status.FAILED
	last_line = ""
	self.file = open(self.name + '.log', 'r+')
	for line in self.file:
		last_line = line
	para = last_line.split(" ")
	if para[0] == 'WRITE':
	      if para[1] == rFile.filename:
		 print("Participant >>> Aborting second write transaction on the same file")
		 return statusReport
		 sys.exit()
	else:
	  self.file = open(self.name+'.log', "a+")
	  self.file.write("WRITE"+" "+ rFile.filename + " " + rFile.content)
	  self.file.flush()
	  #print("sleeping for 10 seconds in writeFile ..abort now")
	  #time.sleep(10)
	  try:
	      self.conn = sqlite3.connect(self.name + '.db')
	      self.cur = self.conn.cursor()
	      self.cur.execute('INSERT OR REPLACE INTO Backup VALUES(?, ?)', (rFile.filename, rFile.content))
	      self.conn.commit()
	  except Exception as e:
	      self.conn.rollback()
	      raise e
	  finally:
	      self.conn.close()
	  statusReport.status = Status.SUCCESSFUL
	  self.startTime = time.time()
	  return statusReport
 


    def canCommit(self):
	statusReport = StatusReport()
	statusReport.status = Status.VOTE_REQUEST
	self.file = open(self.name+'.log', "a+")
	self.endTime = time.time()
	print("Participant >>> Time diff at Part is ", self.endTime - self.startTime)
	# Coordinator failure case 1 always abort
        print("Participant >>> Timedout? ",self.endTime-self.startTime> self.timeout)
	if self.endTime - self.startTime > self.timeout:
	    	self.file.write(" VOTE_ABORT\n")
		self.file.flush()
		statusReport.status = Status.VOTE_ABORT
		return statusReport
	else:
		self.file.write(" VOTE_COMMIT\n")
		self.file.flush()
		#print("sleeping for 10 seconds in votecommit ..abort now")
		time.sleep(8)
		statusReport.status = Status.VOTE_COMMIT
		return statusReport

    # reads file content from the database
    def readFile(self, filename):
        rFile = RFile()
        rFile.filename = filename
	rFile.content = ""
	print("Participant >>> Inside readFile")
	self.file = open(self.name + ".log", "a+")
	self.file.write("READ"+" "+ filename+ "\n")
	self.file.flush()
	
        try:
	    self.conn = sqlite3.connect(self.name + '.db')
            self.cur = self.conn.cursor()
            self.cur.execute('SELECT content FROM Info WHERE filename = ?', (rFile.filename,))
	    cont = str(self.cur.fetchone()[0])
	    if cont == None:
		cont = ""
	    print(cont)
            rFile.content = cont
	    self.conn.commit()
        except sqlite3.Error, e:
            print(e.args)
        return rFile


    def doCommit(self):
	if self.option == 1:
	    sys.exit("participant failure after voting")
        try:
	    self.conn = sqlite3.connect(self.name + '.db')
	    self.cur = self.conn.cursor()
	    self.cur.execute('INSERT OR REPLACE INTO Info SELECT * FROM Backup')
            self.conn.commit()
        except sqlite3.Error, e:
            print(e.args)
	self.file = open(self.name + ".log", "a+")
	self.file.write(" GLOBAL_COMMIT\n")
	self.file.flush()

    def doAbort(self):
	if self.option == 1:
	    sys.exit("participant failure after voting")
        try:
	    self.conn = sqlite3.connect(self.name + '.db')
	    self.cur = self.conn.cursor()
	    self.cur.execute('DELETE FROM Backup')
            self.conn.commit()
        except sqlite3.Error, e:
            print(e.args)
	self.file = open(self.name + ".log", "a+")
	self.file.write(" GLOBAL_ABORT\n")
	self.file.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Participant')
    parser.add_argument('name',type=str,help='The name of participant')
    parser.add_argument('port',type=int,help='The port Number')
    parser.add_argument('timeout',type=int,help='Timeout for participant')
    parser.add_argument('coorIp',type=str,help='The coordinator IP')
    parser.add_argument('coorPort',type=int,help='The coordinator port')
    parser.add_argument('option',type=int,help='Option to crash Participant')
	
    args = parser.parse_args()
    handler = Participant(args.name, args.port, args.timeout, args.coorIp, args.coorPort, args.option)
    handler.recover()
    processor = FileStore.Processor(handler)
    try:
        transport = TSocket.TServerSocket(port=args.port)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolFactory()
        server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
        server.daemon = True
        server.serve()
        print("Participant >>> Starting Participant on port ...", args.port)
    except Thrift.TException, tx:
        print('%s' % tx.message)