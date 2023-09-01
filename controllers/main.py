import json

import werkzeug.urls

from odoo.http import request
from odoo.addons.auth_oauth.controllers.main import OAuthLogin

#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class OAuthLoginKeyCloak(OAuthLogin):
    def list_providers(self):
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            if provider['name'] == 'Keycloak':
                params_casdoor = dict(
                    apiKey='86ad4c77-3db3-4f37-861b-7e6ac178b98c',
                    ReturnUrl=return_url + "?state={\"d\":\"demo\", \"p\":9}",
                    response_type='code',
                    client_id=provider['client_id'],
                    redirect_uri=return_url,
                    scope=provider['scope'],
                    state=json.dumps(state),                    
                )
                provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params_casdoor))

            else:
                params = dict(
                    response_type='token',
                    client_id=provider['client_id'],
                    redirect_uri=return_url,
                    scope=provider['scope'],
                    state=json.dumps(state),
                )                

                provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.urls.url_encode(params))

        return providers