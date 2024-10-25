from odoo import fields,models

class SetuStandardMedium(models.Model):
    _name = 'setu.standard.medium'
    _description = 'Standard Medium'

    name = fields.Char(string='Name', required=True)
    code=fields.Char(string='Code')