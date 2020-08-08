import utils
from copy import deepcopy
from base import Ballot, BallotClaimTicket, VotingComputer, VoterAuthenticationBooth


class FlexibleBallot(Ballot):
    """Flexible ballot that allows arbitrary candidates to be added for arbitrary positions."""

    def fill_out(self, selections=None, additional_selections=None):
        """
        additional_selections    additional positions w/ single candidate to add to ballot. should be
                                   in form [{'position': 'prez', 'candidate': 'jai punjwani'}]
        """
        filled_out = super().fill_out(selections=selections)
        if not filled_out:
            return False

        # allow voter to enter custom ballot item
        print('Flexible Ballot -- you can bypass front end and add any candidate / position you would like.\n')
        if additional_selections:
            for selection in additional_selections:
                self.add_item(
                    selection['position'], 
                    description='new position from simulation', 
                    choices=[selection['candidate']], 
                    max_choices=1
                )
                print('Writing in position: {}'.format(selection['position']))
                selected = [0]
                self.select(selection['position'], selected)
        else:
            another_candidate = input("If you wish to write in an additional candidate or vote please enter his/her name. (Press enter to skip)\n")
            if another_candidate:
                position = input("Type in position name\n")
                if position in self.items:
                    # add candidate as a possible choice
                    self.items[position]['choices'].append(another_candidate)
                    selected = [len(self.items[position]['choices']) - 1]  # disregards previous selections, if any
                else:
                    # create new position altogether
                    choices = [another_candidate]
                    self.add_item(position, description='custom user entered', choices=choices, max_choices=1)
                    selected = [0]
                self.select(position, selected)
        return True

    def finalize(self):
        self.finalized = False  # this ballot is never finalized. you can always add items to it


class KeyChangingNodeMixin(object):
    """
    Injects faulty/adversary behavior in node so that it changes its 
    key pair each time it signs something.
    """
    is_adversary = True

    def sign_message(self, message):
        self.public_key, self._private_key = utils.get_key_pair()
        return super().sign_message(message)


class UnrecognizedVoterAuthenticationBooth(KeyChangingNodeMixin,
                                           VoterAuthenticationBooth):
    """
    Voter Auth node that uses different key-pair to simulate out-of-network node.
    """
    is_adversary = True


class AuthBypassVoterAuthenticationBooth(VoterAuthenticationBooth):
    """
    Voter Auth node that bypasses checks for voter auth & ballot claim tickets left.
    """
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
        self.create_transaction(voter)
        return ticket


class DOSVotingComputer(VotingComputer):
    """Voting computer that performs DOS by foregoing participation during consensus round."""
    is_adversary = True

    def check_transactions_for_consensus(self, txs):
        pass  # doesn't vote on validity during consensus


class InvalidBallotVotingComputer(VotingComputer):
    """
    Voting Computer that allows the user to submit arbitrary candidates for arbitrary positions
    """
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