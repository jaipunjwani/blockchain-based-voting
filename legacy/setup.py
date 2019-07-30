import base
import random
import time
import utils
from constants import NODE_TYPE
from copy import deepcopy
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from decimal import Decimal
from election import Ballot, BallotItem, Choice, Voter

MINIMUM_AGREEMENT_PCT = 0.8  # required consensus for blockchain approval

def create_nodes(NodeClass, num_nodes=50, adversary=None):
    """Creates the specified number of Node objects and returns a list.
    Args:
        NodeClass       Subclass of Node to use for construction
        num_nodes       number of nodes to create
        adversary       whether or not Node should be adversaries
    """
    nodes = []

    # create Nodes as well as public_key-node dictionary mapping
    for node in range(num_nodes):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=512,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        node = NodeClass(public_key, private_key, adversary=adversary)
        nodes.append(node)
    return nodes


def set_up_node_mapping(node_list):
    """Generates the mapping of Node objects to their public key, and sets this mapping
    for each of the nodes.
    Args:
        node_list       list of nodes to create mapping for
    """
    node_mapping = dict()
    for node in node_list:
        node_mapping[hash(node.public_key)] = node

    for node in node_list:
        # create separate copy of mapping for each node, since nodes delete their own key from the dictionary
        node.set_node_mapping(dict(node_mapping))


class VotingProgram:
    """Main voting program that sets up and runs election"""
    VOTING_ADVERSARY_CLASSES = [base.BallotChangingVotingComputer, 
                                base.DoubleSpendingVotingComputer,
                                base.RecordTamperingVotingComputer]

    VOTER_ADVERSARY_CLASSES = [base.AuthorizationBypassVoterComputer]


    def set_up_election(self, adversarial_mode=False, num_nodes=50):
        """
        Args:
            adversarial_mode        determines whether program will run with adversary nodes for the simulation
            num_nodes               total number of nodes in election
        """
        self.adversarial_mode = False  #adversarial_mode

        # choose adversary type and dynamically set the number of adversary/honest nodes
        if adversarial_mode:
            adversary_classes = self.VOTER_ADVERSARY_CLASSES  # TODO: disable once testing over
            self.adversary_class = random.choice(adversary_classes)
            # check the type of adversary
            if self.adversary_class in self.VOTER_ADVERSARY_CLASSES:
                self.adversary_class_type = NODE_TYPE.VOTER
            else:
                self.adversary_class_type = NODE_TYPE.VOTING

            num_honest_nodes = int((num_nodes * MINIMUM_AGREEMENT_PCT)) + 1
            num_adversary_nodes = num_nodes - num_honest_nodes
        else:
            num_honest_nodes = num_nodes

        # create sample election w/ ballot contents
        election = "2020 U.S. Federal Election"
        candidates = [
            Choice("Barack Obama (D)"),
            Choice("Michael Bloomberg (R)"),
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

        candidates = [
            Choice("Joe Biden (D)"),
            Choice("Mike Pence (R)"),
        ]
        ballot_item_2 = BallotItem (
                title="Vice President",
                max_choices=1,
                description="Vice President of the United States",
                choices=candidates
        )
        # items.append(ballot_item_2)

        # set up voting computers, voter computers, ballot generator w/ key pairs & blockchain instances
        print('Setting up voting computers, voter computers, and ballot generator')
        self.voting_computers = create_nodes(base.VotingComputer, num_nodes=num_honest_nodes)
        self.voter_computers = create_nodes(base.VoterComputer, num_nodes=num_honest_nodes)
        self.ballot_generator = create_nodes(base.BallotGenerator, num_nodes=1)[0]

        if adversarial_mode:
            # construct adversary nodes & add to network
            self.adversary_computers = create_nodes(self.adversary_class, num_nodes=num_adversary_nodes, adversary=True)

            node_list = self.voting_computers if self.adversary_class_type == NODE_TYPE.VOTING else self.voter_computers

            for node in self.adversary_computers:
                node_list.append(node)
            '''
            # construct adversary nodes & add to network
            self.adversary_voting_computers = create_nodes(self.adversary_class, num_nodes=num_adversary_nodes, adversary=True)
            self.adversary_voter_computers = create_nodes(self.adversary_class, num_nodes=num_adversary_nodes, adversary=True)
            
            for node in self.adversary_voting_computers:
                self.voting_computers.append(node)
            for node in self.adversary_voter_computers:
                self.voter_computers.append(node)
            '''
        # add mapping of node-public key to all nodes
        set_up_node_mapping(self.voting_computers)
        set_up_node_mapping(self.voter_computers)

        # give ballot generator mapping of voting computers
        self.ballot_generator.set_node_mapping(
            {hash(node.public_key): node for node in
             self.voting_computers}
        )

        # set ballot generator for each voting computer
        for voting_computer in self.voting_computers:
            voting_computer.set_ballot_generator(self.ballot_generator)

        # TODO: read in voter roll from file; assign incrementing voter ID
        voter_roll_file = '/'
        print('Extracted voter roll from {}'.format(voter_roll_file))
        self.voter_roll = [Voter('Mateusz Gembarzewski', '1'),
                           Voter('Jai Punjwani', '2')]

        # TODO: generate ballot claim tickets ahead of time?
        # generate ballots using the election and ballot content. generate same number of ballots as registered voters
        print('Voter registration closed. Generating {} ballots'.format(len(self.voter_roll)))
        ballots = self.ballot_generator.generate_ballots(election, items, num_ballots=len(self.voter_roll))

        # TODO: make id a simple incrementer?
        # ensure that ballot IDs are unique by adding all IDs to a master set & checking that set length = ballot list length
        ballot_ids = set()
        for ballot in ballots:
            ballot_ids.add(ballot.id)

        if len(ballot_ids) != len(ballots):
            raise Exception("Generated non-unique ballot")

        # TODO: make paper trail configurable for paper-based system
        # holds filled out ballots.
        self.paper_trail = []

        # TODO: eliminate ledger; instead, count blocks on the fly
        # initialize ledgers
        voter_ledger = base.VoterLedger(self.voter_roll)
        vote_ledger = base.VoteLedger(ballots)

        # initialize separate copy of blockchains for each node
        for voting_computer in self.voting_computers:
            voting_computer.set_blockchain(base.VoteBlockchain(vote_ledger.get_copy()))

        for voter_computer in self.voter_computers:
            voter_computer.set_blockchain(base.VoterBlockchain(voter_ledger.get_copy()))

    def begin_election(self):
        """Start of election. Controls flow of voting program."""
        exit = False
        print('Start of election!')
        while not exit and self.ballot_generator.are_ballots_available():
            utils.clear_screen()
            self.print_menu()
            menu_choice = utils.get_input_of_type("Please enter choice:", int)
            exit = self.handle_input(menu_choice)
            input("Press enter to advance")
        print('Election Over!')
        utils.clear_screen()
        self.show_consensus(self.voter_computers, 'Voter Blockchain')
        time.sleep(2)
        print()
        self.show_consensus(self.voting_computers, 'Vote Blockchain')
        time.sleep(2)
        
        # print out blockchain results
        print('\nBlockchain Results:')
        blockchain_results = self.voting_computers[0].blockchain.current_ledger
        for ballot_item in blockchain_results.content[0].items:
            for candidate in ballot_item.choices:
                print('{}: {}'.format(candidate.description, blockchain_results.ledger[candidate.description]))
        
        time.sleep(2)
        
        # print out paper trail results for comparison
        '''
        paper_tally_results = Ballot.tally(self.paper_trail)
        print('\nPaper Trail Results:')
        for key in paper_tally_results:
            print(key, ": ", paper_tally_results[key])
        '''

    def print_menu(self):
        if self.adversarial_mode:
            print('Mode: {}'.format('Adversarial'))
            print('Behavior: {}'.format(self.adversary_class.behavior_message))
            print('Takeaway: {}'.format(self.adversary_class.simulation_message))
        else:
            print('Mode: {}'.format('Normal'))
        print()
        print("(1) Vote")
        print("(2) View Current Results")
        print("(3) View Logs")
        print("(4) Inspect Ledger")
        print("(5) exit")
        print()

    def handle_menu_option(self, menu_number):
        """Redirects user to appropriate method and returns whether or not program should exit.
        Args:
            menu_number         menu option to be used for redirection
        """
        if menu_number == 5:
            return True
        elif menu_number == 4:
            pass
        elif menu_number == 3:
            pass
        elif menu_number == 2:
            pass
        elif menu_number == 1:
            self.begin_voting_process()
        return False  # meaning that program will not exit

    def begin_voting_process(self):
        """Handles full voting flow for user."""
        for voter in self.voter_roll:
            print(voter.id, voter.name)

        # Allow user to self-authenticate
        voter_id = utils.get_input_of_type("Please enter your voter ID: ", str)
        voter = self.get_voter_by_id(voter_id)
        if not voter:
            print("Incorrect ID entered.")
            return
        print('Voter authenticated')

        # check that voter has not voted before
        if self.adversarial_mode and self.adversary_class_type == NODE_TYPE.VOTER:
            voter_computer = random.choice(self.adversary_computers)
        else:
            voter_computer = random.choice(self.voter_computers)
        voted = voter_computer.has_voter_voted(voter)
        if voted:
            print('You have already voted!')
            return

        # voter has not voted; retrieve a ballot from the ballot generator
        ballot = self.ballot_generator.retrieve_ballot()  # creates transaction for the ballot as well
        print('Retrieved random ballot (ID:{})'.format(str(ballot.id)))

        # create transaction on voter computer indicating that voter has retrieved ballot (we say that they have effectively voted)
        print('Creating transaction on voter blockchain: {} has retrieved a ballot'.format(voter.name))
        print('Broadcasting transaction to all voting computers')
        #import ipdb; ipdb.set_trace()
        voter_computer.create_transaction(voter)

        # voter visits random voting computer
        if self.adversarial_mode and self.adversary_class_type == NODE_TYPE.VOTING:
            voting_computer = random.choice(self.adversary_computers) 
        else:
            voting_computer = random.choice(self.voting_computers)
        print('Now at voting booth')
        
        # voter fills out ballot and confirms choice
        self.process_ballot(ballot)
        ballot_filled = ballot.is_filled()

        # ensures that ballot is filled out
        while not ballot_filled:
            self.process_ballot(ballot)
            ballot_filled = ballot.is_filled()
        input("Press enter to submit your ballot")

        # submit ballot to paper trail
        self.paper_trail.append(deepcopy(ballot))  # add ballot to paper trail; deepcopy added because of object reference possession in adversary's hands

        # create a transaction with the ballot
        voting_computer.create_transaction(ballot)
        print("Created a transaction with the ballot on the vote blockchain.")

        # TODO: allow user to request new ballot
        # TODO: handle state of select/chosen for multi-choice options

    def get_voter_by_id(self, id):
        """Returns voter that matches provided ID.
        Args:
            id      ID of expected voter
        """
        for voter in self.voter_roll:
            if voter.id == id:
                return voter
        return None

    def process_ballot(self, ballot):
        """Prints out each ballot item and allows user to select and verify a choice for each.
        Args:
            ballot      ballot that user fills out
        """
        for item in ballot.items:
            if item.max_choices_selected():
                continue

            choice_num = 1
            print(item.description)
            for choice in item.choices:
                choice_str_list = [str(choice_num), ':', choice.description]
                if choice.chosen:
                    choice_str_list.append('SELECTED')
                print(" ".join(choice_str_list))
                choice_num = choice_num + 1

            candidate_selection = utils.get_input_of_type("Please enter the number of the candidate to bubble in your optical scan ballot: ", 
                                                          int, 
                                                          list(range(1, len(item.choices)+1))
            )
            candidate_index = candidate_selection - 1
            confirmed = utils.get_input_of_type("Enter 'y' to confirm selection or 'n' to reject. " + item.choices[candidate_index].description + ": ",
                                                str,
                                                ['y','n']
            )
            if confirmed == 'y':
                item.choices[candidate_index].select()
            else:
                pass  # outer while loop should ensure that all ballot items are filled

    def show_consensus(self, node_list, network_name):
        """Demonstrates consensus process for both VoterBlockchain and VoteBlockchain.
        Args:
            node_list       list of nodes participating in Blockchain
            network_name    name of Blockchain; used in output
        """
        # compute the expected consensus percentage based on honest/adversary nodes
        num_nodes = len(node_list)
        num_adversary_nodes = 0
        for node in node_list:
            if node.adversary:
                num_adversary_nodes = num_adversary_nodes + 1
        honest_node_pct = (1 - (num_adversary_nodes/num_nodes)) * 100
        honest_node_pct = Decimal(honest_node_pct).quantize(Decimal(10) ** -2)
        print('Demonstrating consensus process among nodes in the {}'.format(network_name))
        print('Total nodes: {}.\tAdversary Nodes:{}\tExpected Consensus:{}%'.format(str(num_nodes),
                                                                                    str(num_adversary_nodes),
                                                                                    str(honest_node_pct)))
        # nodes broadcast transactions to each other so everyone has the master list
        for node in node_list:
            node.broadcast_transactions()
        print('All nodes have sent their transactions to each other')

        """
        all nodes vote on the validity of each transaction by processing it.
        this is already done b/c each node verifies each transaction as it receives it.
        """

        # now all nodes send each other what their VALID transactions are
        for node in node_list:
            node.send_nodes_transactions_for_consensus()

        # Nodes aggregate transactions with enough approval
        tally = node_list[0].transaction_tally  # use first node since all of them have the same master list
        num_nodes = len(node_list)
        approved_transaction_list = []
        for node in node_list:
            # keep only the ones with enough approval
            tally = node.transaction_tally
            total_transactions = 0
            approved_transactions = 0
            rejected_transactions = 0
            for tx in tally.keys():  # iterate through master transaction set
                total_transactions = total_transactions + 1
                if tally[tx]/num_nodes < MINIMUM_AGREEMENT_PCT:
                    print('{} approvals'.format(str(tally[tx])))
                    node.rejected_transactions.add(tx)
                    rejected_transactions = rejected_transactions + 1
                    print("transaction only received {}% approval from network. Rejected.".format(str(100*tally[tx]/num_nodes)))
                else:
                    approved_transaction_list.append(tx)
                    approved_transactions = approved_transactions + 1

        # show aggregate statistics on consensus
        print('Approved: {}\tRejected:{}'.format(approved_transactions, rejected_transactions))

        # create block with the approved transactions
        print('Consensus round over. Creating block on {}.'.format(network_name)) 
        for node in node_list:
            node.blockchain.add_block(node, approved_transaction_list)