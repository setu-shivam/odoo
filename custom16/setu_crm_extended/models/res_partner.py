from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    crm_lead_id = fields.Many2one('crm.lead', string='Crm Lead')












