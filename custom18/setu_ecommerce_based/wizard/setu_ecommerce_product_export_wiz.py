# -*- coding: utf-8 -*-
from odoo import models, fields


class SetuEcommerceProductExportWiz(models.TransientModel):
    _name = 'setu.ecommerce.product.export.wiz'
    _description = 'eCommerce Product Export Wiz'

    basic_details = fields.Boolean(string='Basic Details')
    price_export = fields.Boolean(string='Price Export')
    set_image = fields.Boolean(string="Set Image")
    inventory_export = fields.Boolean(string='Inventory Export')
    export_action = fields.Selection(string='Export Action',
                                     selection=[('create_and_sync', 'Create and Sync'), ('sync_only', 'Sync Only')],
                                     default='create_and_sync')
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)

    def prepare_product_export_to_ecommerce(self):
        if hasattr(self,
                   '%s_prepare_product_export_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_prepare_product_export_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True
