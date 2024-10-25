from odoo import fields,models,api

class SetuMotherTongue(models.Model):
    _name = 'setu.mother.tongue'
    _description = 'Mother Tongue'

    name = fields.Char(string='Name')
