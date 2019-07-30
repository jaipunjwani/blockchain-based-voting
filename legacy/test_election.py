import random
import unittest
import rsa
import datetime
import utils
from copy import deepcopy
from constants import STATE
from election import Voter, Choice, Ballot, BallotItem
from utils import verify_signature


class TestVoterClass(unittest.TestCase):
    def setUp(self):
        self.voter = Voter("Jai", 1)

    def test_get_voter_object_signature(self):
        self.assertEqual(self.voter.get_signature_contents(), 1)


class TestChoiceClass(unittest.TestCase):
    def setUp(self):
        self.choice = Choice("test choice")

    def test_str(self):
        to_str = str(self.choice)
        expected = "test choice:False"
        self.assertEqual(to_str, expected)

    def test_select(self):
        # select choice
        self.assertFalse(self.choice.chosen)
        self.choice.select()
        self.assertTrue(self.choice.chosen)

    def test_unselect(self):
        # assume that chosen is false and check for change
        self.choice.chosen = True
        self.choice.unselect()
        self.assertFalse(self.choice.chosen)

    def test_get_signature_contents(self):
        # test that signature should only return state of chosen if kwarg is provided
        # say chosen is True
        self.choice.chosen = True
        transaction_signature = self.choice.get_signature_contents(include_chosen=False)
        self.assertEqual(transaction_signature, 'test choice')
        full_signature = self.choice.get_signature_contents(include_chosen=True)
        self.assertEqual(full_signature, 'test choice:True')


class TestBallotItem(unittest.TestCase):
    def setUp(self):
        self.choices = [
            Choice('test choice 1'),
            Choice('test choice 2')
        ]
        self.ballot_item = BallotItem('President of US', '2020 US Presidential Election', 1, self.choices)

    def test_choices_are_deepcopied(self):
        # IF
        new_ballot_item = BallotItem('President of US', '2020 US President', 1, self.choices)
        self.assertNotEqual(id(new_ballot_item), id(self.ballot_item))
        for choice in zip(self.choices, new_ballot_item.choices):
            self.assertNotEqual(id(choice[0]), id(choice[1]))


class TestBallot(unittest.TestCase):
    def setUp(self):
        self.choices = [
            Choice('Michael Bloomberg'),
            Choice('Joe Biden')
        ]
        self.election = 'Federal Election'
        self.ballot_items = [BallotItem('President of US', '2020 US Presidential Election', 1, self.choices)]
        self.ballot1 = Ballot(self.election, self.ballot_items)
        self.ballot2 = Ballot(self.election, self.ballot_items)
        self.ballots = [self.ballot1, self.ballot2]

    def test_is_deepcopied(self):
        for items in zip(self.ballot1.items, self.ballot2.items):
            self.assertNotEqual(id(items[0]), id(items[1])) 

    def test_ballot_uniqueness(self):
        self.assertNotEqual(self.ballot1.id, self.ballot2.id)

    def test_tally(self):
        # IF
        self.ballots[0].items[0].choices[0].chosen = True
        self.ballots[0].items[0].choices[1].chosen = False

        self.ballots[1].items[0].choices[0].chosen = False
        self.ballots[1].items[0].choices[1].chosen = True

        self.ballots[0].items[0].choices[0].chosen = True
        self.assertTrue(self.ballots[0].items[0].choices[0].chosen)

        # WHEN
        tally = Ballot.tally(self.ballots)

        # THEN
        self.assertEqual(tally['Michael Bloomberg'], 1)
        self.assertEqual(tally['Joe Biden'], 1)

    def test_is_filled(self):
        # IF
        # we add a second BallotItem
        new_ballot_items = [BallotItem(
            'Vice President',
            '2020 Federal election',
            1,
            self.choices
        )]
        ballot = Ballot(self.election, self.ballot_items+new_ballot_items)
        ballot.items[0].choices[0].chosen = True  # only fill out one item

        # WHEN
        is_filled = ballot.is_filled()

        # THEN
        self.assertFalse(is_filled)

        # BUT IF
        ballot.items[1].choices[0].chosen = True # we fill out the second item

        # THEN
        self.assertTrue(ballot.is_filled())

    def test_get_selected_choices(self):
        # IF
        ballot = deepcopy(self.ballot1)  # nothing is selected by default

        # WHEN
        selected_choices = ballot.get_selected_choices()

        # THEN
        self.assertEqual(len(selected_choices), 0)

        # BUT IF
        ballot.items[0].choices[0].chosen = True  # we select one choice
        selected_choices = ballot.get_selected_choices()

        # THEN
        self.assertEqual(len(selected_choices), 1)
        self.assertEqual(selected_choices[0], ballot.items[0].choices[0])


'''

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