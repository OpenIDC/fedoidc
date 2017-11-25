# -*- coding: utf-8 -*-

keys = [
    {"type": "RSA", "key": "keys/enc_key.pem", "use": ["enc"]},
    {"type": "RSA", "key": "keys/sig_key.pem", "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["enc"]}
]

ISSUER = 'https://localhost'
SERVICE_URL = "{issuer}/verify"

# Only Username and password.
AUTHENTICATION = {
    "UserPassword": {"ACR": "PASSWORD", "WEIGHT": 1, "URL": SERVICE_URL,
                     "END_POINTS": ["verify"]}
}

PASSWD = {
    "diana": "krall",
    "babs": "howes",
    "upper": "crust"
}

JWKS_FILE_NAME = "static/jwks.json"

MAKO_ROOT = './'

COOKIENAME = 'pyoic'
COOKIETTL = 4 * 60  # 4 hours
SYM_KEY = "SoLittleTime,Got"

SERVER_CERT = "certs/cert.pem"
SERVER_KEY = "certs/key.pem"
# CA_BUNDLE="certs/chain.pem"
CA_BUNDLE = None

# =======  SIMPLE DATABASE ==============

USERINFO = "SIMPLE"

USERDB = {
    "diana": {
        "sub": "dikr0001",
        "name": "Diana Krall",
        "given_name": "Diana",
        "family_name": "Krall",
        "nickname": "Dina",
        "email": "diana@example.org",
        "email_verified": False,
        "phone_number": "+46 90 7865000",
        "address": {
            "street_address": "Umeå Universitet",
            "locality": "Umeå",
            "postal_code": "SE-90187",
            "country": "Sweden"
        },
    },
    "babs": {
        "sub": "babs0001",
        "name": "Barbara J Jensen",
        "given_name": "Barbara",
        "family_name": "Jensen",
        "nickname": "babs",
        "email": "babs@example.com",
        "email_verified": True,
        "address": {
            "street_address": "100 Universal City Plaza",
            "locality": "Hollywood",
            "region": "CA",
            "postal_code": "91608",
            "country": "USA",
        },
    },
    "upper": {
        "sub": "uppe0001",
        "name": "Upper Crust",
        "given_name": "Upper",
        "family_name": "Crust",
        "email": "uc@example.com",
        "email_verified": True,
    }
}

# === These are the federation specific things ====

# Key used by the OP to sign metadata stetments
SIG_DEF_KEYS = [{"type": "RSA", "key": "keys/op_key.pem", "use": ["sig"]}]

# Where the OP can find signed metadata statements
MS_DIR = 'ms'

# Where FO keys are found
JWKS_DIR = 'jwks_dir'
FO_JWKS = '../fo_jwks'

# Priority order between the federations.
# MUST contain all the federations this OP belongs to.
PRIORITY = ['https://swamid.sunet.se']

# Superior
SUPERIOR = 'https://sunet.se'

# Where a signed version of the JWKS is kept
SIGNED_JWKS_PATH = 'static/signed_jwks.jose'
SIGNED_JWKS_ALG = 'RS256'
