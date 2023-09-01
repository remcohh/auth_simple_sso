# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from odoo import api, models, exceptions, _
import logging
import requests
from ..exceptions import OAuthError

logger = logging.getLogger(__name__)


# NOTE: `sub` is THE user id in keycloak
# https://www.keycloak.org/docs/latest/server_development/index.html#_action_token_anatomy  # noqa
# and you cannot change it https://stackoverflow.com/questions/46529363


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _keycloak_validate(self, provider, access_token):
        """Validate token against Keycloak."""
        logger.debug('Calling: %s' % provider.validation_endpoint)
        headers = { "apiKey": "86ad4c77-3db3-4f37-861b-7e6ac178b98c" }
        resp = requests.get(
            provider.validation_endpoint + "/" + access_token,
            headers=headers
        )
        if not resp.ok:
            raise OAuthError(resp.reason)
        validation = resp.json()['ADFS']
        if validation.get("error"):
            raise OAuthError(validation)
        logger.debug('Validation: %s' % str(validation))
        return validation

    @api.model
    def _auth_oauth_validate(self, provider, access_token):
        """Override to use authentication headers.

        The method `_auth_oauth_rpc` is not pluggable
        as you don't have the provider there.
        """
        # `provider` is `provider_id` actually... I'm respecting orig signature
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = self._keycloak_validate(oauth_provider, access_token)
        # clone keycloak ID expected by odoo into `user_id`
        validation['user_id'] = validation['EmailAddress'] # validation['sub']
        return validation
    
    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oauth_uid = validation['user_id']
        try:
            oauth_user = self.search([("login", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_user:
                raise AccessDenied()
            assert len(oauth_user) == 1
            oauth_user.write({'oauth_access_token': params['SSSOId']})
            return oauth_user.login
        except AccessDenied as access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = json.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(provider, validation, params)
            try:
                login, _ = self.signup(values, token)
                return login
            except (SignupError, UserError):
                raise access_denied_exception    
    
    @api.model
    def auth_oauth(self, provider, params):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        access_token = params.get('SSSOId')
        validation = self._auth_oauth_validate(provider, access_token)

        # retrieve and sign in user
        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise AccessDenied()
        # return user credentials
        return (self.env.cr.dbname, login, access_token)    

    def button_push_to_keycloak(self):
        """Quick action to push current users to Keycloak."""
        provider = self.env.ref(
            'auth_keycloak.default_keycloak_provider',
            raise_if_not_found=False
        )
        enabled = provider and provider.users_management_enabled
        if not enabled:
            raise exceptions.UserError(
                _('Keycloak provider not found or not configured properly.')
            )
        wiz = self.env['auth.keycloak.create.wiz'].create({
            'provider_id': provider.id,
            'user_ids': [(6, 0, self.ids)],
        })
        action = self.env.ref('auth_keycloak.keycloak_create_users').read()[0]
        action['res_id'] = wiz.id
        return action
