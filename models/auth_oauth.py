from odoo import fields, models, api

class OAuthProvider(models.Model):
    _inherit = 'auth.oauth.provider'
    api_key = fields.Char()