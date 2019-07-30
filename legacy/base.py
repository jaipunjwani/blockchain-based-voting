import datetime
import random
import utils
from constants import STATE
from copy import deepcopy
from election import Ballot, Voter


class Node:
    """Abstract class for Node that participates in a blockchain"""

    def __init__(self, public_key, private_key, adversary=None):
        """
        Args:
            public_key      RSA public key
            private_key     RSA private key
            adversary       whether or not Node is an adversary node; currently used to control printing
        """
        self.public_key = public_key
        self._private_key = private_key
        self.verified_transactions = set()  # transactions that were verified. includes created transactions
        self.rejected_transactions = set()  # transactions that were rejected. may be marked for not counting
        self.transaction_tally = dict()  # holds tally for each transaction during consensus round
        self.adversary = adversary

    def set_node_mapping(self, node_dict):
        """Sets mapping for public key addresses to each node in the network.
        Args:
            node_dict   dictionary of every node in network, including self
        """
        node_dict.pop(hash(self.public_key), None)  # remove current node's own mapping
        self.node_mapping = node_dict

    def create_transaction(self):
        """Abstract method to allow node to create transaction specific to blockchain. 
        Should return boolean indicating success."""
        pass

    def broadcast_transactions(self, transactions):
        """Abstract method to allow node to broadcast transactions to other nodes"""
        pass

    def add_transaction(self, transaction):
        """Adds an incoming (broadcast) transaction to the local node if it is valid.
        Args:
            transaction     Transaction to be added
        Returns:
            whether or not transaction was successfully added
        Raises:
            AttributeError: if transaction is untimestamped and came from Node that does not have `pending_transactions`
            Exception: if transaction Node is not in network
        """
        # check that source is trusted and validate transaction
        if (not self.is_node_in_network(transaction.node.public_key)):
            raise Exception('Unexpected node!')
        valid = self.validate_transaction(transaction)
        if valid:
            if not transaction.timestamped:
                # only for untimestamped vote transactions
                self.pending_transactions.add(transaction)
            else:
                self.verified_transactions.add(transaction)
            return True
        else:
            # print out when adversary rejects transaction to demonstrate adversarial behavior
            if self.adversary and transaction not in self.rejected_transactions:
                print('(Adversary Node) transaction was rejected!')
            # TODO: ????? Order? self.rejected_transactions.add(transaction)
            return False

    def validate_transaction(self, transaction):
        """Performs basic validation of transaction. Should be combined with any content-specific validation in child classes."""
        return Transaction.validate_transaction(transaction)

    def check_transactions_for_consensus(self, transactions):
        """Validates a collection of transactions and adjusts each one's tally during the consensus round.
        Args:
            transactions            iterable of Transactions to check
        """
        for tx in transactions:
            # check if we have already approved a transaction
            if tx in self.transaction_tally:
                self.transaction_tally[tx] = self.transaction_tally[tx] + 1
            else:
                # validate transaction and set tally accordingly
                validity = 1 if self.validate_transaction(tx) else 0
                self.transaction_tally[tx] = validity

    def send_nodes_transactions_for_consensus(self):
        """Sends verified transactions to all nodes in the network specifically for the consensus round"""
        for node in self.node_mapping.values():
            node.check_transactions_for_consensus(self.verified_transactions)

    def set_blockchain(self, blockchain):
        """Sets the blockchain software for this Node.
        Args:
            blockchain      independent copy of a master Blockchain
        """
        blockchain.create_genesis_block(self)
        self.blockchain = blockchain

    def create_block(self):
        """Supposed to happen during consensus round, in which Node creates block after all transactions
        are approved by majority of network.
        """
        pass

    def is_node_in_network(self, public_key):
        """Returns whether or not public key is one of the recognized nodes, including itself.
        Args:
            public_key      RSA public key
        """
        public_key_hash = hash(public_key)
        return public_key_hash == hash(self.public_key) or public_key_hash in self.node_mapping

    def sign_message(self, message):
        """Signs a string or bytes message using the RSA algorithm.
        Args:
            message         string of bytes to sign
        """
        return utils.sign(message, self._private_key)


class VotingComputer(Node):
    """Node that handles the casting of votes. The VotingComputer processes ballots, signs them, 
    and participates in the VoteBlockchain."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: remove pending transactions
        self.pending_transactions = set()  # transactions waiting to be timestamped and broadcasted
    
    def set_ballot_generator(self, ballot_generator):
        """Stores reference to ballot generator so that VotingComputer accepts its transactions.
        Args:
            ballot_generator    BallotGenerator that generates ballots
        """
        self.ballot_generator = ballot_generator

    def is_node_in_network(self, public_key):
        """Returns whether or not public key belongs to one of the recognized nodes OR the ballot generator.
        Args:
            public_key          RSA public key of node in question
        """
        return super().is_node_in_network(public_key) or hash(public_key) == hash(self.ballot_generator.public_key)

    def validate_ballot(self, ballot):
        """Ensures that ballot is legitimate and filled out properly and returns boolean for validity.
        Args:
            ballot              Ballot that we wish to validate
        TODO: finish or remove
        """
        valid =  self.ballot_generator.is_legitimate_ballot(ballot) 
        """
                 and
                 True or  # check ledger that ballot status is unused 
                 True # check local transactions to see if ballot is issued & has not been used 
        # check that the ballot contents are valid - meaning that the voter selected
        # the required number of choice(s)
        """

    def validate_transaction(self, transaction):
        """Validates VoteTransaction by checking that a ballot has not been used before in addition to basic validation.
        Note: This method assumes that an existing ballot record of USED is the only additional invalid case.
        Args:
            transaction         transaction to validate
        """
        ballot = transaction.content
        ballot_status = self.blockchain.current_ledger.ledger.get(ballot)
        if ballot_status == STATE.USED:
            return False 
        return super().validate_transaction(transaction)

    def create_transaction(self, ballot):
        """Creates an untimestamped transaction and adds to pending list of transactions.
        Args:
            ballot              Ballot that is submitted
        Returns:
            whether or not transaction was created
        """
        # checks whether ballot was issued. Note: ballot issuance transactions are only broadcast with the corresponding ballot usage transaction
        ballot_issued = False
        for transaction in self.pending_transactions:
            if transaction.content.id == ballot.id and transaction.new_state == STATE.ISSUED:
                ballot_issued = True

        if ballot_issued:
            tx = VoteTransaction(ballot, self, STATE.ISSUED, STATE.USED, timestamped=False)
            self.pending_transactions.add(tx)
            return True
        else:
            print('ballot was never issued!')
            return False

    def broadcast_transactions(self):
        """Timestamps, signs, and sends pending transactions to all nodes.
        Note: This should only be done if there is enough statistical variation, to avoid links between voters and votes.
        However, for the simulation, we do not have enough votes to do so, so we broadcast all votes at the end.
        """
        VoteTransaction.timestamp_and_sign_transactions(self.pending_transactions)
        for tx in self.pending_transactions:
            self.verified_transactions.add(tx)
            # broadcast transaction to every node in network
            for node in self.node_mapping.values():
                node.add_transaction(tx)
        self.pending_transactions = set()  # reset


# TODO: add ballot claim ticket generation responsibility
# rename? 
class VoterComputer(Node):
    """Node that handles the authentication of voters and ensure that they only vote retrieve a ballot once. 
    The VoterComputer participates in the VoterBlockchain."""

    # TODO: make voter_roll member of VoterComputer
    def authenticate_voter(self, voter, voter_roll):
        """Returns whether or not voter is registered in voter roll.
        Args:
            voter           Voter in question
            voter_roll      iterable of Voter objects
        """
        if voter in voter_roll:
            print(voter.name + ' authenticated')
            return True
        else:
            print(voter.name + ' not on voter roll')
            return False

    def has_voter_voted(self, voter):
        """Returns whether voter has voted.
        Args:
            voter       authenticated Voter
        """
        # check VoterBlockchain/Ledger for voter
        current_ledger = self.blockchain.current_ledger.ledger
        if current_ledger[voter.id] == STATE.VOTED:
            return True

        # check local transactions for voter
        for tx in self.verified_transactions:
            if tx.content == voter and tx.new_state == STATE.VOTED:
                return True
        return False

    def create_transaction(self, voter):
        """Creates transaction indicating that voter has retrieved ballot on VoterBlockchain and broadcasts it immediately.
        Args: 
            voter       Voter that just retrieved a ballot
        Returns:
            whether or not transaction was created
        """
        tx = VoterTransaction(voter, self, STATE.NOT_VOTED, STATE.VOTED, timestamped=True)
        self.verified_transactions.add(tx)
        self.broadcast_transactions()  # broadcast to nodes right away
        return True

    def broadcast_transactions(self):
        """Broadcasts all transactions to nodes in network."""
        for tx in self.verified_transactions:
            for node in self.node_mapping.values():
                node.add_transaction(tx)

    def validate_transaction(self, transaction):
        """Validates a VoterTransaction by checking that a voter has not previously voted in addition to basic transaction validation.
        Args:
            transaction             transaction to validate
        """
        voter = transaction.content
        voter_status = self.blockchain.current_ledger.ledger.get(voter)
        if voter_status == STATE.VOTED:
            return False

        # check transactions that were broadcast but not put on the blockchain
        for tx in self.verified_transactions:
            # skip transaction if it's the same
            if hash(transaction) == hash(tx):
                continue
            if tx.content.id == voter.id and tx.new_state == STATE.VOTED:
                return False

        return super().validate_transaction(transaction)


class BallotChangingVotingComputer(VotingComputer):
    """VotingComputer that changes ballot before it is cast."""
    
    behavior_message = 'Voting Computer changes electronic ballot before it is submitted on blockchain'
    simulation_message = 'Simulation will show that paper trail provides a check on such machines'

    def create_transaction(self, ballot):
        """Corruptedly changes ballot before creating transaction/signing. This will be detected by the paper trail.
        Args:
            ballot      Ballot that was just submitted
        Returns:
            whether not transaction was created
        """
        selected_choices = ballot.get_selected_choices()
        for item in ballot.items:
            chose_different = False
            inverted = False
            for choice in item.choices:
                if choice.chosen and not inverted:
                    choice.unselect()
                    inverted = True
                elif not chose_different:
                    choice.select()
                    chose_different = True
                if chose_different and inverted:
                    break  # we are done with the current ballot item
        
        print('(Adversary node) creating transaction')
        return super().create_transaction(ballot)


class DoubleSpendingVotingComputer(VotingComputer):
    behavior_message = 'Voting Computer tries to submit same ballot twice'
    simulation_message = 'Simulation shows that the network will not allow double-spending'


class RecordTamperingVotingComputer(VotingComputer):
    behavior_message = 'Voting Computer tries to change ballots during the consensus round'
    simulation_message = 'Simulation shows that tampering with records on a blockchain is difficult'    


class AuthorizationBypassVoterComputer(VoterComputer):
    """VoterComputer that denies that a voter has voted, allowing him/her to vote multiple times."""

    behavior_message = 'Voter Computer allows voters to vote on multiple occasions (try it!)'
    simulation_message = 'Simulation shows that the network will reject multiple ballots from the same voter'

    def has_voter_voted(self, voter):
        """Always returns False to allow voters to vote multiple times. Consensus should overrule the
        duplicate transactions."""
        return False

    def validate_transaction(self, transaction):
        """Negates the validation of a trasaction.
        Args:
            transaction             transaction to validate/corrupt
        """
        return not super().validate_transaction(transaction)

# TODO: merge with ballot claim tickets. put ballot template on ballot blockchain
class BallotGenerator(Node):
    """Computer that generates ballots and notifies voting computers for each ballot's creation."""

    def generate_ballots(self, election, items, num_ballots=None):
        """Generates ballots by making deepcopy of choices. This takes place before election day.
        Args:
            election        string representation of election name
            items           BallotItem list
            num_ballots     number of ballots to create
        Returns:
            tuple of Ballot objects
        """
        ballots = []
        if num_ballots:
            for i in range(num_ballots):
                ballots.append(Ballot(election, items))
        self.ballots = tuple(ballots)  # master list
        self.available_ballots = list(ballots)
        return ballots

    def are_ballots_available(self):
        """Returns whether there are any available ballots."""
        return len(self.available_ballots) > 0

    def retrieve_ballot(self):
        """Returns a random ballot and creates a transaction for change in ballot state."""
        if self.are_ballots_available():
            ballot = random.choice(self.available_ballots)      
            self.available_ballots.remove(ballot)
            # create transaction and notify all voting computers
            self.create_transaction(ballot)
            return ballot
        return None

    def is_legitimate_ballot(self, ballot):
        """Returns whether ballot was generated by BallotGenerator.
        Args:
            ballot      Ballot in question
        """
        return ballot in self.ballots

    def create_transaction(self, ballot):
        """Creates untimestamped transaction indicating that ballot was issued and sends this to all voting computers.
        Args:
            ballot      Ballot that was just issued
        Returns:
            whether transaction was successfully created
        """
        tx = VoteTransaction(ballot, self, STATE.CREATED, STATE.ISSUED, timestamped=False, include_chosen=False)
        
        # notify all voting machines that ballot is issued and authorized for use
        for voting_machine in self.node_mapping.values():
            voting_machine.add_transaction(tx)
        return True


class Transaction:
    """A change of state for an entity or object. Transactions are signed, and may
    or may not be timestamped."""

    allowed_states = None  # defines valid states for the content of the transaction
    content_class = None   # defines the expected class of the content
    timestamped = True     # by default, all Transactions are timestamped

    def __init__(self, content, node, previous_state, new_state, timestamped=timestamped, **signature_kwargs):
        """Transaction consists of some content, an issuing node (public key), a signature,
        and, depending on the use case, a timestamp, which is enabled by default
        Args:
            content             the object whose state is being tracked in the transaction
            node                the Node that creates the transaction
            previous_state      the previous state of the content
            new_state           the new state of the content
            timestamped         whether or not this transaction should be timestamped
            signature_kwargs    key word arguments to control signature (e.g., signature of empty Ballot  vs. filled in)
        Raises:
            TypeError:          if transaction content is of unexpected type
            AttributeError:     if content object not implement `get_signature_contents` method
            Exception:          if either old or new state is not in the `allowed_states`
        """
        if type(content) is not self.content_class:
            raise TypeError('Unexpected transaction content!')
        if getattr(content, 'get_signature_contents') is None:
            raise AttributeError(str(content_class) + ' needs to implement method get_signature_contents')
        self.content = content
        self.signature_kwargs = signature_kwargs
        if previous_state in self.allowed_states and new_state in self.allowed_states:
            self.previous_state = previous_state
            self.new_state = new_state
        else:
            raise Exception("Invalid state for transaction..add to tamper log?")
        self.node = node
        self.timestamped = timestamped
        if timestamped:
            self.time = datetime.datetime.now()
        self.signature = node.sign_message(self.get_signature_contents(**self.signature_kwargs))

    def __str__(self):
        return str(self.signature)

    def get_signature_contents(self, **signature_kwargs):
        """Produces unique string representation of transaction which is being signed. Adds timestamp if enabled.
        Note:
            Signature kwargs is currently needed for transactions that use Ballots. We create two transacions 
            involving ballots: (1) a transaction when a ballot is issued, and (2) a transaction when it is used.
            Both transactions hold a reference to the same ballot object, which is filled out before the second
            transaction, thus causing it to change. Hence, when comparing the signature in the first transaction,
            we need to exclude the filled in choices from the ballot signature through the kwargs.
        Args:
            signature_kwargs:       kwargs to control content signature
        """
        str_list = [self.content.get_signature_contents(**signature_kwargs),
                    self.previous_state,
                    self.new_state]
        if self.timestamped:
            str_list.append(self.get_time_str())
        return ":".join(str_list)

    def get_time_str(self):
        """Returns transaction's time formatted (Y-M-D H:M) as a string."""
        if self.timestamped:
            return utils.get_formatted_time_str(self.time)
        return None

    @staticmethod
    def validate_transaction(transaction):
        """Validates a transaction's signature and returns whether its content matches the signature. Note that this validation
        may not be enough for a transaction; the content for a specific transaction may need further validation. Use this method 
        as a first-step verification of any transaction.
        Args:
            transaction         transaction to be validated
        """
        return utils.verify_signature(transaction.get_signature_contents(**transaction.signature_kwargs), transaction.signature, transaction.node.public_key)


class VoteTransaction(Transaction):
    """Class for transactions related to the state of ballots."""
    allowed_states = [STATE.CREATED, STATE.ISSUED, STATE.USED]
    timestamped = False  # we do not timestamp vote transactions when they are created
    content_class = Ballot

    def add_timestamp(self, time=None):
        """Adds a timestamp to a transaction when it is ready to be broadcast.
        Args:
            time            specified timestamp to add (i.e., all transactions in a single block)
        """
        self.time = time or datetime.datetime.now()
        self.timestamped = True

    @staticmethod
    def timestamp_and_sign_transactions(transactions):
        """Adds a timestamp to each transaction and re-signs it. This is used for vote
        transactions that are ready to be timestamped and broadcasted (i.e., there is enough statistical 
        disparity in the voter-vote links). Note that the timestamp is now included in the signature.
        Args:
            transactions            iterable of Transactions
        """
        now = datetime.datetime.now()
        for tx in transactions:
            tx.add_timestamp(time=now)
            # overwrite old signature
            tx.signature = tx.node.sign_message(tx.get_signature_contents(**tx.signature_kwargs))


class VoterTransaction(Transaction):
    """Transaction that stores the state of individual voters."""
    allowed_states = [STATE.NOT_VOTED, STATE.VOTED]
    content_class = Voter


class Ledger:
    """Abstract Ledger class that stores the current cumulative result of transactions.
    Note that the Ledger is only updated by the blockchain when consensus has been achieved."""

    def __init__(self, content=None):
        """
        Args:
            content         iterable of objects that is being tracked in the Ledger (i.e., Ballots, Voters)
        """
        self.content = content
        self.ledger = dict()

    def get_copy(self):
        """Returns copy of Ledger object by copying over its dictionary contents rather than creating a deepcopy
        of all objects, which include dictionary keys (objects) that need to remain unique."""
        copy = self.__class__(self.content)
        for key in self.ledger.keys():
            copy.ledger[key] = self.ledger[key]
        return copy

    def get_hash(self):
        """Returns unique string hash of Ledger."""
        return str(hash(str(self.ledger)))


class VoteLedger(Ledger):
    """Ledger that stores state of ballots, total votes for candidates as well as collective 
    totals of created, issued, and used ballots."""

    def __init__(self, ballots):
        """
        Args:
            ballots         list of Ballot objects. Assumes each ballot has the same content.
        """
        super().__init__(content=ballots)
        total_ballots = len(ballots)

        # add state of individual ballots
        for ballot in ballots:
            self.ledger[ballot] = STATE.CREATED    

        # add collective ballot totals
        self.ledger[STATE.CREATED] = total_ballots
        self.ledger[STATE.ISSUED] = 0
        self.ledger[STATE.USED] = 0

        # extract candidates from ballots and initialize their vote count to 0
        candidades = []
        for item in ballots[0].items:
            for candidate in item.choices:
                # use name of the candidate as key to avoid issues with object reference when making copies
                self.ledger[candidate.description] = 0

    def apply_transactions(self, transactions):
        """Updates the ledger based on the provided transactions. Note: Two logical types of transactions can
        be applied to ballots: tx: ballot.created -> ballot.issued and tx: ballot.issued -> ballot.used. They 
        must be applied in the specified order; transactions passed here are not guaranteed to be in the right
        order, which is why we loop over the transactions twice, ensuring we process them in the correct order.
        
        Args:
            transactions        list of VoteTransaction objects to apply
        """
        for iteration in range(2):    
            for transaction in transactions:
                if iteration == 1 and transaction._reiterate is False:
                    del transaction._reiterate  # remove unnecessary attribute
                    continue

                ballot = transaction.content
                old_state = self.ledger[ballot]
                tx_previous_state = transaction.previous_state
                tx_new_state = transaction.new_state

                if tx_previous_state != old_state:
                    # if transaction does not line up with ledger state, mark so that we come back to it
                    transaction._reiterate = True
                    continue
                
                # update individual ballot state
                self.ledger[ballot] = tx_new_state

                # update collective ballots
                self.ledger[old_state] = self.ledger[old_state] - 1
                self.ledger[tx_new_state] = self.ledger[tx_new_state] + 1

                # update candidate votes if ballot is used
                if tx_new_state == STATE.USED:    
                    candidates = ballot.get_selected_choices()
                    for candidate in candidates:
                        self.ledger[candidate.description] = self.ledger[candidate.description] + 1

                transaction._reiterate = False


class VoterLedger(Ledger):
    """Ledger that stores whether individual voters have voted as well as the collective totals."""

    def __init__(self, voters):
        """
        Args:
            voters          list of Voter objects
        """
        super().__init__(content=voters)
        num_voters = len(voters)
        
        # add collective totals to ledger
        self.registered_voters = num_voters
        self.ledger[STATE.NOT_VOTED] = num_voters
        self.ledger[STATE.VOTED] = 0

        # add state of individual voters to ledger
        for voter in voters:
            self.ledger[voter.id] = STATE.NOT_VOTED

    def apply_transactions(self, transactions):
        """Updates the ledger based on the provided transactions.
        Args:
            transactions    list of VoterTransaction objects
        """
        for transaction in transactions:
            voter = transaction.content
            current_state = self.ledger[voter.id]
            tx_previous_state = transaction.previous_state
            tx_new_state = transaction.new_state

            if current_state != tx_previous_state:
                continue

            # update voter state
            self.ledger[voter.id] = tx_new_state

            # update collective totals
            self.ledger[tx_previous_state] = self.ledger[tx_previous_state] - 1
            self.ledger[tx_new_state] = self.ledger[tx_new_state] + 1


class Block:
    """Block in a blockchain that contains transactions and references the previous block, if any."""
    ledger_class = None  # type of ledger that will be tracked by the Block class

    def __init__(self, transactions, node, ledger=None, prev_block=None, genesis=False):
        """There are two types of Blocks: a genesis block, which is the first in a blockchain, and a regular block,
        which builds off a previous block. A genesis block must specify an initial ledger, and should not specify 
        any transactions or a previous block. A regular block must specify a previous block, and transactions to be 
        applied to a copy of the previous block's ledger and form the ledger for the current block. Regular blocks 
        should not specify a ledger.
        Args:
            transactions:           iterable of Transactions to store in block
            node                    Node that creates block. Should be None for genesis block
            ledger                  Ledger that represent's current block's state after applying transactions. Only used for genesis block.
            prev_block              Block that the current Block builds on. None iff genesis (first) block
            genesis                 whether the Block is a genesis Block
        Raises:
            AttributeError:         if transactions are not specified for a non-genesis block
            TypeError:              if Ledger object does not match expected `ledger_class` or `previous_block` is inconsistent with the current Block type
        """
        if genesis:
            if type(ledger) is not self.ledger_class:
                raise TypeError('Wrong type of ledger')

            self.ledger = ledger  # initial ledger
            self.previous_block = None
            self.transactions = None
        else:
            if type(prev_block) is not self.__class__:
                raise TypeError('Previous Block type is inconsistent with current type')
            
            if transactions is None:
                raise AttributeError('Missing transactions to apply')

            self.previous_block = prev_block
            self.transactions = transactions
            # apply transactions to previous block's ledger
            self.ledger = prev_block.ledger.get_copy()
            self.ledger.apply_transactions(transactions)

        self.time = datetime.datetime.now()
        self.node = node
        self.header = node.sign_message(self.get_signature_contents())

    def __eq__(self, other):
        return self.header == other.header

    def get_signature_contents(self, **signature_kwargs):
        """Produces unique string representation of Block using its ledger, transactions, previous block header,
        and time.
        Args:
            signature_kwargs            kwargs to control signature
        """
        str_list = []
        if self.previous_block:
            str_list.append(str(self.previous_block.header))
        else:
            str_list.append('')  # no previous block

        # add each transaction's signature
        if self.transactions:
            for tx in self.transactions:
                str_list.append(str(tx.signature))
        
        if self.ledger:
            str_list.append(self.ledger.get_hash())
        str_list.append(utils.get_formatted_time_str(self.time))  # add time
        return ":".join(str_list)

    def is_genesis_block(self):
        """Returns whether block is a genesis block."""
        if not self.previous_block:
            return True
        return False


class VoteBlock(Block):
    """Block that is stored in VoteBlockchain."""
    ledger_class = VoteLedger


class VoterBlock(Block):
    """Block that is stored in VoterBlockchain."""
    ledger_class = VoterLedger


class Blockchain:
    """Blockchain that stores a chain of Blocks. Note: The consensus protocol for the blockchain 
    is currently implemented as an external method rather than in this class. Ideally this protocol 
    should be linked to the Blockchain implementatiion more closely."""

    block_class = Block  # defines the type of block that will be constructed

    def __init__(self, initial_ledger):
        """
        Args:
            initial_ledger      starting ledger that will be used to create the genesis block
        """
        self.current_ledger = initial_ledger

    def create_genesis_block(self, node):
        """Creates genesis block with specified node and stores it in blockchain.
        Args:
            node                Node creating genesis block
        """
        self.current_block = self.block_class(None, node, ledger=self.current_ledger, genesis=True)
    
    def add_block(self, node, transactions):
        """Creates and adds new block to blockchain from transactions.
        Args:
            node                Node that is creating block
            transactions        transactions that will be encapsulated in the block
        """
        block = self.block_class(transactions, node, prev_block=self.current_block)
        self.current_block = block
        self.current_ledger = block.ledger

    def remove_block(self, block):
        """Here to demonstrate that we should never try to remove blocks from a blockchain."""
        raise Exception('The blockchain does not allow removing blocks as it serves as an audit trail. Append blocks correcting any mistakes, if any.')


class VoteBlockchain(Blockchain):
    """Blockchain that tracks ballots/votes."""
    block_class = VoteBlock


class VoterBlockchain(Blockchain):
    """Blockchain that tracks voters."""
    block_class = VoterBlock
