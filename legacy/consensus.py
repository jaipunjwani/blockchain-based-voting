from __future__ import print_function  # should be on the top
import time
import threading
import time
import rsa
import hashlib

class block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index  # instance variable unique to each instance
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash

    def calculateHash(self):
        return sha256(str(self.index + self.timestamp + self.data + self.previous_hash))

class blockchain:

    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return block(0, "4/20/18 9:00 pm",'Genesis Block', 0)

    def getLatestBlock(self):
        return self.chain.length-1

    def addBlock(self , newBlock):
        newBlock.previousHash = self.getLatestBlock().__hash__()
        newBlock.__hash__() = newBlock.calculateHash();
        self.chain.push(newBlock)





#basic threading as object example.
class MyThread(threading.Thread):
    def run(self):
        print("{} started!".format(self.getName()))  # "Thread-x started!"
        time.sleep(1)  # Pretend to work for a second
        print("{} finished!".format(self.getName()))  # "Thread-x finished!"


if __name__ == '__main__':
    for x in range(45):  # Four times...
        mythread = MyThread(name="Thread-{}".format(x + 1))  # ...Instantiate a thread and pass a unique ID to it
        mythread.start()  # ...Start the thread
        time.sleep(.9)  # ...Wait 0.9 seconds before starting another


# consensus algorithm class
class Consensus:
    # time_interval = 30 seconds
    time_interval = 30.00
    time_count = 0.00  # time counter
    time_is_up = False

    # minimum_agreement = percentage can be set - assuming 67% minimum agreement
    min_agreement = .67

    def __init__(self, nodes):
        # store nodes
        nodes = []
        nodes = self.nodes
        # store_minimumPCT(parameter)
        self.min_PCT = .67

    def begin(self, voting_computers, time_is_up, min_agreement):
        while (time_is_up != True):
            # do nothing... nodes will collect transactions
            time.sleep(1)
            time_count = time_count + 1
        # used class and function holders below until further clarified
        # time is up (only evaluate current transactions) : begin algorithm (check statistical variation)
        if time_is_up == True:
            # nodes send each other all of their txns (broadcast)
            print("nodes now send each other all of their transactions")
            # nodes receive & add it to a set - easy for loop
            for node in self.nodes:
                for txns in node:
                    self.nodes.append(node)
                print(set)
                for node in self.nodes:
                    # each node votes & passes it to each other, tallying upvotes
                    print("Nodes vote and pass results to each other - a tally of upvotes and downvotes")
                    self.nodes.Tally()
            # if minimum % reached, node creates block w/ tx and adds it to local BC
            if min_agreement == .67:
                print("If consensus percentage is hit, a block is now created with those transactions")
                self.nodes.createBlock()


# the use of polling, when polling the program first checks to see if information is avaliable, and then asks for it. An alternative
# would be to throw an exception if information is not yet ready to be retreived. _ NETWORKING MULTI THREADING SLIDES

# better way to do this is use callbacks to wait for consensus to end

