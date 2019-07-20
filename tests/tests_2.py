import base
from copy import deepcopy
from election import BallotItem, Choice, Ballot
from constants import STATE
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def sign(message, private_key):
    if type(message) == str:
        message = message.encode()

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature


private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()
message = 'hi'
signature = sign(message, private_key)

vbc = base.VoterBlockchain(None)
print(isinstance(vbc, base.Blockchain))

#print(str(signature))
"""
voting_computer = base.VotingComputer(public_key, private_key)

tx = base.VoteTransaction('content', voting_computer, STATE.CREATED, STATE.ISSUED)
tx_set = set()
tx_set.add(tx)

tx = base.VoteTransaction('content', voting_computer, STATE.CREATED, STATE.ISSUED)
tx_set.add(tx)
tx.content = 'contenttttt'
tx_set.add(tx)

print(len(tx_set))
"""

candidates = [
            Choice("Hillary Clinton (D)"),
            Choice("Donald Trump (R)"),
            Choice("Gary Johnson (L)"),
            Choice("Jill Steel (G)")
        ]
item = BallotItem(
                title="President",
                max_choices=1,
                description="President of the United States",
                choices=candidates
)
items = [item]

b = Ballot("2016 election", items)
ballots = [b]

ledger = base.VoteLedger(ballots)
copied_ledger = ledger.get_copy()

for key in ledger.ledger:
    if isinstance(key, Ballot):
        print(hash(key))

for key in copied_ledger.ledger:
    if isinstance(key, Ballot):
        print(hash(key))

b.items[0].choices[0].chosen = True
print(ledger.ledger[b])

#print(ledger.ledger[b] == copied_ledger.ledger[b])

copied_item = deepcopy(item)


for choice in item.choices:
    choice.select()


for choice in copied_item.choices:
    if choice.chosen:
        print('chosen =[')
    else:
        print('success!')


#print(hash(candidates[0]))