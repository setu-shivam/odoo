# -*- coding: utf-8 -*-

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def preparation_of_sale_order_line_vals(self, vals):
        sale_order_line_obj = self.env['sale.order.line']
        order_line_vals = {'order_id': vals.get('order_id', False),
                           'product_id': vals.get('product_id', False),
                           'company_id': vals.get('company_id', False),
                            'name': vals.get('name', ''),
                           'product_uom': vals.get('product_uom')}
        new_order_line = sale_order_line_obj.new(order_line_vals)
        new_order_line._onchange_product_id_warning()
        order_line_vals = sale_order_line_obj._convert_to_write(
            {name: new_order_line[name] for name in new_order_line._cache})
        order_line_vals.update({'order_id': vals.get('order_id', False),
                                'product_uom_qty': vals.get('order_qty', 0.0),
                                'price_unit': vals.get('price_unit', 0.0),
                                'discount': vals.get('discount', 0.0),
                                'state': 'draft'})
        return order_line_vals
