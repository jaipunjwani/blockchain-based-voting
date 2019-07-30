# TODO: design configuration for secret/non-secret vote
import random
from constants import STATE
from copy import deepcopy

# TODO: remove class; make simple global dictionary?
class Voter:
    """Simple voter class with a name and unique ID"""

    def __init__(self, name, voter_id):
        """
        Args:
            name            Voter's name
            voter_id        Voter's unique ID (pre-assigned by registration authorities)
        """
        self.name = name
        self.id = voter_id  # must be unique
        self.state = STATE.NOT_VOTED

    def __str__(self):
        return self.id

    def get_signature_contents(self, **kwargs):
        """Returns unique representation (ID) for signature.
        Args:
            kwargs          kwargs to control signature (currently not needed)
        """
        return self.id


# TODO: change ballot structure to a dictionary-based class?
class Choice:
    """Choice on a Ballot."""

    def __init__(self, description):
        """
        Args:
            description         string describing the choice (i.e., "Barack Obama (D)")
        """
        self.description = description
        self.chosen = False

    def __str__(self):
        return ":".join([self.description, str(self.chosen)])

    def get_signature_contents(self, include_chosen=True):
        """Returns the description of a choice and (by default) whether it was chosen. The latter can be 
        overridden (useful for transaction signature of a ballot that was newly created and later filled).
        Args:
            include_chosen      indicates that the signature string should include whether the choice was chosen 
        """
        content_list = [self.description]
        if include_chosen:
            content_list.append(str(self.chosen))
        return ":".join(content_list)

    def select(self):
        """Selects choice."""
        self.chosen = True

    def unselect(self):
        """Unselects choice."""
        self.chosen = False


class BallotItem:
    """Item/Position in an election that is represented on a ballot. Ballots can have multiple
    BallotItems that voters can vote on. Moreover, a ballot item can allow one or more selections."""

    def __init__(self, title, description, max_choices, choices):
        """
        Args:
            title               equivalent to the position (e.g., President)
            description         longer description of position (e.g., President of United States)
            max_choices         max number of choices allowed
            choices             list of Choices
        """
        self.title = title
        self.description = description
        self.max_choices = max_choices
        self.choices = deepcopy(choices)

    def __str__(self):
        str_list = [self.title, self.description, str(self.max_choices)]
        str_list.extend([str(choice) for choice in self.choices])
        return ":".join(str_list)

    def get_signature_contents(self, **signature_kwargs):
        """Returns unique representation of BallotItem using its choices.
        Args:
            signature_kwargs        kwargs to control the signature
        """
        str_list = [self.title, self.description, str(self.max_choices)]
        for choice in self.choices:
            str_list.append(choice.get_signature_contents(**signature_kwargs))
        return ":".join(str_list)

    def clear(self):
        """Unselects all choices."""
        for choice in self.choices:
            choice.unselect()

    def max_choices_selected(self):
        """Returns whether or not the maximum number of choices is selected."""
        selected = 0
        for choice in self.choices:
            if choice.chosen:
                selected = selected + 1
            if selected == self.max_choices:
                return True
        return False

    def vote(self, choice_description):
        """Fills out specified choice on ballot.
        Args:
            choice_description          choice description to fill out
        """
        for i in self.choices:
            if choice_description == i.description:
                i.select()


class Ballot:
    """Ballot in an election. Supports multiple positions, or BallotItems."""

    def __init__(self, election, items):
        """
        Args: 
            election            name of election
            items               list of BallotItem objects
        """
        self.id = str(random.getrandbits(128))  # assign a random ID to the ballot
        self.election = election
        self.items = deepcopy(items)  # ballots cannot share reference with the choices

    def __str__(self):
        str_list = [self.id, self.election]
        for item in self.items:
            str_list.append(str(item))
        return ":".join(str_list)

    def get_signature_contents(self, **signature_kwargs):
        """Returns unique signature string of Ballot using its ID, election title, and the signature string of all its BallotItems.
        Args:
            signature_kwargs        kwargs to control signature (currently passed down to control Choice signature)
        """
        str_list = [self.id, self.election]
        for item in self.items:
            str_list.append(item.get_signature_contents(**signature_kwargs))
        return ":".join(str_list)        

    def is_filled(self):
        """Returns whether or not each BallotItem has at least one selected choice."""
        for item in self.items:
            item_filled = False
            for choice in item.choices:
                if choice.chosen:
                    item_filled = True
                    continue
            # if any single ballotitem is not filled
            if not item_filled:
                return False
        return True  # all BallotItems have been checked   

    def get_selected_choices(self):
        """Returns list of selected choices."""
        selected_choices = []
        for item in self.items:
            for choice in item.choices:
                if choice.chosen:
                    selected_choices.append(choice)
        return selected_choices

    def vote(self, title, option):
        """Records the vote on the Ballot.
        Args:
            title       title of the BallotItem
            option      the Choice objet that was selected
        """
        for item in Ballot.items:  # for each item in ballot.items
            if title == item.title:  # if the titles ever match in the iteration
                for choice in item.choices:  # then for every X in option
                    if choice == option:
                        item.vote(option)  # vote for candidate X

    @staticmethod
    def tally(ballots):
        """Tallies the results from a collection of Ballots.
        Args:
            ballots         iterable of Ballots
        Returns:
            dictionary of the candidates and their final tallies
        """
        results = dict()
        for ballot in ballots:
            for item in ballot.items:
                for choice in item.choices:
                    if choice.description not in results:
                        results[choice.description] = 0
                    if choice.chosen:
                        results[choice.description] = results[choice.description] + 1

                    '''
                    if choice.description in results:
                        if choice.chosen:
                            results[choice.description] = results[choice.description] + 1
                    else:
                        results[choice.description] = 0
                        if choice.chosen:
                            results[choice.description] = 1
                    '''
        return results
                