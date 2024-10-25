# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = "stock.quant"

    is_ecommerce_inventory_adjustment = fields.Boolean(string="Is eCommerce Inventory Adjustment", default=False)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)

    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)

    @api.model
    def _get_inventory_fields_write(self):
        """ Returns a list of fields user can edit when he want to edit a quant in `inventory_mode`.
        """
        fields = super(StockQuant, self)._get_inventory_fields_write()
        fields += ['is_ecommerce_inventory_adjustment', 'multi_ecommerce_connector_id']
        return fields

    @api.model
    def create_ecommerce_stock_inventory(self, products, location_id, is_auto_validate_inventory=False):
        stock_quant_lst = []
        for product_dict in products:
            if product_dict.get('product_id') and product_dict.get('product_qty'):
                existing_stock_quant_id = self.search(
                    [('location_id', '=', location_id.id), ('product_id', '=', product_dict.get('product_id').id)],
                    limit=1)
                if existing_stock_quant_id:
                    existing_stock_quant_id.write({"inventory_quantity": product_dict.get('product_qty')})

                if not existing_stock_quant_id:
                    existing_stock_quant_id = self.create({'company_id': self.company_id.id,
                                                           "product_id": product_dict.get('product_id').id,
                                                           'location_id': location_id.id,
                                                           "inventory_quantity": product_dict.get('product_qty'),
                                                           'product_uom_id': product_dict.get(
                                                               'product_id').uom_id.id if product_dict.get(
                                                               'product_id').uom_id else False})
                if existing_stock_quant_id:
                    stock_quant_lst.append(existing_stock_quant_id.id)
        if stock_quant_lst and is_auto_validate_inventory:
            for stock_quant_id in stock_quant_lst:
                stock_quant_id = self.browse(stock_quant_id)
                stock_quant_id.action_apply_inventory()
        return stock_quant_lst
