import utils


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
        selections  pre-determined selections (used by simulation/adversaries)
                      ex: {'President': [0], 'Vice President': [1]}

        Returns whether or not ballot was filled out. This determines whether or not
        a transaction will be created. 

        Future enhancement: Implment retry mechanism, allowing ballots to be invalidated.
        To do this, we would have to support invalidating claim tickets and allowing the
        voter to claim another ticket in its stead.
        """

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

            # no valid selections were made
            if not selection_indexes:
                retry = True

            selections = [metadata['choices'][i] for i in selection_indexes]
            print("Your valid selections: {}".format(selections))
            confirmation = utils.get_input_of_type(
                "Enter 'y' to confirm choices or 'n' to invalidate ballot ",
                str, allowed_inputs=['y', 'n', 'Y', 'N']
            ).lower()
            print()
            if confirmation == 'n':
                retry = True
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
        """Future work"""
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
        returns tally in format
          {
              'president': [{'Obama': 1}, {'Bloomberg': 2}],
              'vice president': [{'Biden': 1}, {'Tusk': 2}]
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


class FlexibleBallot(Ballot):
    """Flexible ballot that allows arbitrary candidates to be added for arbitrary positions."""

    def fill_out(self, selections=None):
        filled_out = super().fill_out(selections=selections)
        if not filled_out:
            return False

        # TODO: handle selections for simulation

        # allow voter to enter custom ballot item
        print('Flexible Ballot -- you can bypass front end and add any candidate / position you would like.\n')
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