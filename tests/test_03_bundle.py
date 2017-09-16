from fedoidc.bundle import JWKSBundle

from oic.utils.keyio import build_keyjar

ISS = 'https://example.com'
ISS2 = 'https://example.org'

KEYDEFS = [
    {"type": "RSA", "key": '', "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["sig"]}
]
SIGN_KEYS = build_keyjar(KEYDEFS)[1]

KEYJAR = {}

for iss in ['https://www.swamid.se', 'https://www.sunet.se',
            'https://www.feide.no', 'https://www.uninett.no']:
    KEYJAR[iss] = build_keyjar(KEYDEFS)[1]


def test_create():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    assert bundle


def test_set_get():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    bundle['https://www.swamid.se'] = KEYJAR['https://www.swamid.se']

    # When imported the key in issuer_keys are changed from '' to the issuer ID
    _kj = KEYJAR['https://www.swamid.se'].copy()
    _kj.issuer_keys['https://www.swamid.se'] = _kj.issuer_keys['']
    del _kj.issuer_keys['']

    _sekj = bundle['https://www.swamid.se']
    assert _sekj == _kj


def test_set_del_get():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    bundle['https://www.swamid.se'] = KEYJAR['https://www.swamid.se']
    bundle['https://www.sunet.se'] = KEYJAR['https://www.sunet.se']
    bundle['https://www.feide.no'] = KEYJAR['https://www.feide.no']

    del bundle['https://www.sunet.se']

    assert set(bundle.keys()) == {'https://www.swamid.se',
                                  'https://www.feide.no'}


def test_set_jwks():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    bundle['https://www.sunet.se'] = KEYJAR['https://www.sunet.se'].export_jwks(
        private=True)

    _kj = KEYJAR['https://www.sunet.se'].copy()
    _kj.issuer_keys['https://www.sunet.se'] = _kj.issuer_keys['']
    del _kj.issuer_keys['']

    assert bundle['https://www.sunet.se'] == _kj


def test_dumps_loads():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    bundle['https://www.swamid.se'] = KEYJAR['https://www.swamid.se']
    bundle['https://www.sunet.se'] = KEYJAR['https://www.sunet.se']
    bundle['https://www.feide.no'] = KEYJAR['https://www.feide.no']

    _str = bundle.dumps()

    bundle2 = JWKSBundle(ISS, SIGN_KEYS)
    bundle2.loads(_str)

    assert set(bundle.keys()) == set(bundle2.keys())

    for iss, kj in bundle.items():
        assert bundle2[iss] == kj


def test_sign_verify():
    bundle = JWKSBundle(ISS, SIGN_KEYS)
    bundle['https://www.swamid.se'] = KEYJAR['https://www.swamid.se']
    bundle['https://www.sunet.se'] = KEYJAR['https://www.sunet.se']
    bundle['https://www.feide.no'] = KEYJAR['https://www.feide.no']

    _jws = bundle.create_signed_bundle()

    bundle2 = JWKSBundle(ISS2)
    verify_keys = SIGN_KEYS.copy()
    verify_keys.issuer_keys[ISS] = verify_keys.issuer_keys['']

    bundle2.upload_signed_bundle(_jws, verify_keys)

    assert set(bundle.keys()) == set(bundle2.keys())

    for iss, kj in bundle.items():
        assert bundle2[iss] == kj
