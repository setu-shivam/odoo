from odoo import fields, models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_suggest= fields.Boolean(string="Add Suggested Product")
    suggested_product_id=fields.Many2one('product.product',string='Suggested Product')

    @api.onchange('is_suggest')
    def _onchange_is_suggest(self):
        for rec in self:
            if rec.is_suggest:
                rec.suggested_product_id = ''
