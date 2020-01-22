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