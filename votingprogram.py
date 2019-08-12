import random
import utils

from base import VotingComputer, VoterAuthenticationBooth
from copy import copy, deepcopy
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

MINIMUM_AGREEMENT_PCT = 0.8  # required consensus for blockchain approval

class Voter:

    def __init__(self, voter_id, name):
        self.id = str(voter_id)
        self.name = name

    def __repr__(self):
        return self.name

    def get_signature_contents(self, **kwargs):
        return "{}:{}".format(str(self.id), self.name)


class Ballot:
    """Ballot for a specific election that can have many ballot items."""

    def __init__(self, election):
        self.election = election
        self.items = dict()
        self.finalized = False

    def get_signature_contents(self, **kwargs):
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

    def fill_out(self):
        # TODO: review
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

            # TODO: handle
            if not selection_indexes:
                retry = True
                pass # need more valid selections
            if len(selection_indexes) > metadata['max_choices']:
                retry = True
                pass # too many choices

            selections = [metadata['choices'][i] for i in selection_indexes]
            print("Your valid selections: {}".format(selections))
            confirmation = utils.get_input_of_type(
                "Enter 'y' to confirm choices or 'n' to clear ballot ",
                str, allowed_inputs=['y', 'n', 'Y', 'N']
            ).lower()
            print()
            if confirmation == 'n':
                retry = True # ?
                self.clear()
                return False
            else:
                self.select(position, selection_indexes)
        return True    

    def select(self, position, selected):
        self.items[position]['selected'] = selected

    def unselect(self, position, selected):
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
        pass


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
        # set up election with ballot template
        self.ballot = Ballot(election='U.S. 2020 Federal Election')
        self.ballot.add_item(
            position='President', 
            description='Head of executive branch', 
            choices=['Obama(D)', 'Bloomberg(R)'], 
            max_choices=1
        )
        self.ballot.add_item(
            position='Vice President',
            description='Executive right below President',
            choices=['Joe Biden(D)', 'Bradley Tusk(R)'],
            max_choices=1
        )
        self.ballot.finalize()

        # read voter roll from file
        self.voter_roll = self.load_voter_roll()

        # initialize nodes
        num_nodes = 50
        self.voting_computers = create_nodes(
            VotingComputer, self.ballot, num_nodes=num_nodes
        )
        self.voter_authentication_booths = create_nodes(
            VoterAuthenticationBooth, self.voter_roll, num_nodes=num_nodes
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
        continue_program = True

        while continue_program:
            utils.clear_screen()
            self.display_header()
            self.display_menu()
            choice = utils.get_input_of_type("Enter in an option: ", int)
            continue_program = self.handle_menu_choice(choice)
            input("Press any key to continue")

    def display_header(self):
        print ("{}".format(self.ballot.election))
        print ("Voter Blockchain  | Nodes: {}\t Adversary Nodes: {}".format(
                len(self.voter_authentication_booths), 0
            )
        )
        print ("Ballot Blockchain | Nodes: {}\t Adversary Nodes: {}".format(
                len(self.voting_computers), 0
            )
        )
        print()

    def display_menu(self):
        print ("(1) Vote")
        print ("(2) Lookup voter id")
        print ("(3) View current results")
        print ("(4) View logs")
        print ("(5) Exit")

    def handle_menu_choice(self, choice):
        """
        Redirects menu choice to appropriate function.
        Returns whether or not program should continue.
        """
        if choice == 1:
            return self.vote()
        elif choice == 2:
            self.lookup_voter_id()
        elif choice == 3:
            pass
        elif choice == 4:
            pass
        elif choice == 5:
            return False
        else:
            print("Unrecognized option")
        return True

    def vote(self):
        """Controls voting flow. Returns whether or not program should continue."""
        # authenticate voter
        voter_auth_booth = random.choice(self.voter_authentication_booths)
        voter = utils.get_input_of_type(
            "Please authenticate yourself by typing in your full name.\n",
            str
        ).lower()
        voter_id = None

        voters = self.get_voter_by_id(voter)
        if len(voters) > 1:
            voter_id = utils.get_input_of_type(
                "Multiple matches found for {}. Please enter in your voter id.\n".format(voter),
                str
            )
            if voter_id not in [v.id for v in voters]:
                print("Please look up your ID and try again.")
                return True
        elif len(voters) == 1:
            voter_id = voters[0]

        authenticated = voter_auth_booth.authenticate_voter(voter_id)

        if not authenticated:
            print("{} is not on the voter roll".format(voter))
            return True

        can_vote = voter_auth_booth.can_voter_vote(voter_id)
        if not can_vote:
            print("{} has already voted!".format(voter))

        # retrieve ballot claim ticket
        ballot_claim_ticket = voter_auth_booth.generate_ballot_claim_ticket(voter_id)
        print("Retrieved ballot claim ticket. Please proceed to the voting booths.\n")

        # vote
        voting_computer = random.choice(self.voting_computers)
        voting_computer.vote(ballot_claim_ticket)

        # return False if election is over (all voters have voted)
        return True

    def lookup_voter_id(self):
        name = utils.get_input_of_type(
                "Type in your full name: ",
                str
            ).lower()
        matches = self.get_voter_by_id(name)

        if not matches:
            print("No matches found")
        else:
            print("Matching ID(s) found: {}".format(
                [voter.id for voter in matches]
            ))

    def get_voter_by_id(self, name):
        return [voter for voter in self.voter_roll if voter.name == name]

    def load_voter_roll(self):
        voter_roll = []
        voter_id = 1
        with open(self.path, 'r') as file:
            for voter in file:
                voter = voter.strip().lower()  # use lowercase for simplicity
                if voter:
                    voter_roll.append(Voter(voter_id, voter))
                    voter_id = voter_id + 1
        print ("Registered voters from {}: {}".format(
            self.path, voter_roll)
        )
        return voter_roll