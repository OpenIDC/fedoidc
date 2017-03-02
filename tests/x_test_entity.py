import json
import os
import shutil
from time import time
from future.backports.urllib.parse import quote_plus, unquote_plus

from jwkest.jwk import rsa_load

from fedoidc import ClientMetadataStatement
from fedoidc.bundle import FSJWKSBundle
from fedoidc.bundle import JWKSBundle
from fedoidc.entity import FederationEntity
from fedoidc.operator import Operator

from oic import rndstr
from oic.utils.authn.authn_context import AuthnBroker
from oic.utils.authn.user import UserAuthnMethod
from oic.utils.authz import AuthzHandling
from oic.utils.keyio import KeyBundle
from oic.utils.keyio import KeyJar
from oic.utils.keyio import build_keyjar
from oic.utils.userinfo import UserInfo

BASE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data/keys"))
_key = rsa_load(os.path.join(BASE_PATH, "rsa.key"))
KC_RSA = KeyBundle({"key": _key, "kty": "RSA", "use": "sig"})

CLIENT_ID = "client_1"

KEYDEFS = [
    {"type": "RSA", "key": '', "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["sig"]}
]

CONSUMER_CONFIG = {
    "authz_page": "/authz",
    "scope": ["openid"],
    "response_type": ["code"],
    "user_info": {
        "name": None,
        "email": None,
        "nickname": None
    },
    "request_method": "param"
}

SERVER_INFO = {
    "version": "3.0",
    "issuer": "https://connect-op.heroku.com",
    "authorization_endpoint": "http://localhost:8088/authorization",
    "token_endpoint": "http://localhost:8088/token",
    "flows_supported": ["code", "token", "code token"],
}

BASE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "data/keys"))

KEYJAR = KeyJar()
KEYJAR[""] = KC_RSA

CDB = {}

USERDB = {
    "username": {
        "name": "Linda Lindgren",
        "nickname": "Linda",
        "email": "linda@example.com",
        "verified": True,
        "sub": "username"
    }
}

URLMAP = {CLIENT_ID: ["https://example.com/authz"]}


def _eq(l1, l2):
    return set(l1) == set(l2)


class DummyAuthn(UserAuthnMethod):
    def __init__(self, srv, user):
        UserAuthnMethod.__init__(self, srv)
        self.user = user

    def authenticated_as(self, cookie=None, **kwargs):
        if cookie == "FAIL":
            return None, 0
        else:
            return {"uid": self.user}, time()


# AUTHN = UsernamePasswordMako(None, "login.mako", tl, PASSWD, "authenticated")
AUTHN_BROKER = AuthnBroker()
AUTHN_BROKER.add("UNDEFINED", DummyAuthn(None, "username"))

# dealing with authorization
AUTHZ = AuthzHandling()
SYMKEY = rndstr(16)  # symmetric key used to encrypt cookie info
USERINFO = UserInfo(USERDB)

KEYS = {}
ISSUER = {}
OPERATOR = {}

for entity in ['fo', 'fo1', 'org', 'inter', 'admin', 'ligo', 'op']:
    fname = os.path.join(BASE_PATH, "{}.key".format(entity))
    _keydef = KEYDEFS[:]
    _keydef[0]['key'] = fname

    _jwks, _keyjar, _kidd = build_keyjar(_keydef)
    KEYS[entity] = {'jwks': _jwks, 'keyjar': _keyjar, 'kidd': _kidd}
    ISSUER[entity] = 'https://{}.example.org'.format(entity)
    OPERATOR[entity] = Operator(keyjar=_keyjar, iss=ISSUER[entity])

FOP = OPERATOR['fo']
FOP.fo_keyjar = FOP.keyjar
FO1P = OPERATOR['fo1']
FO1P.fo_keyjar = FO1P.keyjar
ORGOP = OPERATOR['org']
ADMINOP = OPERATOR['admin']
INTEROP = OPERATOR['inter']
LIGOOP = OPERATOR['ligo']
OPOP = OPERATOR['op']


def fo_member(*args):
    _jb = JWKSBundle('')
    for fo in args:
        _jb[fo.iss] = fo.keyjar.issuer_keys['']

    return Operator(jwks_bundle=_jb)


def create_compound_metadata_statement(spec):
    _ms = None
    root_signer = ''
    for op, op_args, signer, sig_args in spec:
        _cms = ClientMetadataStatement(
            signing_keys=op.keyjar.export_jwks(), **op_args)
        if _ms:
            sig_args['metadata_statements'] = [_ms]
        else:  # root signed
            root_signer = signer.iss
        _ms = signer.pack_metadata_statement(_cms, **sig_args)
    return root_signer, _ms


SPEC = [
    [ORGOP, {'contacts': ['info@example.com']},
     FOP, {'alg': 'RS256', 'scope': ['openid']}],
    [INTEROP, {'tos_uri': ['https://rp.example.com/tos.html']},
     ORGOP, {'alg': 'RS256'}],
    [ADMINOP, {'redirect_uris': ['https://rp.example.com/auth_cb']},
     INTEROP, {'alg': 'RS256'}]
]

SMD_DIR = 'sign_mds'
JWKS_DIR = 'fo_jwks'


def populate_sms_dir(spec):
    # populate the signed metadata statements directory
    signer, sms = create_compound_metadata_statement(spec)

    if not os.path.exists(SMD_DIR):
        os.mkdir(SMD_DIR)

    fname = os.path.join(SMD_DIR, quote_plus(signer))
    fp = open(fname, 'w')
    fp.write(sms)
    fp.close()


def populate_jwks_dir(fos):
    # Populate the FO jwks directory
    if not os.path.exists(JWKS_DIR):
        os.mkdir(JWKS_DIR)

    for op in fos:
        fname = os.path.join(JWKS_DIR, quote_plus(op.iss))
        fp = open(fname, 'w')
        fp.write(json.dumps(op.keyjar.export_jwks()))
        fp.close()


JWKS_FILE = 'my.jwks'
fp = open(JWKS_FILE, 'w')
fp.write(json.dumps(OPOP.keyjar.export_jwks(private=True)))
fp.close()


def test_create_entity():
    for _dir in [JWKS_DIR, SMD_DIR]:
        try:
            shutil.rmtree(_dir)
        except Exception:
            pass
        os.makedirs(_dir)

    fo_bundle = FSJWKSBundle(CLIENT_ID, fdir=JWKS_DIR,
                             key_conv={'to': quote_plus, 'from': unquote_plus})

    entity = FederationEntity(None, iss=CLIENT_ID, jwks_file=JWKS_FILE,
                              signed_metadata_statements_dir=SMD_DIR,
                              fo_bundle=fo_bundle)

    assert entity
    assert list(entity.signed_metadata_statements.keys()) == []


def test_create_compound_statement():
    signer, sms = create_compound_metadata_statement(SPEC)

    assert sms
    assert signer == FOP.iss


def test_create_entity_with_fo_jwks_dir():
    for _dir in [JWKS_DIR, SMD_DIR]:
        try:
            shutil.rmtree(_dir)
            os.makedirs(_dir)
        except Exception:
            pass

    populate_jwks_dir([FOP, FO1P])

    fo_bundle = FSJWKSBundle(CLIENT_ID, fdir=JWKS_DIR,
                             key_conv={'to': quote_plus, 'from': unquote_plus})

    entity = FederationEntity(None, iss=CLIENT_ID, jwks_file=JWKS_FILE,
                              signed_metadata_statements_dir=SMD_DIR,
                              fo_bundle=fo_bundle)

    assert entity
    assert set(entity.fo_bundle.keys()) == {'https://fo.example.org',
                                            'https://fo1.example.org'}
    assert list(entity.signed_metadata_statements.keys()) == []


def test_create_entity_with_fo_jwks_and_sms_dirs():
    for _dir in [JWKS_DIR, SMD_DIR]:
        try:
            shutil.rmtree(_dir)
        except Exception:
            pass

    populate_jwks_dir([FOP, FO1P])
    populate_sms_dir(SPEC)

    fo_bundle = FSJWKSBundle(CLIENT_ID, fdir=JWKS_DIR,
                             key_conv={'to': quote_plus, 'from': unquote_plus})

    entity = FederationEntity(None, iss=CLIENT_ID, jwks_file=JWKS_FILE,
                              signed_metadata_statements_dir=SMD_DIR,
                              fo_bundle=fo_bundle)

    assert entity
    assert set(entity.fo_bundle.keys()) == {'https://fo.example.org',
                                            'https://fo1.example.org'}
    assert list(entity.signed_metadata_statements.keys()) == [FOP.iss]

