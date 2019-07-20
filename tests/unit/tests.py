#from blockchain_evoting_system import *
import base

'''
import random
import unittest
import rsa
import datetime
import utils
from copy import deepcopy
from constants import STATE
from base import Node, BallotGenerator, VoteLedger, VoteTransaction, VotingComputer
from election import Voter, Choice, Ballot, BallotItem
from setup import set_up_nodes
from utils import verify_signature


class TestUtilsClass(unittest.TestCase):

    def setUp(self):
        (pubkey, privkey) = rsa.newkeys(512)
        self.pubkey = pubkey
        self.privkey = privkey

    def test_verify_signature(self):
        message = "nooneknows"
        message_encoded = message.encode('utf8')
        #signature = rsa.sign(message_encoded, self.privkey, "SHA-256")
        #actual = utils.verify_signature(message_encoded, signature, self.pubkey)
        #self.assertTrue(actual, True)

    def test_get_input_of_type(self):
        message = "test message"
        #self.assertTrue(type(message), str())

    def test_get_hash(self):
        pass

    def test_formatted_time_str(self):
        pass

"""
class TestVotingProgram(unittest.TestCase):

    def setUp(self):
        self.mock_election = self.set_up_election()

    def test_retrieve_ballot(self):
        ballot = BallotGenerator.generate_ballots(self.mock_election, self.mock_election.choices, 1)

    def test_get_voter_by_id(self):
        for voter in self.voter_roll:
            print (voter)
            self.assertTrue()

    def test_begin_voting_process(self):
        pass
"""

class TestBallotClass(unittest.TestCase):
    def setUp(self):
        election = "2018"
        items = ['HC', 'DT']
        self.test_ballot_obj = Ballot(election, items)

    def test_get_id(self):
        self.assertEqual(self.test_ballot_obj.id, self.test_ballot_obj.get_id())


class TestBallotItemClass(unittest.TestCase):
    def setUp(self):
        title = "President",
        max_choices = 1,
        description = "President of the United States",
        choices = [
            Choice("Hillary Clinton (D)"),
            Choice("Donald Trump (R)"),
            Choice("Gary Johnson (L)"),
            Choice("Jill Steel (G)")
        ]
        self.ballot_item = BallotItem(title, description, max_choices, choices)

    def test_vote(self):
        description = "President of the United States",
        self.assertEqual(self.test_ballotItem.description, description)

    def test_get_choices(self):
        self.assertEqual(self.test_ballotItem.choices, [
            Choice("Hillary Clinton (D)"),
            Choice("Donald Trump (R)"),
            Choice("Gary Johnson (L)"),
            Choice("Jill Steel (G)")
        ])

    def test_deep_copy(self):
        copied_item = deepcopy(self.ballot_item)
        # make changes to the original object, and show that these changes are not reflected in copied one
        for choice in self.ballot_item.choices:
            choice.select()

        for choice in copied_item.choices:
            self.assertFalse(choice.chosen)


class TestChoiceClass(unittest.TestCase):

    def setUp(self):
        description = "descriptor"
        self.test_Choice = Choice(description)

    def test_select(self):
        description = "Jill Steel (G)"
        self.test_Choice = Choice(description)
        self.test_Choice.select()
        self.assertEqual(self.test_Choice.chosen, True)


class TestVoterClass(unittest.TestCase):

    def setUp(self):
        test_name = 'john smith'
        test_id = 1
        self.test_voter = Voter(test_id, test_name)

    def test_constructor(self):
        self.assertTrue(self.test_voter.name, 'john smith')
        self.assertTrue(self.test_voter.id, 1)

    def test_vote(self):
        self.test_voter.vote()
        self.assertEqual(self.test_voter.state, 'voted')


class TestNodeClass(unittest.TestCase):
    """Class to test common behavior of all nodes"""

    def setUp(self):
        (public_key, private_key) = rsa.newkeys(512)
        self.node = Node(public_key, private_key)
        self.node_mapping = {str(public_key): self.node}

    def test_set_mapping(self):
        self.node.set_node_mapping(dict(self.node_mapping))
        # node is supposed to remove its own mapping from dictionary
        self.assertEqual(self.node.node_mapping, {})

    def test_method_name(self):
        # call method here
        # assert that the expected result is the case
        pass

    def test_node_in_network(self):
        actual = self.node.is_node_in_network(self.node.public_key)
        self.assertTrue(self.node_mapping, actual)

    def test_sign_message(self):
        # Encoding our message into bits using .encode()
        message = 'Test Message'.encode()

        # Ciphertext that takes a message and makes a node sign the message
        cipher = self.node.sign_message(message)

        # plaintext that uses decryption with the private key on the cipher text
        # Cannot test for encryption equality, because random seed makes encryption results different
        plaintxt = rsa.decrypt(cipher, self.node._private_key)

        # tested if node signs message properly
        self.assertEqual(message, plaintxt,
                         'Node did not sign message properly')


class TestVotingComputerClass(unittest.TestCase):
    # Testing a VotingComputer

    def setUp(self):
        public_key, private_key = rsa.newkeys(512)
        self.voting_node = Node(public_key, private_key)
        self.VotingComputer(self.voting_node)


class TestVoteLedgerClass(unittest.TestCase):

    def setUp(self):
        # set up test ballots
        election = "2016 Presidential Election"
        candidates = [
            Choice("Hillary Clinton (D)"),
            Choice("Donald Trump (R)"),
            Choice("Gary Johnson (L)"),
            Choice("Jill Steel (G)")
        ]
        items = [
            BallotItem(
                title="President",
                max_choices=1,
                description="President of the United States",
                choices=candidates
            )
        ]
        self.ballots = [Ballot(election, items) for i in range(2)]
        self.vote_ledger = VoteLedger(self.ballots)

    def test_get_copy(self):
        copy = self.vote_ledger.get_copy()
        self.assertNotEqual(hash(copy), hash(self.vote_ledger))

        # test that ledger still has the same keys (same Ballot objects)
        self.assertTrue(self.ballots[0] in copy.ledger and self.ballots[0] in self.vote_ledger.ledger)

    def test_apply_transactions(self):
        # TODO: determine sub-cases (i.e., different order of transactions)
        
        node = set_up_nodes(VotingComputer, num_nodes=1)[0]
        # test out of order transaction and ensure that logically earlier transaction is applied first
        txs = [
            VoteTransaction(self.ballots[0], node, STATE.ISSUED, STATE.USED),
            VoteTransaction(self.ballots[0], node, STATE.CREATED, STATE.ISSUED)
        ]
        self.vote_ledger.apply_transactions(txs)
        
        # check that the final state of USED was applied
        self.assertEqual(self.vote_ledger.ledger[self.ballots[0]], STATE.USED)
        # self.vote_ledger.ledger[]


if __name__ == '__main__':
    unittest.main()
'''