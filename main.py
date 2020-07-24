import logging
from utils import get_input_of_type
from election import VotingProgram, Simulation
from adversary import (UnrecognizedVoterAuthenticationBooth, AuthBypassVoterAuthenticationBooth,
    DOSVotingComputer, InvalidBallotVotingComputer)

def main():
    """Entry point of program, in which user gets to run election in Normal mode or Simulation mode.
    Both modes support an additional adversarial flag, which introduces malicious behavior for up to
    20% of the nodes. Adversaries in the system can be used to show that our approach works with the
    aforementioned tolerance level of faulty nodes. 
    """
    simulation_mode = input('Enter -1 for simulation, or anything else for main program.')
    simulation_mode = True if simulation_mode == '-1' else False
    adversarial_mode = input('Enter -1 to enable adversarial mode or anything else for a normal election.\n')
    adversarial_mode = True if adversarial_mode == '-1' else False

    simulation_map = {
        1: {'description': 'Valid voters casting valid votes', 'adversarial': False},
        2: {'description': 'Unknown voter attempting to cast vote', 'adversarial': False, 'kwargs': {'num_unregistered_voters': 10}},
        3: {'description': 'Valid voter attempting to cast extra vote', 'adversarial': False, 'kwargs': {'num_double_voting_voters': 5}},  # voter will vote twice so effectively 10 voters
        # note about 4: this isn't necessarily an adversarial scenario, but we choose to treat it as one here.
        4: {'description': 'Valid voters attempting to cast invalid vote', 'adversarial': True, 'kwargs': {'voting_node_adversary_class': InvalidBallotVotingComputer, 
                                                                                                           'additional_selections': [{'position': 'FakePosition', 'candidate': 'Jai Punjwani'}]}},
        5: {'description': 'Node broadcasting invalid transaction', 'adversarial': True, 'kwargs': {'voter_node_adversary_class': UnrecognizedVoterAuthenticationBooth}},
        6: {'description': 'Adversarial node creating invalid claim tickets', 'adversarial': True, 'kwargs': {'voter_node_adversary_class': AuthBypassVoterAuthenticationBooth}},
        7: {'description': 'Adversarial node not participating in consensus round', 'adversarial': True, 'kwargs': {'voting_node_adversary_class': DOSVotingComputer}},
        8: {'description': 'Custom', 'adversarial': adversarial_mode}  # TODO - future work
    }
    adversary_simulation_indexes = [k for k,v in simulation_map.items() if v['adversarial']]
    setup_kwargs = {}

    # allow user to choose which simulation to run
    if simulation_mode:
        for n in simulation_map:
            # print either adversarial or non-adversarial simulations
            if simulation_map[n]['adversarial'] == adversarial_mode:
                print('({}) {}'.format(n, simulation_map[n]['description']))
        simulation_number = int(input('Enter a simulation number: '))

        try:
            simulation = simulation_map[simulation_number]
            if simulation_number in adversary_simulation_indexes and not adversarial_mode:
                print('Wrong index. Defaulting to (1)')
                simulation_number = 1
            setup_kwargs.update(simulation.get('kwargs', {}))
            if simulation_number == 8:
                exit('Custom mode is for future development.')
        except KeyError:
            print ("Wrong index. Defaulting to (1)")
            simulation_number = 1

    # adversarial in normal program mode 
    elif adversarial_mode:
        # prompt user to select adversary of choice
        voting_node_key = 'voting_node_adversary_class'
        voter_node_key = 'voter_node_adversary_class'
        adversary_classes = {
            voter_node_key: [UnrecognizedVoterAuthenticationBooth, AuthBypassVoterAuthenticationBooth],
            voting_node_key: [InvalidBallotVotingComputer, DOSVotingComputer]
        }

        blockchain_names = {
            voter_node_key: 'Voter Blockchain',
            voting_node_key: 'Ballot Blockchain'
        }

        for i, blockchain_key in enumerate([voter_node_key, voting_node_key]):
            blockchain_name = blockchain_names[blockchain_key]
            _input = input('Enter {} for {} or anything else to skip.\n'.format(i, blockchain_name))
            if _input == str(i):
                for index, adversary_class in enumerate(adversary_classes[blockchain_key]):
                    print ('({}) {}'.format(index, adversary_class.__name__))
                node_index = int(input('Choose an adversary node.'))
                try:
                    setup_kwargs.update(
                        {blockchain_key: adversary_classes[blockchain_key][node_index]}
                    )
                except (TypeError, KeyError) as e:
                    print('Invalid index. exiting..')
                    exit()

    program = Simulation() if simulation_mode else VotingProgram()
    consensus_round_interval = 6 if simulation_mode else 30
    
    print("Setting up election...")
    program.setup(
        adversarial_mode=adversarial_mode, 
        consensus_round_interval=consensus_round_interval,
        **setup_kwargs
    )
    input('Set up complete. Press enter to begin election\n')
    program.begin_program()


if __name__ == '__main__':
    main()