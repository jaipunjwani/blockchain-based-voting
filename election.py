import random
import time
import utils
import json
from constants import *
from datetime import datetime, timedelta
from base import (VotingComputer, VoterAuthenticationBooth, Voter, Ballot)
from copy import copy, deepcopy
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from exceptions import NotEnoughBallotClaimTickets, UnknownVoter
from consensus import ConsensusParticipant


VOTER_ROLL_PATH = 'voter_roll.txt'
LOG_FILE_PATH = 'logs/node.log'


def create_nodes(NodeClass, *additional_args, num_nodes=0):
    nodes = []
    if NodeClass:
        for i in range(num_nodes):
            public_key, private_key = utils.get_key_pair()
            args_list = list(additional_args) + [public_key, private_key]
            args = tuple(args_list)
            node = NodeClass(*args)
            nodes.append(node)
    return nodes


def get_pki(nodes):
    pki = dict()
    for node in nodes:
        pki[hash(node.public_key)] = node
    return pki


class VotingProgram:
    path = VOTER_ROLL_PATH
    num_voters_voted = 0

    def setup(self, 
              adversarial_mode=False, 
              consensus_round_interval=DEFAULT_CONSENSUS_ROUND_INTERVAL,
              voter_node_adversary_class=None,
              voting_node_adversary_class=None,
              total_nodes=50):
        self.adversarial_mode = adversarial_mode
        self.consensus_round_interval = consensus_round_interval
        self.total_nodes = total_nodes
        total_adversarial_nodes = 0
        self.total_voter_node_adversarial_nodes = 0
        self.total_voting_node_adversarial_nodes = 0
        
        if self.adversarial_mode:
            if not (voter_node_adversary_class or voting_node_adversary_class):
                exit('Adversarial mode requires an adversary class to be chosen')
            total_adversarial_nodes = int((1-MINIMUM_AGREEMENT_PCT) * self.total_nodes) - 1
            if voter_node_adversary_class:
                self.total_voter_node_adversarial_nodes = total_adversarial_nodes
            if voting_node_adversary_class:
                self.total_voting_node_adversarial_nodes = total_adversarial_nodes

        # set up election with ballot template
        self.ballot = Ballot(election='U.S. 2020 Federal Election')
        self.ballot.add_item(
            position='President', 
            description='Head of executive branch', 
            choices=['Mike Bloomberg(D)', 'Donald Trump(R)'], 
            max_choices=1
        )
        self.ballot.add_item(
            position='Vice President',
            description='Executive right below President',
            choices=['Joe Biden(D)', 'Mike Pence(R)'],
            max_choices=1
        )
        self.ballot.finalize()

        # load voter roll from file/configuration
        self.load_voter_roll()

        # initialize regular nodes
        num_nodes = self.total_nodes - total_adversarial_nodes
        self.voting_computers = create_nodes(
            VotingComputer, self.ballot, num_nodes=num_nodes
        )
        self.voter_authentication_booths = create_nodes(
            VoterAuthenticationBooth, self.voter_roll, num_nodes=num_nodes
        )

        # initialize adversary nodes (defaults to 0 nodes)
        self.voting_computers += (
            create_nodes(voting_node_adversary_class, self.ballot, num_nodes=total_adversarial_nodes)
        )
        self.voter_authentication_booths += (
            create_nodes(voter_node_adversary_class, self.voter_roll, num_nodes=total_adversarial_nodes)
        )

        # construct copy of PKI and add to all nodes
        voting_nodes_pki = get_pki(self.voting_computers)
        for node in self.voting_computers:
            node.set_node_mapping(copy(voting_nodes_pki))

        voter_auth_nodes_pki = get_pki(self.voter_authentication_booths)
        for node in self.voter_authentication_booths:
            node.set_node_mapping(copy(voter_auth_nodes_pki))

        # initialize blockchain with appropriate content?

    def begin_program(self):
        self.last_time = datetime.now()
        continue_program = True
    
        while continue_program:
            utils.clear_screen()
            self.display_header()
            self.display_menu()
            choice = self.get_menu_choice()
            continue_program = self.handle_menu_choice(choice)
            if self.is_election_over():
                break
            if self.is_consensus_round():
                self.demonstrate_consensus(self.voter_authentication_booths, 'Voter Blockchain')
                self.demonstrate_consensus(self.voting_computers, 'Ballot Blockchain')
            input("Press any key to continue")

        self.demonstrate_consensus(self.voter_authentication_booths, 'Voter Blockchain')
        self.demonstrate_consensus(self.voting_computers, 'Ballot Blockchain')        
        print("Election over! Results: ")
        self.display_results()

    def get_menu_choice(self):
        return utils.get_input_of_type('Enter in an option: ', int)

    def is_consensus_round(self):
        if datetime.now() - self.last_time >= timedelta(seconds=self.consensus_round_interval):
            self.last_time = datetime.now()
            return True
        return False

    def demonstrate_consensus(self):
        ConsensusParticipant.demonstrate_consensus(self.voter_authentication_booths, 'Voter Blockchain')
        ConsensusParticipant.demonstrate_consensus(self.voting_computers, 'Ballot Blockchain') 
        
    def display_header(self):
        mode = 'ADVERSARIAL MODE' if self.adversarial_mode else 'NORMAL MODE'
        print (mode)
        print ("{}".format(self.ballot.election))
        print ("Voter Blockchain  | Normal Nodes: {}\t Adversary Nodes: {}".format(
                len(self.voter_authentication_booths) - self.total_voter_node_adversarial_nodes, 
                self.total_voter_node_adversarial_nodes
            )
        )
        print("Ballot Blockchain | Normal Nodes: {}\t Adversary Nodes: {}".format(
                len(self.voting_computers) - self.total_voting_node_adversarial_nodes, 
                self.total_voting_node_adversarial_nodes
            )
        )
        next_consensus_round = self.last_time + timedelta(seconds=self.consensus_round_interval)
        print("Next consensus round: {}".format(
                next_consensus_round.time().strftime("%H:%M:%S")
            )
        )
        print()

    def display_menu(self):
        print ("(1) Vote")
        print ("(2) Lookup voter id")
        print ("(3) View current results")
        print ("(4) View logs")
        print ("(5) Exit")

    def display_results(self):
        # Displays results from all nodes in ballot blockchain
        print('Displaying results from the blockchain: ')

        hash_frequency = {}
        num_nodes = len(self.voting_computers)
        hash_to_block = {}
        # check blockchain for all nodes and find block based on consensus
        for node in self.voting_computers:
            block = node.blockchain.current_block
            if block.hash not in hash_frequency:
                hash_frequency[block.hash] = 1
                hash_to_block[block.hash] = block
            else:
                hash_frequency[block.hash] += 1

            if hash_frequency[block.hash]/num_nodes >= MINIMUM_AGREEMENT_PCT:
                print(json.dumps(hash_to_block[block.hash].state, indent=4))
                return

        print('Blocks are not in sync. please wait until next consensus round.')
        return

    def handle_menu_choice(self, choice):
        """
        Redirects menu choice to appropriate function.
        Returns whether or not program should continue.
        """
        if choice == 1:
            self.vote()
        elif choice == 2:
            self.lookup_voter_id()
        elif choice == 3:
            self.display_results()
        elif choice == 4:
            self.display_logs()
        elif choice == 5:
            return False
        else:
            print("Unrecognized option")
        return True

    def display_logs(self):
        print('Displaying last 30 lines')
        log_file = LOG_FILE_PATH
        lines = []
        with open(log_file, 'r') as fh:
            for line in fh:
                lines.append(fh.readline().strip())
        for line in lines[-30:]:
            print(line)

    def _authenticate_voter(self, voter_auth_booth, **kwargs):
        """Authenticates voter and returns voter object (None if voter cannot vote)."""
        voter_name = utils.get_input_of_type(
            "Please authenticate yourself by typing in your full name.\n",
            str
        ).lower()
        voter_id = None
        voter = None

        voters = self.get_voter_by_name(voter_name)
        if len(voters) > 1:
            voter_id = utils.get_input_of_type(
                "Multiple matches found for {}. Please enter in your voter id.\n".format(voter_name),
                str
            )
            for v in voters:
                if v.id == voter_id:
                    voter = v
                    break
            if not voter:
                print("Please look up your ID and try again.")
                return None
        elif len(voters) == 1:
            voter = voters[0]
            voter_id = voters[0].id
        return voter

    def vote(self, **kwargs):
        """Simulates voter's experience at authentication and voter booths."""
        voter_auth_booth = random.choice(self.voter_authentication_booths)
        voter = self._authenticate_voter(voter_auth_booth, voter=kwargs.pop('voter', None))

        # try to retrieve ballot claim ticket
        try:
            ballot_claim_ticket = voter_auth_booth.generate_ballot_claim_ticket(voter)
            print('Authenticated voter {}'.format(voter.name))
            print("Retrieved ballot claim ticket. Please proceed to the voting booths.\n")
        except (NotEnoughBallotClaimTickets, UnknownVoter) as e:
            print(e)
            return

        # vote
        voting_computer = random.choice(self.voting_computers)
        voting_computer.vote(ballot_claim_ticket, **kwargs)

        # TODO: local global counter
        self.num_voters_voted+=1

    def is_election_over(self):
        # TODO: counter increases even if vote fails..rectify by making node.vote() call throw exception and catching it
        # check for consensus among global counters from all nodes
        if self.num_voters_voted >= len(self.voter_roll):
            return True
        return False

    def lookup_voter_id(self):
        name = utils.get_input_of_type(
                "Type in your full name: ",
                str
            ).lower()
        matches = self.get_voter_by_name(name)

        if not matches:
            print("No matches found")
        else:
            print("Matching ID(s) found: {}".format(
                [voter.id for voter in matches]
            ))

    def get_voter_by_name(self, name):
        return [voter for voter in self.voter_roll if voter.name == name]

    def load_voter_roll(self):
        voter_roll = []
        voter_id = 1

        with open(self.path, 'r') as file:
            voter_roll_dict = json.load(file)
            for voter in voter_roll_dict:
                name = voter['name'].strip().lower()  # use lowercase for simplicity
                if name:
                    num_claim_tickets = int(voter.get('num_claim_tickets', 1))
                    voter_roll.append(Voter(voter_id, name, num_claim_tickets))
                    voter_id += 1
        print ("Registered voters from {}: {}".format(
            self.path, voter_roll)
        )
        self.voter_roll = voter_roll


class Simulation(VotingProgram):
    """Wrapper for voting program that overrides parts of it for simulation purposes"""
    current_voter_index = 0 
    candidate_one_percentage = 0.6
    candidate_two_percentage = 1 - candidate_one_percentage
    voter_ballot_selections = {}

    def load_voter_roll(self):
        self.voter_roll = []
        for voter_id in range(self.num_voters):
            voter_id = str(voter_id+1)
            name = 'Voter{}'.format(voter_id)
            self.voter_roll.append(Voter(voter_id, name, num_claim_tickets=1))

            # preset voter selections for simulation
            self.voter_ballot_selections[voter_id] = {}
            for position in self.ballot.items:
                metadata = self.ballot.items[position]
                if int(voter_id)/self.num_voters <= self.candidate_one_percentage:
                    selected = [0]
                else:
                    selected = [1]
                self.voter_ballot_selections[voter_id][position] = selected

    def setup(self, *args, 
        num_voters=100, 
        num_unregistered_voters=0, 
        num_double_voting_voters=0, 
        additional_selections=None,   
        **kwargs):
        """
        num_voters                number of regular voters to simulate
        num_unregistered_voters   number of unregistered voters to be introduced
        num_double_voting_voters  number of regular voters who will double vote
        additional_selections     pre-configured selections for FlexibleBallot
        """
        
        self.num_voters = num_voters
        self.num_unregistered_voters = max(0, num_unregistered_voters)  # separate from main voter roll
        self.num_double_voting_voters = min(max(0, num_double_voting_voters), num_voters)  # part of main voter roll
        super().setup(*args, **kwargs)

        self.additional_selections = additional_selections

        self.unregistered_voters = []
        unregistered_voter_name_str = 'UnknownVoter{}'
        id_str = 'anon{}'
        for i in range(self.num_unregistered_voters):
            self.unregistered_voters.append(
                Voter(id_str.format(i+1), unregistered_voter_name_str.format(i+1), num_claim_tickets=0)
            )

        self.double_voting_voters = []
        if self.num_double_voting_voters:
            self.double_voting_voters = self.voter_roll[-1*self.num_double_voting_voters:]

    def begin_program(self):
        """
        Overriding flow of program since it doesnt require user interaction
        kwargs:
            selections   
        """
        self.last_time = datetime.now()
    
        utils.clear_screen()
        self.display_header()

        # space out unregistered voters and registered voters
        for voter in self.generate_voters():
            # get voter's pre-configured choices
            self.vote(
                voter=voter, 
                selections=self.voter_ballot_selections.get(voter.id),
                additional_selections=self.additional_selections
            )

            if self.is_consensus_round():
                self.demonstrate_consensus()

            utils.clear_screen()
            self.display_header()

        input("Press any key to continue")
        print("Displaying logs")
        self.display_logs()
        input('Press enter to see results.')
        utils.clear_screen()

        self.demonstrate_consensus()
        print("Election over! Results: ")
        self.display_results()

    def generate_voters(self):
        """Generate sequence of voters from voter roll & any unregistered voters for the simulation"""
        voters = self.voter_roll + self.unregistered_voters + self.double_voting_voters
        return voters
        # return double voting voters twice
        #return voters + self.double_voting_voters + self.double_voting_voters

    def display_menu(self):
        print('Simulating voting process')

    def get_menu_choice(self):
        return 1  # choice for voting

    def _authenticate_voter(self, voter_auth_booth, voter=None):
        """Return the provided voter object for the simulation, else continue
        iterating over the voter roll"""
        if not voter and self.current_voter_index < len(self.voter_roll):
            voter = self.voter_roll[self.current_voter_index]
            self.current_voter_index += 1
        return voter