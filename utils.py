import hashlib
import os
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def get_key_pair(key_size=512):
    private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=512,
            backend=default_backend()
        )
    public_key = private_key.public_key()
    return public_key, private_key


def sign(message, private_key):
    """Signs a message with an RSA private key.
    Args:
        message             string or bytes message to sign
        private_key         RSA private key
    """
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


def verify_signature(message, signature, public_key):
    """Returns whether or not signature/public key matches expected message hash
    Args:
        message         original message
        signature       signed message
        public_key      RSA public key used to verify signature
    """
    if type(message) == str:
        message = message.encode()
    try:
        public_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        # log 'Invalid signature'
        pass
    except Exception as e:
        print('Unexpected error: {}'.format(e))
    return False


def get_formatted_time_str(date_obj):
    """Returns a string representation of a date object as Y-M-D H:M
    Args:
        date_obj        datetime object
    """
    return date_obj.strftime("%Y-%m-%d %H:%M")


def get_input_of_type(message, expected_type, allowed_inputs=None):
    """Generic function to receive user input of an expected type and restrict to a subset of inputs.
    Args:
        message             message to display to prompt user for input
        expected_type       type of input expected
        allowed_inputs      iterable of allowed input values
    """
    while True:
        try:
            user_input = expected_type(input(message))
            if allowed_inputs:
                if user_input in allowed_inputs:
                    break   # correct input type and part of allowed inputs
                print('Unexpected input')
                continue
            break
        except (ValueError, TypeError):
            print("Wrong type of input")
    return user_input


def clear_screen():
    """Clears terminal screen"""
    os.system('cls||clear')