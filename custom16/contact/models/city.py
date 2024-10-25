from odoo import fields, models, api


class City(models.Model):
    _name = 'city'
    _description = 'city'

    name = fields.Char(string='Name', required=True, default='abc', copy=False)
    state_id = fields.Many2one('state', string='State')
    country_city_id = fields.Many2one('country', string='Country')
    isCapital = fields.Boolean(string='Capital')
