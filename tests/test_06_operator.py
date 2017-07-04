import json
import os
import time
from urllib.parse import quote_plus, urlparse
from urllib.parse import unquote_plus

import shutil

from jwkest import as_unicode
from jwkest.jws import factory

from fedoidc.test_utils import MetaDataStore

from fedoidc.bundle import FSJWKSBundle
from oic.utils.keyio import build_keyjar

from fedoidc import test_utils, MetadataStatement
from fedoidc.operator import FederationOperator
from fedoidc.operator import Operator

KEYDEFS = [
    {"type": "RSA", "key": '', "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["sig"]}
]

TOOL_ISS = 'https://localhost'

FO = {'swamid': 'https://swamid.sunet.se', 'feide': 'https://www.feide.no',
      'edugain': 'https://edugain.com'}

OA = {'sunet': 'https://sunet.se'}

IA = {}

SMS_DEF = {
    OA['sunet']: {
        "discovery": {
            FO['swamid']: [
                {'request': {}, 'requester': OA['sunet'],
                 'signer_add': {'federation_usage': 'discovery'},
                 'signer': FO['swamid'], 'uri': False},
            ],
            FO['feide']: [
                {'request': {}, 'requester': OA['sunet'],
                 'signer_add': {'federation_usage': 'discovery'},
                 'signer': FO['feide'], 'uri': True},
            ],
            FO['edugain']: [
                {'request': {}, 'requester': FO['swamid'],
                 'signer_add': {'federation_usage': 'discovery'},
                 'signer': FO['edugain'], 'uri': True},
                {'request': {}, 'requester': OA['sunet'],
                 'signer_add': {}, 'signer': FO['swamid'], 'uri': True}
            ]
        },
        "registration": {
            FO['swamid']: [
                {'request': {}, 'requester': OA['sunet'],
                 'signer_add': {'federation_usage': 'registration'},
                 'signer': FO['swamid'], 'uri': False},
            ]
        }
    }
}

# Clear out old stuff
for d in ['mds', 'ms_dir', 'ms_path']:
    if os.path.isdir(d):
        shutil.rmtree(d)

liss = list(FO.values())
liss.extend(list(OA.values()))

signer, keybundle = test_utils.setup(
    KEYDEFS, TOOL_ISS, liss, ms_path='ms_path_6', csms_def=SMS_DEF,
    mds_dir='mds_dir_6', base_url='https://localhost')


class Response(object):
    pass


class MockHTTPClient():
    def __init__(self, mds):
        self.mds = mds

    def http_request(self, url):
        p = urlparse(url)
        rsp = Response()
        rsp.status_code = 200
        rsp.text = self.mds[p.path.split('/')[-1]]
        return rsp


def test_key_rotation():
    _keyjar = build_keyjar(KEYDEFS)[1]
    fo = FederationOperator(iss='https://example.com/op', keyjar=_keyjar,
                            keyconf=KEYDEFS, remove_after=1)
    fo.rotate_keys()
    assert len(fo.keyjar.get_issuer_keys('')) == 4
    time.sleep(1)
    fo.rotate_keys()
    assert len(fo.keyjar.get_issuer_keys('')) == 4


def test_pack_metadata_statement():
    jb = FSJWKSBundle('', None, 'fo_jwks',
                      key_conv={'to': quote_plus, 'from': unquote_plus})
    _keyjar = build_keyjar(KEYDEFS)[1]
    op = Operator(keyjar=_keyjar, jwks_bundle=jb, iss='https://example.com/')
    req = MetadataStatement(issuer='https://example.org/op')
    sms = op.pack_metadata_statement(req)
    assert sms  # Should be a signed JWT
    _jwt = factory(sms)
    assert _jwt
    assert _jwt.jwt.headers['alg'] == 'RS256'
    _body = json.loads(as_unicode(_jwt.jwt.part[1]))
    assert _body['iss'] == op.iss
    assert _body['issuer'] == 'https://example.org/op'
    # verify signature
    r = _jwt.verify_compact(sms, _keyjar.get_signing_key())
    assert r


def test_pack_metadata_statement_other_iss():
    _keyjar = build_keyjar(KEYDEFS)[1]
    op = Operator(keyjar=_keyjar, iss='https://example.com/')
    req = MetadataStatement(issuer='https://example.org/op')
    sms = op.pack_metadata_statement(req, iss='https://example.com/')
    assert sms  # Should be a signed JWT
    _jwt = factory(sms)
    _body = json.loads(as_unicode(_jwt.jwt.part[1]))
    assert _body['iss'] == 'https://example.com/'
    # verify signature
    r = _jwt.verify_compact(sms, _keyjar.get_signing_key())
    assert r


def test_pack_metadata_statement_other_alg():
    _keyjar = build_keyjar(KEYDEFS)[1]
    op = Operator(keyjar=_keyjar, iss='https://example.com/')
    req = MetadataStatement(issuer='https://example.org/op')
    sms = op.pack_metadata_statement(req, alg='ES256')
    assert sms  # Should be a signed JWT
    _jwt = factory(sms)
    _body = json.loads(as_unicode(_jwt.jwt.part[1]))
    assert _body['iss'] == 'https://example.com/'
    # verify signature
    r = _jwt.verify_compact(sms, _keyjar.get_signing_key())
    assert r


def test_unpack_metadata_statement_uri():
    s = signer[OA['sunet']]
    req = MetadataStatement(issuer='https://example.org/op')
    # Not intermediate
    ms = s.create_signed_metadata_statement(req, 'discovery')

    jb = FSJWKSBundle('', None, 'fo_jwks',
                      key_conv={'to': quote_plus, 'from': unquote_plus})

    mds = MetaDataStore('mds_dir_6')
    op = Operator(jwks_bundle=jb)
    op.httpcli = MockHTTPClient(mds)
    res = op.unpack_metadata_statement(jwt_ms=ms)
    assert len(res.parsed_statement) == 3
    loel = op.evaluate_metadata_statement(res.result)
    assert len(loel) == 3
    assert set([l.fo for l in loel]) == {'https://swamid.sunet.se',
                                         'https://edugain.com',
                                         'https://www.feide.no'}
