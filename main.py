from utils import get_input_of_type
from votingprogram import VotingProgram, Simulation

def main():
    """Entry point of program, in which user gets to run election in (1) adversarial mode, which demonstrates 
    dishonest behavior from up to 20% of the nodes, or (2) normal mode, which runs a clean election. The 
    former is used to assert the validity of our approach by showing that dishonest behavior is detected.
    """
    simulation = input('Enter -1 for simulation, or anything else for main program.')
    simulation = True if simulation == '-1' else False
    adversarial_mode = input('Enter -1 to enable adversarial mode or anything else for a normal election.\n')
    adversarial_mode = True if adversarial_mode == '-1' else False
    consensus_round_interval = 6 if simulation else 30

    program = Simulation() if simulation else VotingProgram()

    # TODO: simulation supports a few types of adversaries and the regular voting program supports all
    
    print("Setting up election...")
    program.setup(adversarial_mode=adversarial_mode, consensus_round_interval=consensus_round_interval)
    input('Set up complete. Press enter to begin election\n')
    program.begin_program()


if __name__ == '__main__':
    main()