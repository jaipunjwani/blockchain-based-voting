class BaseException(Exception):
    default_message = None

    def __init__(self, *args, **kwargs):
        if not (args or kwargs): 
            args = (self.default_message,)
        super().__init__(*args, **kwargs) 


class NotEnoughBallotClaimTickets(BaseException):
    default_message = 'You do not have enough claim ticket(s) left'


class InvalidBallot(BaseException):
    default_message = 'Invalid ballot'


class UnrecognizedNode(BaseException):
    default_message = 'Node not recognized'