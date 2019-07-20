class STATE:
    """Various states that entities can be in"""

    # voter states
    NOT_VOTED = 'not voted'
    VOTED = 'voted'

    # ballot states
    CREATED = 'ballot_created'
    ISSUED = 'ballot_issued'
    USED = 'ballot_used'


class NODE_TYPE:
    """Types of nodes"""
    
    VOTING = 'voting node'
    VOTER = 'voter node'
