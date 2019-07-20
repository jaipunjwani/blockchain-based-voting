from base import Node, BallotGenerator, VoteLedger, VoteTransaction, VotingComputer
import unittest
from unittest.mock import Mock, patch
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_key_pair():
    private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=512,
            backend=default_backend()
        )
    public_key = private_key.public_key()
    return public_key, private_key

class TestNode(unittest.TestCase):

    def setUp(self):
        self.node = Node(*generate_key_pair())
        self.peer = Node(*generate_key_pair())
        node_dict = {
            hash(self.node.public_key): self.node,
            hash(self.peer.public_key): self.peer
        }
        self.node.set_node_mapping(node_dict)

    def test_set_node_mapping(self):
        node_mapping = self.node.node_mapping
        self.assertEqual(len(node_mapping.keys()), 1)
        self.assertEqual(node_mapping[hash(self.peer.public_key)],self.peer)

    @patch.object(Node, 'validate_transaction')
    def test_add_timestamped_transaction(self, mock_validate_tx):
        # IF
        tx = Mock()
        tx.timestamped = True
        tx.node = self.peer
        mock_validate_tx.return_value = True
        
        # WHEN
        added = self.node.add_transaction(tx)

        # THEN
        mock_validate_tx.assert_called_once()
        self.assertTrue(added)
        self.assertIn(tx, self.node.verified_transactions)

    def test_is_node_in_network(self):
        pass

    def test_sign_message(self):
        pass

    def test_set_blockchain(self):
        pass

    def test_send_nodes_transactions_for_consensus(self):
        pass

    def test_check_transactions_for_consensus(self):
        pass




class TestVotingComputer(unittest.TestCase):

    def setUp(self):
        self.voting_computer = VotingComputer(*generate_key_pair())

    def test_has_pending_transactions(self):
        self.assertTrue(hasattr(self.voting_computer, 'pending_transactions'))

    def test_is_node_in_network(self):
        pass  # if super is false, checks ballot generator as node

    def test_validate_transaction(self):
        pass

    def test_create_transaction(self):
        pass

    def test_broadcast_transactions(self):
        pass


class TestVoterComputer(unittest.TestCase):

    def setUp(self):
        pass

    def test_authenticate_voter(self):
        pass

    def test_has_voter_voted(self):
        pass

    def test_create_transactions(self):
        pass

    def test_broadcast_transactions(self):
        pass

    def test_validate_transaction(self):
        pass


# TODO: test adversary computers
# also redesign - create base class with adversary=True


class TestBallotGenerator(unittest.TestCase):

    def setUp(self):
        pass

    def test_generate_ballots(self):
        pass

    def test_are_ballots_available(self):
        pass

    def test_retrieve_ballot(self):
        pass

    def test_is_legitimate_ballot(self):
        pass

    def test_create_transaction(self):
        pass


class TestTransaction(unittest.TestCase):

    def test_get_signature_contents(self):
        pass


class TestVoteTransaction(unittest.TestCase):

    def setUp(self):
        pass


