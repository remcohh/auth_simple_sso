from odoo import api, models, exceptions, _
import logging
import requests
from ..exceptions import OAuthError

logger = logging.getLogger(__name__)
class ResUsers(models.Model):
    _inherit = 'res.users'

    def _simplesso_validate(self, provider, access_token):
        headers = { "apiKey": provider['api_key'] }
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
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = self._simplesso_validate(oauth_provider, access_token)
        validation['user_id'] = validation['EmailAddress'] # validation['sub']
        return validation
    
    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        oauth_uid = validation['user_id']
        try:
            oauth_user = self.search([("login", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_user:
                oauth_user = self.env["res.users"].create({"login": validation['EmailAddress'], "name": f"{validation['Firstname']} {validation['Lastname']}"})
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
        access_token = params.get('SSSOId')
        validation = self._auth_oauth_validate(provider, access_token)
        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise AccessDenied()
        return (self.env.cr.dbname, login, access_token)    

