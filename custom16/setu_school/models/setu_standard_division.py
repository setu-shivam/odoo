from odoo import fields,models

class SetuStandardDivision(models.Model):
    _name = 'setu.standard.division'
    _description = 'Standard Division'

    name = fields.Char(string='Name', required=True)
    code=fields.Char(string='Code')