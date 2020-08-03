from datetime import datetime, timedelta
from copy import copy, deepcopy
from constants import *
import utils
import random
from exceptions import (NotEnoughBallotClaimTickets, UnrecognizedNode, 
    UnknownVoter, UsedBallotClaimTicket, InvalidBallot)
from consensus import ConsensusParticipant
import logging
from cryptography.exceptions import InvalidSignature
import utils


def set_up_logging(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    f_handler = logging.FileHandler('logs/{}.log'.format(name), mode='a')
    f_handler.setLevel(logging.INFO)

    f_format = logging.Formatter('%(asctime)s Node %(public_key)s: %(message)s')
    f_handler.setFormatter(f_format)

    logger.addHandler(f_handler)
    return logger

logger = set_up_logging('node')


class Voter:

    def __init__(self, voter_id, name, num_claim_tickets):
        self.id = str(voter_id)
        self.name = name
        self.num_claim_tickets = num_claim_tickets

    def __repr__(self):
        return self.name

    def get_unique_repr(self, **kwargs):
        return "{}:{}".format(str(self.id), self.name)


class Ballot:
    """Ballot for a specific election that can have many ballot items."""

    def __init__(self, election):
        self.election = election
        self.items = dict()
        self.finalized = False

    def get_unique_repr(self, **kwargs):
        """Returns unique representation of Ballot"""
        return self.election + str(self.items)

    def add_item(self, position, description, choices, max_choices):
        if self.finalized:
            return

        # one unique position per election
        self.items[position] = {
            'description': description,
            'choices': choices,
            'max_choices': max_choices,
            'selected': []  # tracks index(es) of selected choices
        }

    def fill_out(self, selections=None, **kwargs):
        """
        selections  pre-determined selections (used by simulation/adversaries)
                      ex: {'President': [0], 'Vice President': [1]}

        Returns whether or not ballot was filled out. This determines whether or not
        a transaction will be created. 

        Future enhancement: Implement retry mechanism, allowing ballots to be invalidated.
        To do this, we would have to support invalidating claim tickets and allowing the
        voter to claim another ticket in its stead.
        """

        if selections:
            for position in selections:
                self.select(position, selections[position])
            return True

        print("Ballot for {}".format(self.election))
        for position in self.items:
            metadata = self.items[position]
            print ("{}: {}".format(position, metadata['description']))
            for num, choice in enumerate(metadata['choices']):
                print ("{}. {}".format(num+1, choice))

            max_choices = metadata['max_choices']
            if max_choices > 1:
                msg = "Please enter your choice numbers, separated by commas (no more than {} selections): ".format(
                    max_choices
                )
            else:
                msg = "Please enter your choice number: "

            user_input = input(msg)
            user_input = user_input.split(",")[:max_choices]  # cap at max_choices
            selection_indexes = []
            for selection in user_input:
                try:
                    candidate = metadata['choices'][int(selection)-1]
                    selection_indexes.append(int(selection)-1)
                except (IndexError, ValueError):
                    retry = True

            # no valid selections were made
            if not selection_indexes:
                retry = True

            selections = [metadata['choices'][i] for i in selection_indexes]
            print("Your valid selections: {}".format(selections))
            confirmation = utils.get_input_of_type(
                "Enter 'y' to confirm choices or 'n' to invalidate ballot ",
                str, allowed_inputs=['y', 'n', 'Y', 'N']
            ).lower()
            print()
            if confirmation == 'n':
                retry = True
                return False
            else:
                self.select(position, selection_indexes)
        return True    

    def select(self, position, selected):
        """
        selected   list of selected index(es) for position
        """
        self.items[position]['selected'] = selected

    def unselect(self, position, selected):
        """Future work"""
        pass

    def clear(self):
        """Wipes selections from ballot."""
        for position in self.items:
            self.items[position]['selected'] = []

    def finalize(self):
        """Finalizes ballot items."""
        self.finalized = True

    @staticmethod
    def tally(ballots):
        """
        returns tally in format
          {
              'president': [{'Obama': 1}, {'Bloomberg': 2}],
              'vice president': [{'Biden': 1}, {'Tusk': 2}]
          }
        """
        result = {}

        for ballot in ballots:
            for position in ballot.items:
                choices = ballot.items[position]['choices']
                selected = ballot.items[position]['selected']
                
                if position not in result:
                    result[position] = []
                    for candidate in choices:
                        result[position].append({candidate: 0})

                for candidate_index in selected:
                    candidate = choices[candidate_index]
                    result[position][candidate_index][candidate] += 1
        return result


class Node(ConsensusParticipant):
    """Abstract class for Node that participates in a blockchain"""
    is_adversary = False

    def __init__(self, public_key, private_key):
        """
        Args:
            public_key      RSA public key
            private_key     RSA private key
            is_adversary    whether or not Node is an adversary node
        """
        self.public_key = public_key
        self._private_key = private_key
        self.verified_transactions = set()
        self.rejected_transactions = set()  # transactions that failed validation, but will be included in next round
        super().__init__()  # ConsensusParticipant init

    def log(self, message):
        logger.info(message, extra={'public_key': hash(self.public_key)})

    def set_node_mapping(self, node_dict):
        """Sets mapping for public key addresses to each node in the network.
        Args:
            node_dict   dictionary of every node in network, including self
        """
        node_dict.pop(hash(self.public_key), None)  # remove current node from mapping
        self.node_mapping = node_dict

    def create_transaction(self):
        """Abstract method to allow node to create transaction specific to blockchain. 
        Returns boolean indicating success."""
        pass

    def broadcast_transactions(self, *transactions):
        """Broadcasts transactions to other nodes"""
        for node in self.node_mapping.values():
            for tx in transactions:
                node.add_transaction(tx)

    def add_transaction(self, transaction):
        """Adds an incoming (broadcast) transaction to the local node if it is valid.
        Args:
            transaction     Transaction to be added
        Returns:
            whether or not transaction was successfully added
        Raises:
            Exception: if transaction Node is not in network
        """
        try:
            # check that source is trusted and validate transaction
            self.is_node_in_network(transaction.node.public_key)
            self.validate_transaction(transaction)
            self.verified_transactions.add(transaction)
            return True
        except Exception as e:
            self.log(e)
            self.rejected_transactions.add(transaction)
            return False

    def validate_transaction(self, transaction):
        """Performs basic validation of transaction. Should be combined with any content-specific validation in child classes."""
        Transaction.validate_transaction(transaction)

    
    def is_node_in_network(self, public_key):
        """Returns whether or not public key is one of the recognized nodes, including itself.
        Args:
            public_key      RSA public key
        """
        public_key_hash = hash(public_key)
        recognized = public_key_hash == hash(self.public_key) or public_key_hash in self.node_mapping
        if not recognized:
            raise UnrecognizedNode('{} is an unrecognized node'.format(hash(public_key)))

    def sign_message(self, message):
        """Signs a string or bytes message using the RSA algorithm.
        Args:
            message         string of bytes to sign
        """
        return utils.sign(message, self._private_key)


class BallotClaimTicket:
    """Ticket issued after voter authenticates. Authorizes one ballot."""

    DURATION = timedelta(minutes=10)

    def __init__(self, node):
        self.id = str(random.getrandbits(128))  # assign a random ID to the ballot
        self.node = node
        self.issued = datetime.now()
        self.signature = self.node.sign_message(self.id)
        self.errors = ""

    def get_unique_repr(self, **signature_kwargs):
        return self.id

    @staticmethod
    def validate(ticket):
        try:
            utils.verify_signature(
                ticket.get_unique_repr(),
                ticket.signature, 
                ticket.node.public_key
            )
        except InvalidSignature:
            ticket.errors = "Invalid ballot claim ticket signature"
            raise InvalidSignature(ticket.errors)


class VoterAuthenticationBooth(Node):
    """Voter Registration Authority / Node responsible for authenticating voter
    and creating transactions on VoterBlockchain."""

    def __init__(self, voter_roll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voter_roll = voter_roll
        self.voter_roll_index = {voter.id:voter for voter in self.voter_roll}
        self.blockchain = VoterBlockchain(self)
        self.blockchain.create_genesis_block(self.voter_roll)

    def authenticate_voter(self, voter):
        if voter and voter.id in self.voter_roll_index:
            return True
        return False

    def validate_transaction(self, transaction):
        try:
            super().validate_transaction(transaction)
        except InvalidSignature as e:
            raise e
    
        # check that voter is on original voter roll
        voter = transaction.content
        if not voter.id in self.blockchain.current_block.state:
            raise UnknownVoter(
                '{} ({}) is not on voter roll'.format(voter.id, voter.name)
            )

        # Check blockchain & open transactions that voter has not exceeded alloted claim tickets
        if not self._voter_has_claim_tickets(voter.id):
            raise NotEnoughBallotClaimTickets()

    def _voter_has_claim_tickets(self, voter_id):
        """
        Determines whether voter has claim tickets left based on
        blockchain state and open transactions
        """
        claim_tickets_left = self.blockchain.current_block.state.get(voter_id)
        for tx in self.verified_transactions:
            if tx.content.id == voter_id:
                claim_tickets_left -= 1
        return True if claim_tickets_left > 0 else False

    def generate_ballot_claim_ticket(self, voter):
        try:
            if not self.authenticate_voter(voter):
                if voter:
                    raise UnknownVoter('{} not on voter roll'.format(voter.name))
                else:
                    raise UnknownVoter()

            if not self._voter_has_claim_tickets(voter.id):
                raise NotEnoughBallotClaimTickets(
                    'Voter {} (ID {}) does not have enough claim tickets'.format(voter.name, voter.id)
                )
            ticket = BallotClaimTicket(self)
            # TODO: increase global counter
            self.create_transaction(voter)
            return ticket
        except Exception as e:
            self.log(str(e))
            raise e

    def create_transaction(self, voter):
        tx = VoterTransaction(voter, self, NOT_RETRIEVED_BALLOT, RETRIEVED_BALLOT)
        self.verified_transactions.add(tx)
        self.broadcast_transactions(tx)


class VotingComputer(Node):
    """Voting computer which is also a node in the ballot blockchain."""

    def __init__(self, ballot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ballot = ballot
        self.blockchain = BallotBlockchain(self)
        self.blockchain.create_genesis_block(self.ballot)

    def get_ballot(self):
        """Returns new ballot"""
        return deepcopy(self.ballot)

    def create_transaction(self, ballot_claim_ticket, ballot):
        signature_kwargs = dict()
        tx = BallotTransaction(
            ballot_claim_ticket, ballot, self, BALLOT_CREATED, BALLOT_USED, 
            **signature_kwargs
        )
        self.verified_transactions.add(tx)
        # TODO: update global counters
        self.broadcast_transactions(tx)

    def vote(self, ballot_claim_ticket, **kwargs):
        # pre-voting: authorize claim ticket
        try:
            self.validate_ballot_claim_ticket(ballot_claim_ticket)
        except Exception as e:
            print(e)
            return

        # voting: retrieve and fill out ballot
        ballot = self.get_ballot()
        ballot_filled_out = ballot.fill_out(**kwargs)

        # post-voting: validate ballot and create tx
        if ballot_filled_out:
            self.create_transaction(ballot_claim_ticket, ballot)

    def validate_ballot_claim_ticket(self, ballot_claim_ticket):
        BallotClaimTicket.validate(ballot_claim_ticket)

    def validate_transaction(self, transaction):
        try:
            super().validate_transaction(transaction)
            BallotClaimTicket.validate(transaction.ballot_claim_ticket)
        except InvalidSignature as e:
            raise e

        # check that ballot claim ticket hasn't been used
        for used_claim_ticket in self.blockchain.ballot_claim_tickets:
            if used_claim_ticket.id == transaction.ballot_claim_ticket.id:
                raise UsedBallotClaimTicket(
                    'Ballot claim id {} attempted to be used multiple times'.format(used_claim_ticket.id)
                )

        # check that ballot is actually valid
        self.validate_ballot(transaction.content)

    def validate_ballot(self, ballot):
        """Checks that ballot selections is in line with expected ballot template"""
        expected_ballot = self.get_ballot()
        for position in ballot.items:
            if position not in expected_ballot.items:
                msg = 'Position {} is not part of original ballot template'.format(position)
                self.log(msg)
                raise InvalidBallot(msg)
            selected = ballot.items[position]['selected']
            try:
                actual_choices = expected_ballot.items[position]['choices']
                for index in selected:
                    actual_choices[index]
            except KeyError as e:
                msg = 'Ballot for position {} has been tampered with! (extra candidate)'.format(position)
                self.log(msg)
                raise InvalidBallot(msg)


class Transaction:
    """
    A change of state for an entity or object. Transactions can be timestamped and signed.
    """

    allowed_states = None  # defines valid states for the content of the transaction
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
            AttributeError:     if content object not implement `get_unique_repr` method
            Exception:          if either old or new state is not in the `allowed_states`
        """
        if not getattr(content, 'get_unique_repr'):
            raise AttributeError(str(content_class) + ' needs to implement method get_unique_repr')
        self.content = content
        self.signature_kwargs = signature_kwargs
        if previous_state in self.allowed_states and new_state in self.allowed_states:
            self.previous_state = previous_state
            self.new_state = new_state
        else:
            raise Exception("Invalid state for transaction.")
        self.node = node
        self.timestamped = timestamped
        if timestamped:
            self.time = datetime.now()
        self.signature = node.sign_message(self.get_unique_repr(**self.signature_kwargs))

    def __str__(self):
        return str(self.signature)

    def get_unique_repr(self, **signature_kwargs):
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
        str_list = [self.content.get_unique_repr(**signature_kwargs),
                    self.previous_state,
                    self.new_state]
        if self.timestamped:
            str_list.append(self.get_time_str())
        return ":".join(str_list)

    def get_time_str(self):
        """Returns transaction's time formatted (Y-M-D H:M) as a string."""
        if self.timestamped:
            return utils.get_formatted_time_str(self.time)
        return ""

    @staticmethod
    def validate_transaction(transaction):
        """Validates a transaction's signature and returns whether its content matches the signature. Note that this validation
        may not be enough for a transaction; the content for a specific transaction may need further validation. Use this method 
        as a first-step verification of any transaction.
        Args:
            transaction         transaction to be validated
        """
        try:
            utils.verify_signature(transaction.get_unique_repr(**transaction.signature_kwargs), transaction.signature, transaction.node.public_key)
        except InvalidSignature as e:
            public_key = transaction.node.public_key
            raise InvalidSignature('Invalid signature by public key: {}'.format(hash(public_key)))


class BallotTransaction(Transaction):
    allowed_states = [BALLOT_CREATED, BALLOT_USED]

    def __init__(self, ballot_claim_ticket, *args, **kwargs):
        self.ballot_claim_ticket = ballot_claim_ticket
        super().__init__(*args, **kwargs)

    def get_unique_repr(self, **signature_kwargs):
        signature_contents = super().get_unique_repr(**signature_kwargs)
        return ":".join([
            signature_contents, 
            self.ballot_claim_ticket.get_unique_repr(**signature_kwargs)
        ])


class VoterTransaction(Transaction):
    allowed_states = [NOT_RETRIEVED_BALLOT, RETRIEVED_BALLOT]


class Block:

        def __init__(self, transactions, node, previous_block=None, genesis=False):
            if not genesis and not previous_block:
                raise Exception('Previous block must be provided for all blocks except genesis')
                
            self.transactions = transactions
            self.node = node
            self.previous_block = previous_block
            self.genesis = genesis
            if self.genesis:
                self.state = {}
            else:
                # start off with previous state
                self.state = copy(self.previous_block.state)  
            self.apply_transactions()
            self.time = datetime.now()
            self.hash = utils.get_str_hash(self.get_unique_repr())
            self.header = node.sign_message(self.hash)

        def apply_transactions(self):
            pass

        def get_unique_repr(self, **signature_kwargs):
            str_list = []
            for tx in self.transactions:
                str_list.append(tx.signature.hex())
            
            if self.previous_block:
                # we use hash rather than header b/c header is individually signed hash so it's different per node
                str_list.append(self.previous_block.hash)

            str_list.append(utils.get_formatted_time_str(self.time))
            str_list.append(str(self.genesis))
            return ":".join(str_list)


class VoterBlock(Block):

    def apply_transactions(self):
        for tx in self.transactions:
            voter = tx.content
            # assumes voter id is already in voter roll
            # if it's not (e.g., a node adds a voter after registration),
            # then this should be caught in validation step
            self.state[voter.id] -= 1


class BallotBlock(Block):

    def apply_transactions(self):
        for tx in self.transactions:
            ballot = tx.content
            for position in ballot.items:
                choices = ballot.items[position]['choices']
                selected = ballot.items[position]['selected']
                selected_choices = map(lambda n: choices[n], selected)
                for selection in selected_choices:
                    try:
                        self.state[position][selection] += 1
                    except KeyError as e:
                        pass  # log


class Blockchain:
    block_class = None

    def __init__(self, node):
        self.node = node
        self.current_block = None

    def create_genesis_block(self):
        pass

    def add_block(self, transactions):
        block = self.block_class(transactions, self.node, previous_block=self.current_block)
        self.current_block = block
        self.post_add_block()

    def post_add_block(self):
        """
        Callback for implementing behavior after adding a new block (such as updating global values)
        """
        pass


class VoterBlockchain(Blockchain):
    # TODO: add global counters
    block_class = VoterBlock

    def create_genesis_block(self, voter_roll):
        self.current_block = self.block_class([], self.node, genesis=True)
        # set initial state to voter roll with number of allotted claim tickets
        initial_state = {}
        for voter in voter_roll:
            initial_state[voter.id] = voter.num_claim_tickets
        self.current_block.state = initial_state


class BallotBlockchain(Blockchain):
    # TODO: add global counters
    ballot_claim_tickets = []
    block_class = BallotBlock

    def create_genesis_block(self, empty_ballot):
        self.current_block = self.block_class([], self.node, genesis=True)
        initial_state = {}
        # set initial state to index of position and candidate with 0 votes
        for position in empty_ballot.items:
            initial_state[position] = {}
            position_data = empty_ballot.items[position]
            for choice in position_data['choices']:
                initial_state[position][choice] = 0
        self.current_block.state = initial_state

    def post_add_block(self):
        for tx in self.current_block.transactions:
            # aggregate all ballot claim tickets used for convenience
            self.ballot_claim_tickets.append(tx.ballot_claim_ticket)