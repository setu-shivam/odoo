from odoo import fields, models


class State(models.Model):
    _name = 'state'
    _description = 'State'

    name = fields.Char(string='Name', required=True)
    isCapital = fields.Boolean(string='Capital')
    capital_ids = fields.Many2many('city', 'capital_ids', string='Capital of the State', domain="[('isCapital','=',True)]")
    city_ids = fields.One2many('city', 'state_id', string='Cities')
    country_id = fields.Many2one('country', string='Country')
    