from utils import get_input_of_type
from votingprogram import VotingProgram

def main():
    """Entry point of program, in which user gets to run election in (1) adversarial mode, which demonstrates 
    dishonest behavior from up to 20% of the nodes, or (2) normal mode, which runs a clean election. The 
    former is used to assert the validity of our approach by showing that dishonest behavior is detected.
    """
    program = VotingProgram()
    mode = get_input_of_type(
    	'Enter -1 to enable adversarial mode for this simulation, or 1 for a normal election.\n',
        int,
        allowed_inputs={-1,1}
    )
    adversarial_mode = True if mode == -1 else False
    print("Setting up election...")
    program.setup(adversarial_mode=adversarial_mode)
    input('Set up complete. Press enter to begin election\n')
    program.begin_program()


if __name__ == '__main__':
	main()