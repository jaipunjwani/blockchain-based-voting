import logging
from utils import get_input_of_type
from votingprogram import VotingProgram, Simulation
from base import (UnrecognizedVoterAuthenticationBooth, AuthBypassVoterAuthenticationBooth,
    DOSVotingComputer, InvalidBallotVotingComputer)

def main():
    """Entry point of program, in which user gets to run election in Normal mode or Simulation mode.
    Both modes support an additional adversarial flag, which introduces malicious behavior for up to
    20% of the nodes. Adversaries in the system can be used to show that our approach works with the
    aforementioned tolerance level of faulty nodes. 
    """
    simulation = input('Enter -1 for simulation, or anything else for main program.')
    simulation = True if simulation == '-1' else False
    adversarial_mode = input('Enter -1 to enable adversarial mode or anything else for a normal election.\n')
    adversarial_mode = True if adversarial_mode == '-1' else False

    simulation_map = {
        1: {'description': 'Valid voters casting valid votes', 'adversarial': False},
        2: {'description': 'Unknown voter attempting to cast vote', 'adversarial': False},
        3: {'description': 'Valid voter attempting to cast extra vote', 'adversarial': False},
        # note about 4: this isn't necessarily an adversarial scenario, but we choose to treat it as one here.
        4: {'description': 'Valid voters attempting to cast invalid vote', 'adversarial': True},
        5: {'description': 'Node broadcasting invalid transaction', 'adversarial': True},
        6: {'description': 'Adversarial node creating invalid claim tickets', 'adversarial': True},
        7: {'description': 'Adversarial node not participating in consensus round', 'adversarial': True},
        8: {'description': 'Custom', 'adversarial': adversarial_mode}
    }
    # allow user to choose which simulation to run
    if simulation:
        for n in simulation_map:
            print('({}) {}'.format(n, simulation_map[n]['description']))
        simulation_number = int(input('Enter a simulation number: '))
        
        if adversarial_mode:
            pass

    # adversarial in normal program mode 
    elif adversarial_mode:
        # prompt user to select adversary of choice
        pass


    consensus_round_interval = 6 if simulation else 30

    program = Simulation() if simulation else VotingProgram()

    # TODO: simulation supports a few types of adversaries and the regular voting program supports all
    
    print("Setting up election...")
    program.setup(
        adversarial_mode=adversarial_mode, 
        consensus_round_interval=consensus_round_interval,
        voter_node_adversary_class=None,
        voting_node_adversary_class=None
    )
    input('Set up complete. Press enter to begin election\n')
    program.begin_program()


if __name__ == '__main__':
    main()