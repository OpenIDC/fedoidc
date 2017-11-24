import inspect
import sys

import fedoidc
from fedoidc import ClientMetadataStatement
from fedoidc import ProviderConfigurationResponse
from fedoidc.utils import replace_jwks_key_bundle

from oiccli.oic import requests
from oiccli.oic.requests import ProviderInfoDiscovery
from oiccli.oic.requests import RegistrationRequest
from oiccli.request import Request
from oicmsg.exception import ParameterError
from oicmsg.exception import RegistrationError


class FedRegistrationRequest(RegistrationRequest):
    msg_type = ClientMetadataStatement
    response_cls = ClientMetadataStatement

    def __init__(self, httplib=None, keyjar=None, client_authn_method=None,
                 federation_entity=None, **kwargs):
        Request.__init__(self, httplib, keyjar, client_authn_method)
        self.federation_entity = federation_entity

    def federated_client_registration_request(self, cli_info, req_args):
        """
        Constructs a client registration request to be used by a client in a 
        federation.

        :param kwargs: A set of claims that should be part of the registration.
        :return: A :py:class:`ClientMetadataStatement` 
        """

        if cli_info.federation:
            return self.federation_entity.update_request(
                req_args, federation=cli_info.federation)
        elif cli_info.provider_federations:
            return self.federation_entity.update_request(
                req_args, loes=cli_info.provider_federations)

    def pre_construct(self, cli_info, request_args, **kwargs):
        req_args, post_args = RegistrationRequest.pre_construct(self,
            cli_info=cli_info, request_args=request_args, **kwargs)
        req_args = self.federated_client_registration_request(cli_info,
                                                              req_args)
        return req_args, post_args

    def parse_federation_registration(self, resp, cli_info):
        """
        Receives a dynamic client registration response, verifies the
        signature and parses the compounded metadata statement.
        If only one federation are mentioned in the response then the name
        of that federation are stored in the *federation* attribute and
        the flattened response is handled in the normal pyoidc way.
        If there are more then one federation involved then the decision
        on which to use has to be made higher up, hence the list of
        :py:class:`fedoidc.operator.LessOrEqual` instances are stored in the
        attribute *registration_federations*

        :param resp: A MetadataStatement instance or a dictionary
        :param issuer: Issuer ID
        """
        ms_list = self.federation_entity.get_metadata_statement(
            resp, cls=ClientMetadataStatement)

        if not ms_list:  # No metadata statement that I can use
            raise RegistrationError('No trusted metadata')

        # response is a list of registration infos

        # At this point in time I may not know within which
        # federation I'll be working.
        if len(ms_list) == 1:
            ms = ms_list[0]
            cli_info.provider_info = ms.protected_claims()
            cli_info.federation = ms.fo
        else:
            cli_info.registration_federations = ms_list

    def _post_parse_response(self, resp, cli_info, **kwargs):
        self.parse_federation_registration(resp, cli_info=cli_info)


class FedProviderInfoDiscovery(ProviderInfoDiscovery):
    def __init__(self, httplib=None, keyjar=None, client_authn_method=None,
                 federation_entity=None, **kwargs):
        Request.__init__(self, httplib, keyjar, client_authn_method)
        self.federation_entity = federation_entity

    def store_federation_info(self, cli_info, loe):
        """

        :param cli_info: ClientInfo instance
        :param loe: LessOrEqual instance
        """
        _pi = self.response_cls(**loe.protected_claims())

        if 'signed_jwks_uri' in _pi:
            _kb = fedoidc.KeyBundle(source=_pi['signed_jwks_uri'],
                                    verify_keys=loe.signing_keys,
                                    verify_ssl=False)
            _kb.do_remote()
            replace_jwks_key_bundle(self.keyjar, cli_info.issuer, _kb)

        cli_info.provider_info = _pi
        cli_info.federation = loe.fo

    def parse_federation_provider_info(self, resp, cli_info):
        """
        Takes a provider info response and parses it.
        If according to the info the OP has more then one federation 
        in common with the client then the decision has to be handled higher up.
        The list of :py:class:`fedoidc.operator.LessOrEqual` instances are 
        stored in *provider_federations*.
        If the OP and RP only has one federation in common then the choice is
        easy and the name of the federation are stored in the *federation* 
        attribute while the provider info are stored in the normal pyoidc 
        Client way.

        :param resp: A MetadataStatement instance
        :param issuer: The OpenID Provider ID
        """

        les = self.federation_entity.get_metadata_statement(
            resp, cls=ProviderConfigurationResponse)

        if not les:  # No metadata statement that I can use
            raise ParameterError('No trusted metadata')

        # response is a list of metadata statements

        # At this point in time I may not know within which
        # federation I'll be working.
        if len(les) == 1:
            self.store_federation_info(cli_info, les[0])
        else:
            cli_info.provider_federations = les
            for fo in cli_info.fo_priority:
                for _loe in les:
                    if _loe.fo == fo:
                        self.store_federation_info(cli_info, _loe)
                        return
            raise fedoidc.NoSuitableFederation('Available: {}'.format(
                [l.le for l in les]))

    def _post_parse_response(self, resp, cli_info, **kwargs):
        self.parse_federation_provider_info(resp, cli_info)
        if cli_info.provider_info:
            self.match_preferences(cli_info, cli_info.provider_info,
                                   cli_info.issuer)
            requests.ProviderInfoDiscovery._post_parse_response(
                self,  cli_info.provider_info, cli_info, **kwargs)



def factory(req_name, **kwargs):
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and issubclass(obj, Request):
            try:
                if obj.__name__ == req_name:
                    return obj(**kwargs)
            except AttributeError:
                pass

    return requests.factory(req_name, **kwargs)
