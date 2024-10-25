from odoo import fields, models, api


class Lead(models.Model):
    _inherit = ['crm.lead',]

    partner_ids = fields.One2many('res.partner', 'crm_lead_id', string='Contact', domain=[('active', '=', True)])
    # partner_many_ids = fields.Many2many('res.partner', 'crm_lead_id', string='Contact')











