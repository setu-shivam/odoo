from odoo import fields, models,api
from odoo.exceptions import ValidationError

class Order1(models.Model):
    _name = 'order1'
    _description = 'Order'
    _rec_name ='customer_name'

    customer_name = fields.Char(string='Customer Name',required=True,help='name of customer')
    customer_address = fields.Text(string='Customer Address',required=True)
    phone = fields.Char(string='Phone', unaccent=False)
    email = fields.Char(string='Email')
    city_id = fields.Many2one('city', string='Customer City')
    state_id = fields.Many2one('state', string='State')
    country_id = fields.Many2one('country', string='Country')
    #product_name = fields.Char(string='Product Name')
    quantity=fields.Integer(string='Quantity')
    price = fields.Float(string='Price')
    seller_name = fields.Char(string='Seller Name')
    date=fields.Date(string='Date')
    delivered=fields.Boolean(string='Delivered')

    product_ids = fields.Many2many('product',string='Product')


    # @api.model
    # def create(self,vals):
    #     vals.update({'product_ids':1})
    #     return super(Order1, self).create(vals)

    # @api.model
    # def default_get(self,fields):
    #     res = super(Order1,self).default_get(fields)
    #     res['product_ids']='bottle'
    #     return res

    # default = lambda self: self.env['it.recruitment.freelancer.category'].search([('name', '=', 'Freelancer')]).ids)
# default = lambda self: self.env['product'].search([('name','=','bottle')]).ids

