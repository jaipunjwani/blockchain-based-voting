import random
import utils
import json
from constants import *
from datetime import datetime, timedelta
from base import VotingComputer, VoterAuthenticationBooth
from copy import copy, deepcopy
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from exceptions import NotEnoughBallotClaimTickets


class Voter:

    def __init__(self, voter_id, name, num_claim_tickets):
        self.id = str(voter_id)
        self.name = name
        self.num_claim_tickets = num_claim_tickets

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

    def fill_out(self, selections=None):
        """
        selections  {'President': [0], 'Vice President': [1]}
        """
        # TODO: review

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
        """
        selected   list of selected index(es) for position
        """
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
        """
        {
            'president': [{'Obama': 1}, {'Bloomberg': 1}],
            'vice president': [{'Biden': '1'}, {'Tusk': 1}]
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
    num_voters_voted = 0

    def setup(self, adversarial_mode=False, consensus_round_interval=DEFAULT_CONSENSUS_ROUND_INTERVAL):
        self.adversarial_mode = adversarial_mode
        self.consensus_round_interval = consensus_round_interval

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

        # load voter roll from file/configuration
        self.load_voter_roll()

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
        self.display_results(nodes_in_sync=True)

    def get_menu_choice(self):
        return utils.get_input_of_type('Enter in an option: ', int)

    def is_consensus_round(self):
        if datetime.now() - self.last_time >= timedelta(seconds=self.consensus_round_interval):
            self.last_time = datetime.now()
            return True
        return False

    def demonstrate_consensus(self, nodes, blockchain_name):
        print()
        print('Kicking off consensus round for {}'.format(blockchain_name))
        # step 1 -- achieve consensus on last block hash (aggregate consensus stats)
        hash_agreement = {}
        for node in nodes:
            h = node.blockchain.current_block.hash  # hash contains previous block header, which is signed by particular
            if h in hash_agreement:
                hash_agreement[h].append(node)
            else:
                hash_agreement[h] = [node]
        num_hashes = len(hash_agreement.keys())
 
        # step 2 -- run a consensus round among nodes that have the same hash
        for h in hash_agreement:
            nodes = hash_agreement[h]
            for node in nodes:
                if num_hashes == 1:
                    node.begin_consensus_round()
                else:
                    # perform consensus only with nodes in agreement of hash
                    node.begin_consensus_round(nodes=nodes.copy())
            for node in nodes:
                node.finalize_consensus_round()
        '''
        # step 2 -- achieve consensus on next set of transactions
        for node in nodes:
            node.begin_consensus_round()
        for node in nodes:
            node.finalize_consensus_round()
        '''
        print()

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
        next_consensus_round = self.last_time + timedelta(seconds=self.consensus_round_interval)
        print ("Next consensus round: {}".format(
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

    def display_results(self, nodes_in_sync=False):
        # get results from all nodes in ballot blockchain
        # TODO: check blockchain results first
        #self.blockchain.current
        # extract ballot from transactions that have consensus from network
        print('Displaying results from the blockchain: ')
        #if nodes_in_sync:
        hash_frequency = {}
        num_nodes = len(self.voting_computers)
        hash_to_block = {}
        # find block that meets minimum consensus requirements
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

        '''
        # include majority blockchain state + all node's local transactions that would achieve consensus
        transaction_tally = {}
        for node in self.voting_computers:
            # AGGREGATE all open and verified transactions for all nodes
            for tx in node.verified_transactions:
                if tx in transaction_tally:
                    transaction_tally[tx] += 1
                else:
                    transaction_tally[tx] = 1

        approved_transactions = []
        ballots = []
        network_size = len(self.voting_computers)
        for tx, num_approvals in transaction_tally.items():
            if num_approvals/network_size >= MINIMUM_AGREEMENT_PCT:
                approved_transactions.append(tx)
                ballots.append(tx.content)
        results = Ballot.tally(ballots)

        
        # add blockchain results to it
        blockchain_state = self.voting_computers[0].blockchain.current_block.state
        if not results:
            print(json.dumps(blockchain_state, indent=4))
            return
        else:
            print('Blockchain results:')
            print(json.dumps(results, indent=4))
            print('Pending votes:')
            print(json.dumps(blockchain_state, indent=4))
            return
        for item in blockchain_state:
            #import ipdb; ipdb.set_trace()
            for candidate in blockchain_state[item]:
                results[item][candidate] =+ blockchain_state[item][candidate]
        print(json.dumps(results, indent=4))
        '''

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
            self.display_results(nodes_in_sync=False)
        elif choice == 4:
            pass
        elif choice == 5:
            return False
        else:
            print("Unrecognized option")
        return True

    def _authenticate_voter(self, voter_auth_booth):
        """Authenticates voter and returns voter id (None if voter cannot vote)."""
        voter = utils.get_input_of_type(
            "Please authenticate yourself by typing in your full name.\n",
            str
        ).lower()
        voter_id = None

        voters = self.get_voter_by_name(voter)
        if len(voters) > 1:
            voter_id = utils.get_input_of_type(
                "Multiple matches found for {}. Please enter in your voter id.\n".format(voter),
                str
            )
            if voter_id not in [v.id for v in voters]:
                print("Please look up your ID and try again.")
                return None
        elif len(voters) == 1:
            voter_id = voters[0].id

        authenticated = voter_auth_booth.authenticate_voter(voter_id)

        if not authenticated:
            print("{} is not on the voter roll".format(voter))
            return None
        return voter_id

    def vote(self, **kwargs):
        """Simulates voter's experience at authentication and voter booths."""
        voter_auth_booth = random.choice(self.voter_authentication_booths)
        voter_id = self._authenticate_voter(voter_auth_booth)
        if not voter_id:
            return

        # try to retrieve ballot claim ticket
        try:
            ballot_claim_ticket = voter_auth_booth.generate_ballot_claim_ticket(voter_id)
            print("Retrieved ballot claim ticket. Please proceed to the voting booths.\n")
        except NotEnoughBallotClaimTickets as e:
            print(e)
            return

        # vote
        voting_computer = random.choice(self.voting_computers)
        voting_computer.vote(ballot_claim_ticket, **kwargs)

        # TODO: local global counter
        self.num_voters_voted+=1

    def is_election_over(self):
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
            
            self.voter_ballot_selections[voter_id] = {}
            for position in self.ballot.items:
                metadata = self.ballot.items[position]
                if int(voter_id)/self.num_voters <= self.candidate_one_percentage:
                    selected = [0]
                else:
                    selected = [1]
                self.voter_ballot_selections[voter_id][position] = selected

    def setup(self, *args, num_voters=100, **kwargs):
        self.num_voters = num_voters
        super().setup(*args, **kwargs)

    def begin_program(self):
        """
        Overriding flow of program since it doesnt require user interaction
        kwargs:
            selections   
        """
        self.last_time = datetime.now()
    
        utils.clear_screen()
        self.display_header()
        
        for voter in self.voter_roll:
            # get voter's pre-configured choices
            self.vote(selections=self.voter_ballot_selections[voter.id])

            if self.is_consensus_round():
                self.demonstrate_consensus(self.voter_authentication_booths, 'Voter Blockchain')
                self.demonstrate_consensus(self.voting_computers, 'Ballot Blockchain')
            utils.clear_screen()
            self.display_header()

        input("Press any key to continue")

        self.demonstrate_consensus(self.voter_authentication_booths, 'Voter Blockchain')
        self.demonstrate_consensus(self.voting_computers, 'Ballot Blockchain')        
        print("Election over! Results: ")
        self.display_results(nodes_in_sync=True)

    def display_menu(self):
        print('Simulating voting process')

    def get_menu_choice(self):
        return 1  # choice for voting

    def _authenticate_voter(self, voter_auth_booth):
        while self.current_voter_index < len(self.voter_roll):
            voter = self.voter_roll[self.current_voter_index]
            self.current_voter_index += 1
            authenticated = voter_auth_booth.authenticate_voter(voter.id)
            if not authenticated:
                print('Voter {} is not on voter roll'.format(voter.name))
                return None
            else:
                print('Authenticated voter {}'.format(voter.name))
                return voter.id