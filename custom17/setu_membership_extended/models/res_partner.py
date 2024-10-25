from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    date_of_birth = fields.Date(string='Date of Birth')
    bloodgroup = fields.Char(string='Blood Group')
    adhar_no = fields.Char(string='Adhar No')
    relation_to_contact = fields.Char(string='Relation')

    @api.model
    def default_get(self, fields):
        res = super(ResPartner, self).default_get(fields)
        res['type'] = 'contact'
        return res
