from utils import get_input_of_type
from votingprogram import VotingProgram, Ballot, Simulation

def main():
    """Entry point of program, in which user gets to run election in (1) adversarial mode, which demonstrates 
    dishonest behavior from up to 20% of the nodes, or (2) normal mode, which runs a clean election. The 
    former is used to assert the validity of our approach by showing that dishonest behavior is detected.
    """
    simulation = input('Enter -1 for simulation, or anything else for main program.')
    simulation = True if simulation == -1 else False
    mode = get_input_of_type(
        'Enter -1 to enable adversarial mode for this simulation, or 1 for a normal election.\n',
        int,
        allowed_inputs={-1,1}
    )
    program = Simulation() if simulation else VotingProgram()
    consensus_round_interval = 3 if simulation else 30
    adversarial_mode = True if mode == -1 else False
    print("Setting up election...")
    program.setup(adversarial_mode=adversarial_mode, consensus_round_interval=consensus_round_interval)
    input('Set up complete. Press enter to begin election\n')
    program.begin_program()


def simulation():
    def fill_out(self):
        print ('worked')
    Ballot.fill_out = fill_out
    main()
    #program = VotingProgram()
    #program.setup()


if __name__ == '__main__':
    '''
    choice = input('Enter -1 for simulation, or anything else for main program.')
    if choice == '-1':
        print('Entering simulation mode')
        simulation()
    else:
        print('Entering main program')
        main()
    '''
    main()