from pylib.log import log
from pylib.crypto import AESCrypto
from pylib.api.gitlab_api import GitlabApi


class Main:
    @staticmethod
    def run():
        GitlabApi.get_protected_branch('ci', 'master')
        log.info(AESCrypto.encrypt('goz9O1....11111.cAMuBihtqcm'))
        log.info(AESCrypto.decrypt('hj8E5B76WcvMUa7a36J9EMM8kQra3IVi3V+ge6vj1IA='))


if __name__ == "__main__":
    Main().run()
