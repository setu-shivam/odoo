# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SetuEcommerceImportExportProcessWiz(models.TransientModel):
    _name = 'setu.ecommerce.import.export.process.wiz'
    _description = 'ecommerce Import Export Process'

    is_skip_existing_product_update = fields.Boolean(string="Do you want to Update Existing Product ?")
    ecommerce_is_set_basic_detail = fields.Boolean(string="Set Basic Detail ?", default=True)
    ecommerce_is_set_price = fields.Boolean(string="Set Price ?", default=False)
    ecommerce_is_set_image = fields.Boolean(string="Set Image ?", default=False)
    ecommerce_is_set_stock = fields.Boolean(string="Set Stock ?", default=False)

    is_hide_perform_operation_button = fields.Boolean(default=False, store=False)

    ecommerce_is_update_basic_detail = fields.Boolean(string="Update Basic Details ?", default=False)
    ecommerce_is_update_price = fields.Boolean(string="Update Price ?", default=False)
    ecommerce_is_update_set_image = fields.Boolean(string="Update Image?", default=False)

    orders_from_date = fields.Datetime(string="From Date")
    orders_to_date = fields.Datetime(string="To Date")
    export_stock_from = fields.Datetime(string="Export Stock After")

    import_specific_order_ids = fields.Text(string="Specific Order IDS", translate=True)
    import_specific_template_ids = fields.Text(string="Specific Product IDS", translate=True)

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)

    @api.constrains('orders_from_date', 'orders_to_date')
    def _check_date_validation(self):
        if self.orders_from_date:
            if self.orders_from_date.date() > fields.Date.today():
                raise ValidationError(_("The 'From Date' field cannot be set to a date that is "
                                        "earlier than the current date. "))
        if self.orders_from_date and self.orders_to_date and self.orders_to_date <= self.orders_from_date:
            raise ValidationError(_("Selected date is not correctly set. To date must be greater than the From date."))

    @api.onchange('multi_ecommerce_connector_id')
    def _on_change_multi_ecommerce_connector_id(self):
        if hasattr(self,
                   '%s_on_change_multi_ecommerce_connector_id' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_on_change_multi_ecommerce_connector_id' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        if not self.multi_ecommerce_connector_id:
            self.orders_from_date = False

    def ecommerce_perform_operation(self):
        if hasattr(self, '%s_ecommerce_perform_operation' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_ecommerce_perform_operation' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def manual_export_product_to_ecommerce(self):
        if hasattr(self,
                   '%s_manual_export_product_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_manual_export_product_to_ecommerce' % self.multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def manual_update_product_to_ecommerce(self):
        multi_ecommerce_connector_id = False
        if self._context.get('active_id'):
            multi_ecommerce_connector_id = self.env[self._context.get('active_model')].browse(
                self._context.get('active_id')).multi_ecommerce_connector_id
            if len(multi_ecommerce_connector_id.ids) > 1:
                raise ValidationError(
                    _("Currently found the Multiple e-Commerce to Update Product. Please select only one Multiple e-Commerce to Update"))
        if not multi_ecommerce_connector_id:
            multi_ecommerce_connector_id = self.multi_ecommerce_connector_id
        if hasattr(self, '%s_manual_update_product_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_manual_update_product_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def cron_auto_update_order_status_in_ecommerce(self, ctx):
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        ecommerce_connector_id = ctx.get('multi_ecommerce_connector_id')
        multi_ecommerce_connector_id = setu_multi_ecommerce_connector_obj.browse(ecommerce_connector_id)
        if hasattr(self, '%s_update_order_status_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_update_order_status_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector)(
                multi_ecommerce_connector_id)
        return True

    def action_generic_export_update_process(self):
        multi_ecommerce_connector_id = self.env[self._context.get('active_model')].browse(
            self._context.get('active_id')).multi_ecommerce_connector_id
        if hasattr(self,
                   '%s_action_generic_export_update_process_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self,
                    '%s_action_generic_export_update_process_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector)()
        return True

    def cron_auto_update_stock_in_ecommerce(self, ctx):
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        ecommerce_connector_id = ctx.get('multi_ecommerce_connector_id')
        multi_ecommerce_connector_id = setu_multi_ecommerce_connector_obj.browse(ecommerce_connector_id)
        if hasattr(self, '%s_update_stock_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector):
            getattr(self, '%s_update_stock_to_ecommerce' % multi_ecommerce_connector_id.ecommerce_connector)(
                multi_ecommerce_connector_id)
        return True
