from datetime import datetime, timedelta
from copy import copy, deepcopy
from constants import *
import utils
import random
from exceptions import (NotEnoughBallotClaimTickets, UnrecognizedNode, 
    UnknownVoter, UsedBallotClaimTicket, InvalidBallot)
import logging
from cryptography.exceptions import InvalidSignature
from election import FlexibleBallot, Voter


def set_up_logging(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    f_handler = logging.FileHandler('logs/{}.log'.format(name), mode='a')
    f_handler.setLevel(logging.INFO)

    f_format = logging.Formatter('%(asctime)s Node %(public_key)s: %(message)s')
    f_handler.setFormatter(f_format)

    logger.addHandler(f_handler)


set_up_logging('node')
logger = logging.getLogger('node')


class Node:
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
        self.transaction_tally = dict()  # holds tally for each transaction during consensus round
        self.last_round_approvals = set()
        self.last_round_rejections = set()
        self.rejection_map = {}

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

    def begin_consensus_round(self, nodes=None):
        """
        Args:
            nodes  nodes to participate in consensus with. used to whitelist nodes
                    when nodes with a different block hash are detected. defaults
                    to entire network
        """
        if nodes:
            try:
                nodes.remove(self)
            except ValueError as e:
                print(e)
        else:
            nodes = self.node_mapping.values()
        self.last_round_nodes = nodes
        self.rejection_map = {}
        self.send_nodes_transactions_for_consensus(nodes)

    def send_nodes_transactions_for_consensus(self, nodes):
        """Sends verified transactions to all nodes in the network specifically for the consensus round"""
        for node in nodes:
            node.check_transactions_for_consensus(self.verified_transactions)

    def check_transactions_for_consensus(self, transactions):
        """Validates a collection of transactions and adjusts each one's tally during the consensus round.
        Args:
            transactions            iterable of Transactions to check
        """
        for tx in transactions:
            # TODO - check this logic...
            if tx in self.transaction_tally:
                self.transaction_tally[tx] = self.transaction_tally[tx] + 1
            else:
                # validate transaction and set tally accordingly
                try:
                    if tx not in self.verified_transactions:
                        self.validate_transaction(tx)
                    self.transaction_tally[tx] = 1
                except Exception as e:
                    self.rejection_map[tx] = str(e)
                    self.transaction_tally[tx] = 0

    def finalize_consensus_round(self):
        """Finalizes block and resets state for next round"""
        self.last_round_approvals.clear()
        self.last_round_rejections.clear()
        self.last_round_rejection_reasons = ''

        # aggregate results
        network_size = len(self.node_mapping.values()) + 1  # add itself
        approved_transactions = []
        rejected_transactions = []
        for tx in self.transaction_tally:
            tally = self.transaction_tally[tx]
            if tally/network_size >= MINIMUM_AGREEMENT_PCT:
                approved_transactions.append(tx)
                self.last_round_approvals.add(tx)
            else:
                rejected_transactions.append(tx)
                self.last_round_rejections.add(tx)
                self.last_round_rejection_reasons = self.rejection_map.values()

        # finalize block
        self.blockchain.add_block(approved_transactions)

        # reset round
        self.transaction_tally = {}
        for tx in approved_transactions:
            try:
                self.verified_transactions.remove(tx)
            except KeyError:
                pass
            try:
                self.rejected_transactions.remove(tx)
            except KeyError:
                pass

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

    def get_signature_contents(self, **signature_kwargs):
        return self.id

    @staticmethod
    def validate(ticket):
        try:
            utils.verify_signature(
                ticket.get_signature_contents(),
                ticket.signature, 
                ticket.node.public_key
            )
        except InvalidSignature:
            ticket.errors = "Invalid ballot claim ticket signature"
            raise InvalidSignature(ticket.errors)


class KeyChangingNodeMixin(object):
    """Injects faulty/adversary behavior in node so that it changes its 
    key pair each time it signs something."""
    is_adversary = True

    def sign_message(self, message):
        self.public_key, self._private_key = utils.get_key_pair()
        return super().sign_message(message)


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


class UnrecognizedVoterAuthenticationBooth(KeyChangingNodeMixin,
                                           VoterAuthenticationBooth):
    is_adversary = True

#TODO Issue: a lot of the adversary behavior isn't even caught because the 
# signature fails (since we assume that the adversary cannot sign)


class AuthBypassVoterAuthenticationBooth(VoterAuthenticationBooth):
    is_adversary = True
    
    def sign_message(self, message):
        """Cannot access private key to actually sign"""
        return message.encode()

    def authenticate_voter(self, voter):
        return True  # bypasses auth

    def _voter_has_claim_tickets(self, voter_id):
        return True  # allows user to retrieve unlimited claim tickets

    def generate_ballot_claim_ticket(self, voter):
        ticket = BallotClaimTicket(self)
        # TODO: increase global counter
        self.create_transaction(voter)
        return ticket


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


class DOSVotingComputer(VotingComputer):
    is_adversary = True

    def check_transactions_for_consensus(self, txs):
        pass  # doesn't vote on validity during consensus


class InvalidBallotVotingComputer(VotingComputer):
    """Voting Computer that allows the user to submit arbitrary candidates for 
    arbitrary positions"""
    is_adversary = True

    def get_ballot(self):
        """Overridden to make ballot filling flexible for user"""
        flexible_ballot = FlexibleBallot(election=self.ballot.election)
        for position in self.ballot.items:
            metadata = self.ballot.items[position]
            flexible_ballot.add_item(
                position=position,
                description=metadata['description'],
                choices=deepcopy(metadata['choices']),  # create independent copy
                max_choices=metadata['max_choices']
            )
        return flexible_ballot


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
            AttributeError:     if content object not implement `get_signature_contents` method
            Exception:          if either old or new state is not in the `allowed_states`
        """
        if getattr(content, 'get_signature_contents') is None:
            raise AttributeError(str(content_class) + ' needs to implement method get_signature_contents')
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
            utils.verify_signature(transaction.get_signature_contents(**transaction.signature_kwargs), transaction.signature, transaction.node.public_key)
        except InvalidSignature as e:
            public_key = transaction.node.public_key
            raise InvalidSignature('Invalid signature by public key: {}'.format(hash(public_key)))


class BallotTransaction(Transaction):
    allowed_states = [BALLOT_CREATED, BALLOT_USED]

    def __init__(self, ballot_claim_ticket, *args, **kwargs):
        self.ballot_claim_ticket = ballot_claim_ticket
        super().__init__(*args, **kwargs)

    def get_signature_contents(self, **signature_kwargs):
        signature_contents = super().get_signature_contents(**signature_kwargs)
        return ":".join([
            signature_contents, 
            self.ballot_claim_ticket.get_signature_contents(**signature_kwargs)
        ])


class VoterTransaction(Transaction):
    allowed_states = [NOT_RETRIEVED_BALLOT, RETRIEVED_BALLOT]


class Block:

        # TODO: am I even creating a block?
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
                self.state = copy(self.previous_block.state)
            self.apply_transactions()
            self.time = datetime.now()
            self.hash = self.get_signature_contents()  # TODO: apply hash to this string
            self.header = node.sign_message(self.hash)

        def apply_transactions(self):
            pass

        def get_signature_contents(self, **signature_kwargs):
            """TODO: make this state + previous_block"""
            str_list = []
            for tx in self.transactions:
                str_list.append(tx.signature.hex())
            
            if self.previous_block:
                str_list.append(self.previous_block.hash)  # use hash rather than individually signed hash

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
        """Signal for implementing behavior after adding a new block (such as updating global values)"""
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