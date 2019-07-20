"""
This program is a simulation of an electronic voting system that uses blockchain to decentralize 
the collecting, counting, and verification of votes and bring transparency to the whole process.
Blockchain provides a nice audit trail that we thought would be useful in ensuring that tampering
with voting is difficult and can be detected. Our system simulates a hybrid-evoting system that
uses an optical scan ballot, which is then scanned into a computer and put on the blockchain. We 
make use of Ripple's Consensus Process Algorithm and adapt it to fit our voting system.

Acknowledgements:
    This software simulation was created as part of my Adelphi University Honors College undergraduate thesis.
    
    Developers: Mateusz Gembarzewski & Jai Punjwani
    Research Advised By: Kees Leune, PhD.
"""

from setup import VotingProgram
from utils import get_input_of_type


def main():
    """Entry point of program, in which user gets to run election in (1) adversarial mode, which demonstrates 
    dishonest behavior from up to 20% of the nodes, or (2) normal mode, which runs a clean election. The 
    former is used to assert the validity of our approach by showing that dishonest behavior is detected.
    """
    program = VotingProgram()
    mode = get_input_of_type('Enter -1 to enable adversarial mode for this simulation, or 1 for a normal election.\n',
                      int,
                      allowed_inputs={-1,1})
    adversarial_mode = True if mode == -1 else False
    program.set_up_election(adversarial_mode=adversarial_mode)
    input('Set up complete. Press enter to begin election')
    program.begin_election()


if __name__ == '__main__':
    main()
