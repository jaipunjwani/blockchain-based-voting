from copy import deepcopy

class Node:
    """Abstract class for Node that participates in a blockchain"""

    def __init__(self, public_key, private_key, is_adversary=None):
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
        self.is_adversary = is_adversary

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

    def broadcast_transactions(self, transactions):
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
        # check that source is trusted and validate transaction
        if (not self.is_node_in_network(transaction.node.public_key)):
            raise Exception('Unexpected node!')
        valid = self.validate_transaction(transaction)
        if valid:
            self.verified_transactions.add(transaction)
            return True
        else:
            self.rejected_transactions.add(transaction)
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


class VoterAuthenticationBooth(Node):
    """Voter Registration Authority / Node responsible for authenticating voter
    and creating transactions on VoterBlockchain."""

    def __init__(self, voter_roll, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.voter_roll = voter_roll

    def authenticate_voter(self, voter):
        return True if voter in self.voter_roll.values() else False

    def can_voter_vote(self, voter):
        return self.authenticate_voter(voter)
        # TODO: add logic for checking if voter has voted


class VotingComputer(Node):
    """Voting computer which is also a node in the ballot blockchain."""

    def __init__(self, ballot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ballot = deepcopy(ballot)


class Transaction:
    """
    A change of state for an entity or object. Transactions can be timestamped and signed.
    """

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
            raise Exception("Invalid state for transaction.")
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