import random
import utils

from base import VotingComputer, VoterAuthenticationBooth
from copy import copy, deepcopy
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

MINIMUM_AGREEMENT_PCT = 0.8  # required consensus for blockchain approval

# ballot for a single election, in this case U.S. Federal Election
ballot = [
    # a ballot can have multiple ballot items (1 per position)
    {
     'position': 'President', 
     'description': 'Head of executive branch', 
     'choices': ['Obama (D)', 'Bloomberg (R)'],
     'max_choices': 1,
     'chosen': []
    },
    {
     'position': 'Vice President',
     'description': 'Executive ranked right below the president',
     'choices': ['Joe Biden (D)', 'Bradley Tusk (R)'],
     'max_choices': 1,
     'chosen': []
    }
]

class Ballot:
    """Ballot for a specific election that can have many ballot items."""

    def __init__(self, election):
        self.election = election
        self.items = dict()
        self.finalized = False

    def add_item(self, position, description, choices, max_choices):
        if self.finalized:
            return;

        # one position per election
        self.items[position] = {
            'description': description,
            'choices': choices,
            'max_choices': max_choices
            'selected': []  # tracks selected choices
        }

    def print(self):
        print("Ballot for {}".format(self.election))
        for position in self.items:
            metadata = self.items[position]
            print ("{}: {}".format(position, metadata['description']))
            print ("You may select up to {} of the following choices: ".format(metadata['max_choices']))
            for num, choice in enumerate(metadata['choices']):
                print ("{}. {}".format(num, choice))
            print("Please ")


    def select(self, position, selected):
        pass

    def unselect(self, position, selected):
        pass

    def clear(self):
        """Wipes selections from ballot."""
        for position in self.items:
            self.items[position]['selected'] = []

    def finalize(self):
        """Finalizes ballot items."""
        self.finalized = true


def create_nodes(NodeClass, *additional_args, num_nodes=0, is_adversary=False):
    nodes = []
    for i in range(num_nodes):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=512,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        args_list = list(additional_args) + [public_key, private_key]
        args = tuple(args_list)
        node = NodeClass(*args, is_adversary=is_adversary)
        nodes.append(node)
    return nodes


def get_pki(nodes):
    pki = dict()
    for node in nodes:
        pki[hash(node.public_key)] = node
    return pki


class VotingProgram:
    path = 'voter_roll.txt'

    def setup(self, adversarial_mode=False):
        # read voter roll from file
        voter_roll = self.load_voter_roll()

        # initialize nodes
        num_nodes = 50
        self.voting_computers = create_nodes(
            VotingComputer, num_nodes=num_nodes
        )
        self.voter_authentication_booths = create_nodes(
            VoterAuthenticationBooth, voter_roll, num_nodes=num_nodes
        )

        # construct copy of PKI and add to all nodes
        voting_nodes_pki = get_pki(self.voting_computers)
        for node in self.voting_computers:
            node.set_node_mapping(copy(voting_nodes_pki))

        voter_auth_nodes_pki = get_pki(self.voter_authentication_booths)
        for node in self.voter_authentication_booths:
            node.set_node_mapping(copy(voter_auth_nodes_pki))

        

        # initialize blockchain with appropriate content

    def begin_program(self):
        # TODO: display menu and control program flow
        self.vote()

    def vote(self):
        # authenticate voter
        voter_auth_booth = random.choice(self.voter_authentication_booths)
        voter = utils.get_input_of_type(
            "Please authenticate yourself by typing in your full name.\n",
            str
        ).lower()
        authenticated = voter_auth_booth.authenticate_voter(voter)

        if not authenticated:
            print("{} is not on the voter roll".format(voter))
            return

        can_vote = voter_auth_booth.can_voter_vote(voter)
        if not can_vote:
            print("{} has already voted!".format(voter))

        # retrieve ballot claim ticket
        print("Retrieving ballot claim ticket. Please proceed to the voting booths.")

        # vote
        voting_computer = random.choice(self.voting_computers)
        
    def load_voter_roll(self):
        voter_roll = dict()
        voter_id = 1
        with open(self.path, 'r') as file:
            for voter in file:
                voter = voter.strip().lower()  # use lowercase for simplicity
                if voter:
                    voter_roll[voter_id] = voter
                    voter_id = voter_id + 1
        print ("Registered voters from {}: {}".format(
            self.path, list(voter_roll.values())))
        return voter_roll 