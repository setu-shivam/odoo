from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Product(models.Model):
    _name = 'product'
    _description = 'product data'

    name = fields.Char(string='Name', required=True)
    category = fields.Selection([('electronic', 'electronic'), ('non-electronic', 'non-electronic')], string='Category')
    price = fields.Integer(string='Price')
    # price = fields.Monetary(string='Price')
    rating = fields.Float(string='Rating')
    mfgdate = fields.Date(string='Mfg Date')
    status = fields.Boolean(string='Status')


    _sql_constraints = [('name_unique', 'UNIQUE(name)', 'Product Already Exists'),('price_check','check(price >= 0 )','Cant be Less than 0')]
