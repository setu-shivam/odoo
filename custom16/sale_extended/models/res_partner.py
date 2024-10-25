from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # setu_credit_limit = fields.Integer(string='Credit Limit',tracking=True)
    reward_points = fields.Float(string='Reward Points',tracking=True)



