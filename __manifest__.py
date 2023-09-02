# Copyright 2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "simpleSSO auth integration",
    "summary": "Integrate simpleSSO into your SSO",
    "version": "0.1",
    'category': 'Tools',
    "website": "",
    'author': 'Remco Huijdts, Maastricht University',
    "license": "AGPL-3",
    "depends": [
        "auth_oauth",
    ],
    "data": [
        'data/auth_oauth_provider.xml',
        'views/auth_oauth_views.xml',
        'views/res_users_views.xml',
    ],
}
