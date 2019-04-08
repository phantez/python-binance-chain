import binascii
from enum import Enum
from typing import Optional

from secp256k1 import PrivateKey
from mnemonic import Mnemonic
from pywallet.utils.bip32 import Wallet as Bip32Wallet

from binance_chain.segwit_addr import address_from_public_key, decode_address
from binance_chain.environment import BinanceEnvironment


class MnemonicLanguage(str, Enum):
    ENGLISH = 'english'
    FRENCH = 'french'
    ITALIAN = 'italian'
    JAPANESE = 'japanese'
    KOREAN = 'korean'
    SPANISH = 'spanish'
    CHINESE = 'chinese_traditional'
    CHINESE_SIMPLIFIED = 'chinese_simplified'


class Wallet:

    def __init__(self, private_key, env: Optional[BinanceEnvironment] = None):
        self._env = env or BinanceEnvironment.get_production_env()
        self._private_key = private_key
        self._pk = PrivateKey(bytes(bytearray.fromhex(self._private_key)))
        self._public_key = self._pk.pubkey.serialize(compressed=True)
        self._address = address_from_public_key(self._public_key, self._env.hrp)
        self._account_number = None
        self._sequence = None
        self._chain_id = None

    @classmethod
    def create_random_wallet(cls, language: MnemonicLanguage = MnemonicLanguage.ENGLISH,
                             env: Optional[BinanceEnvironment] = None):
        """Create wallet with random mnemonic code

        :return:
        """
        m = Mnemonic(language.value)
        phrase = m.generate()
        return cls.create_wallet_from_mnemonic(phrase, env=env)

    @classmethod
    def create_wallet_from_mnemonic(cls, mnemonic: str, env: Optional[BinanceEnvironment] = None):
        """Create wallet with random mnemonic code

        :return:
        """
        seed = Mnemonic.to_seed(mnemonic)
        new_wallet = Bip32Wallet.from_master_secret(seed=seed, network='BTC')
        child = new_wallet.get_child_for_path("44'/714'/0'/0/0")
        return cls(child.get_private_key_hex().decode(), env=env)

    def initialise_wallet(self, client):
        if self._account_number:
            return
        account = client.get_account(self._address)

        self._account_number = account['account_number']
        self._sequence = account['sequence']

        node_info = client.get_node_info()
        self._chain_id = node_info['node_info']['network']

    def increment_account_sequence(self):
        if self._sequence:
            self._sequence += 1

    def decrement_account_sequence(self):
        if self._sequence:
            self._sequence -= 1

    def reload_account_sequence(self, client):
        sequence_res = client.get_account_sequence(self._address)
        self._sequence = sequence_res['sequence']

    def generate_order_id(self):
        return f"{binascii.hexlify(self.address_decoded).decode().upper()}-{(self._sequence + 1)}"

    @property
    def env(self):
        return self._env

    @property
    def address(self):
        return self._address

    @property
    def address_decoded(self):
        return decode_address(self._address)

    @property
    def private_key(self):
        return self._private_key

    @property
    def public_key(self):
        return self._public_key

    @property
    def public_key_hex(self):
        return binascii.hexlify(self._public_key)

    @property
    def account_number(self):
        return self._account_number

    @property
    def sequence(self):
        return self._sequence

    @property
    def chain_id(self):
        return self._chain_id

    def sign_message(self, msg_bytes):
        sig = self._pk.ecdsa_sign(msg_bytes)
        return self._pk.ecdsa_serialize_compact(sig)
