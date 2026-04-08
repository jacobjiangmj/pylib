import os
import sys
import base64
import hashlib
import binascii

from Crypto.Cipher import AES


class AESCrypto:
    key = os.getenv('AESCrypto.key', 'ERDv2#j.............$6Ip....NR%f')
    vi = os.getenv('AESCrypto.vi', '0102000000060708')

    @staticmethod
    def padding(string):
        return string + (16 - len(string) % 16) * chr(16 - len(string) % 16)

    @staticmethod
    def un_padding(s):
        return s[0:-s[-1]]

    @staticmethod
    def encrypt(data):
        cipher = AES.new(AESCrypto.key.encode('utf8'), AES.MODE_CBC, AESCrypto.vi.encode('utf8'))
        return base64.b64encode(cipher.encrypt(AESCrypto.padding(data).encode('utf8'))).decode('utf8')

    @staticmethod
    def decrypt(data):
        """解密数据，不可解密的以原数据返回"""
        try:
            cipher = AES.new(AESCrypto.key.encode('utf8'), AES.MODE_CBC, AESCrypto.vi.encode('utf8'))
            return AESCrypto.un_padding(cipher.decrypt(base64.decodebytes(data.encode('utf-8')))).decode('utf8')
        except (binascii.Error, ValueError):    # ValueError在params_local和params两次解密出现padding异常。
            return data
        except Exception as e:
            __import__('traceback').print_exception(type(e), e, sys.exc_info()[2])
            return data

    @staticmethod
    def sha256(data):
        return hashlib.sha256(str([round(float(datum), 3) for datum in data]).encode('utf-8')).hexdigest()
