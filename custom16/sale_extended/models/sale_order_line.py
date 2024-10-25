from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    extra_price = fields.Integer(string='Extra Price')

    @api.model
    def create(self, vals):

        search_laptop_id = self.env['product.product']
        laptop_product_id = self.env.ref('sale_extended.product_product_computer_desk')
        for rec in self:
            # if rec.product_id.name==laptop_product_id':
            _logger.info(">>>>>>>>>>>>>laptop")
            # self.env['sale.order.line'].create({'product_id': self.env['product.product'].search([('name','=','mouse')]).id,'order_id':rec.order_id})
        return super(SaleOrderLine,self).create(vals)
                



    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.order_id.partner_id,
            currency=self.order_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit+self.extra_price,
            quantity=self.product_uom_qty,
            discount=self.discount,
            price_subtotal=self.price_subtotal,
        )




