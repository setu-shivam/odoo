from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.template'

    repairable = fields.Boolean(string='Repairable')
    warranty = fields.Selection(selection=[('yes', 'Yes'), ('no', 'No')], string='Warranty', tracking=True,
                                default='yes')
    warranty_period = fields.Integer(string='Warranty Period', help='Warrany Period in Months', default='1')

    @api.constrains('warranty_period')
    def check_warranty_period(self):
        for rec in self:
            if rec.warranty_period <= 0:
                raise ValidationError('Enter Proper Warranty Period')

    @api.onchange('repairable', 'warranty')
    def _onchange_repairable(self):
        for rec in self:
            if rec.repairable == False:
                rec.warranty = 'yes'
                rec.warranty_period = 1
            if rec.warranty == 'no':
                rec.warranty_period = False
