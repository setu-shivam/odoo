# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class SetuEcommerceImportExportProcessWiz(models.TransientModel):
    _inherit = 'setu.ecommerce.import.export.process.wiz'

    ecommerce_operation_woo = fields.Selection(selection=[('import_attribute', 'Import Attributes'),
                                                          ('import_category', 'Import Categories'),
                                                          ('import_product_tags', 'Import Product Tags'),
                                                          ('import_product', 'Import Products'),
                                                          ("import_specific_product", "Import Specific Product-IDS"),
                                                          ('import_stock', 'Import Stock'),
                                                          ('import_customer', 'Import Customers'),
                                                          ('import_coupon', 'Import Coupons'),
                                                          ('import_orders', 'Import Orders'),
                                                          ("import_specific_order", "Import Specific Order-IDS"),
                                                          ('update_order_status', 'Update Order Status'),
                                                          ('export_tags', 'Sync Tags'),
                                                          ('export_stock', 'Export Stock'),
                                                          ('export_category', 'Sync Categories'),
                                                          ('export_coupon', 'Sync Coupons')],
                                               string="Operation")

    @api.onchange("multi_ecommerce_connector_id", "ecommerce_operation_woo")
    def woocommerce_connector_on_change_multi_ecommerce_connector_id(self):
        multi_ecommerce_connector_id = self.multi_ecommerce_connector_id
        self.is_hide_perform_operation_button = False
        if self.ecommerce_operation_woo == "import_product":
            self.orders_from_date = multi_ecommerce_connector_id.woocommerce_last_product_import or False

        if self.multi_ecommerce_connector_id.woocommerce_last_order_import_date:
            self.orders_from_date = multi_ecommerce_connector_id.woocommerce_last_order_import_date or False
        else:
            self.orders_from_date = fields.Datetime.now() - timedelta(days=1)
        self.export_stock_from = self.multi_ecommerce_connector_id.woocommerce_last_update_product_stock or datetime.now() - timedelta(
            30)
        self.orders_to_date = fields.Datetime.now()

    def woocommerce_connector_ecommerce_perform_operation(self):
        final_chain_lst = []
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']
        setu_woocommerce_customer_chain_obj = self.env['setu.ecommerce.customer.chain']
        setu_woocommerce_order_chain_obj = self.env['setu.ecommerce.order.chain']
        setu_woocommerce_coupons_obj = self.env['setu.woocommerce.coupons']
        setu_woocommerce_product_chain_obj = self.env['setu.ecommerce.product.chain']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        sale_order_obj = self.env['sale.order']

        multi_ecommerce_connector_id = self.multi_ecommerce_connector_id
        if self.ecommerce_operation_woo == "import_category":
            setu_woocommerce_product_category_obj.fetch_and_create_product_category_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_attribute":
            setu_woocommerce_product_attributes_obj.fetch_and_create_product_attributes_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_product_tags":
            setu_woocommerce_product_tags_obj.fetch_and_create_product_tags_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_product":
            product_chain_lst = setu_woocommerce_product_chain_obj.create_woocommerce_product_chain(
                multi_ecommerce_connector_id, self.is_skip_existing_product_update, self.orders_from_date,
                self.orders_to_date)

            if product_chain_lst:
                final_chain_lst = product_chain_lst
                action_name = "setu_woocommerce_connector.setu_woocommerce_ecommerce_product_chain_action"
                form_view_name = "setu_ecommerce_based.setu_ecommerce_product_chain_form_view"

        elif self.ecommerce_operation_woo == "import_customer":
            customer_chain_lst = setu_woocommerce_customer_chain_obj.process_via_import_customer_chain(
                multi_ecommerce_connector_id)

            if customer_chain_lst:
                final_chain_lst = customer_chain_lst
                action_name = "setu_woocommerce_connector.setu_woocommerce_ecommerce_customer_chain_action"
                form_view_name = "setu_ecommerce_based.setu_ecommerce_customer_chain_form_view"

        elif self.ecommerce_operation_woo == 'import_stock':
            setu_woocommerce_product_variant_obj.fetch_and_create_product_stock_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_coupon":
            setu_woocommerce_coupons_obj.fetch_and_create_coupons_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_orders":
            order_chain_lst = setu_woocommerce_order_chain_obj.process_to_import_all_woocommerce_order(
                multi_ecommerce_connector_id, self.orders_from_date, self.orders_to_date)

            if order_chain_lst:
                final_chain_lst = order_chain_lst
                action_name = "setu_woocommerce_connector.setu_woocommerce_ecommerce_order_chain_action"
                form_view_name = "setu_ecommerce_based.setu_ecommerce_order_chain_form_view"

        # ===============================================================================
        # Methods which Define below the WooCommerce To Odoo Data Management
        # ===============================================================================

        elif self.ecommerce_operation_woo == "export_stock":
            inventory_records = setu_woocommerce_product_variant_obj.fetch_and_export_product_stock_erp_to_woocommerce(
                multi_ecommerce_connector_id, self.export_stock_from)
            #
            # if inventory_records:
            #     final_chain_lst = inventory_records
            #     action_name = "stock.action_view_inventory_tree"
            #     form_view_name = "stock.view_stock_quant_tree_inventory_editable"

        elif self.ecommerce_operation_woo == "export_tags":
            self.fetch_and_export_or_update_product_tags_to_woocommerce()

        elif self.ecommerce_operation_woo == "export_category":
            self.fetch_and_export_or_update_category_to_woocommerce()

        elif self.ecommerce_operation_woo == "export_coupon":
            self.fetch_and_export_or_update_coupons_to_woocommerce()

        # ===============================================================================
        # Methods which Define below the WooCommerce To Odoo Data Management
        # ===============================================================================
        elif self.ecommerce_operation_woo == "update_order_status":
            sale_order_obj.update_sale_order_information_erp_to_woocommerce(multi_ecommerce_connector_id)

        elif self.ecommerce_operation_woo == "import_specific_product":
            parameter = {"per_page": 100, "page": 1, "order": "asc"}
            products_data = setu_woocommerce_product_chain_obj.create_woocommerce_product_chain_for_specific_products(
                parameter,
                self.import_specific_template_ids,
                multi_ecommerce_connector_id)
            if products_data:
                self.env['setu.ecommerce.product.chain'].process_for_create_woocommerce_product_chain(
                    products_data, multi_ecommerce_connector_id, True, False)
        elif self.ecommerce_operation_woo == "import_specific_order":
            parameter = {"per_page": 100, "page": 1, "order": "asc"}
            orders_data = sale_order_obj.process_to_import_specific_woocommerce_orders(parameter,
                                                                                       self.import_specific_order_ids,
                                                                                       multi_ecommerce_connector_id)
            if orders_data:
                self.env['setu.ecommerce.order.chain'].ecommerce_process_create_order_chain(
                    multi_ecommerce_connector_id,
                    orders_data, 'import_process')
        if final_chain_lst and action_name and form_view_name:
            action = self.env.ref(action_name).sudo().read()[0]
            form_view = self.sudo().env.ref(form_view_name)
            if len(final_chain_lst) == 1:
                action.update({"view_id": (form_view.id, form_view.name), "res_id": final_chain_lst[0],
                               "views": [(form_view.id, "form")]})
            else:
                action["domain"] = [("id", "in", final_chain_lst)]
            return action
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def woocommerce_connector_manual_export_product_to_ecommerce(self):
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_template_obj._name)
        active_woocommerce_product_template_ids = self._context.get('active_ids')
        multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search(
            [('state', '=', 'fully_integrated'), ('ecommerce_connector', '=', 'woocommerce_connector')])

        if not active_woocommerce_product_template_ids:
            raise ValidationError(_("Please select some products to Export to WooCommerce."))

        if active_woocommerce_product_template_ids and len(active_woocommerce_product_template_ids) > 80:
            raise ValidationError(_("For better performance please select only 80 records to export."))

        pending_export_woocommerce_template_ids = setu_woocommerce_product_template_obj.search(
            [('id', 'in', active_woocommerce_product_template_ids),
             ('is_product_template_exported_in_woocommerce', '=', False)])

        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            pending_export_product_template_ids = pending_export_woocommerce_template_ids.filtered(
                lambda x: x.multi_ecommerce_connector_id.id == multi_ecommerce_connector_id.id)
            template_lst = self.checked_woocommerce_variant_with_code(pending_export_product_template_ids)
            process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                             self.multi_ecommerce_connector_id,
                                                                                             model_id)
            setu_woocommerce_product_template_obj.export_product_in_woocommerce(
                multi_ecommerce_connector_id=multi_ecommerce_connector_id,
                woocommerce_product_template_ids=template_lst,
                is_set_basic_detail=self.ecommerce_is_set_basic_detail,
                is_set_price=self.ecommerce_is_set_price,
                is_set_images=self.ecommerce_is_set_image,
                is_publish=self.woocommerce_product_published_defined,
                process_history_id=process_history_id)

            if not process_history_id.process_history_line_ids:
                process_history_id.sudo().unlink()
        return True

    def checked_woocommerce_variant_with_code(self, pending_export_product_template_ids):
        template_lst = []
        for pending_export_product_template_id in pending_export_product_template_ids:
            if not self.env['setu.woocommerce.product.variant'].search(
                    [('setu_woocommerce_product_template_id', '=', pending_export_product_template_id.id),
                     ('default_code', '=', False)]):
                template_lst.append(pending_export_product_template_id)
        return template_lst

    # ===========================================================================
    # Manual Update Product ERP To WooCommerce
    # ===========================================================================

    def woocommerce_connector_manual_update_product_to_ecommerce(self):
        if not self.ecommerce_is_set_basic_detail and not self.ecommerce_is_set_price and not self.ecommerce_is_set_image and not self.ecommerce_product_published_defined:
            raise ValidationError(_('Please Select any one Option for process Update Products'))

        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_template_obj._name)

        process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                         self.multi_ecommerce_connector_id,
                                                                                         model_id)
        active_woocommerce_product_template_ids = self._context.get('active_ids')
        if self._context.get('process') == 'update_products':
            if active_woocommerce_product_template_ids and len(active_woocommerce_product_template_ids) > 80:
                raise ValidationError(_("For better performance please select only 80 records to export."))

        multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search([('active', '=', True),
                                                                                   ('state', '=',
                                                                                    'fully_integrated'),
                                                                                   ('ecommerce_connector', '=',
                                                                                    'woocommerce_connector')])

        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            if active_woocommerce_product_template_ids:
                woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search([(
                    'multi_ecommerce_connector_id',
                    '=',
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                    ('id', 'in',
                     active_woocommerce_product_template_ids),
                    (
                        'is_product_template_exported_in_woocommerce',
                        '=', True)])
                setu_woocommerce_product_template_obj.update_product_in_woocommerce(
                    multi_ecommerce_connector_id=multi_ecommerce_connector_id,
                    template_ids=woocommerce_product_template_ids,
                    is_update_basic_detail=self.ecommerce_is_update_basic_detail,
                    is_update_price=self.ecommerce_is_update_price,
                    is_update_image=self.ecommerce_is_set_image,
                    is_update_publish="publish",
                    process_history_id=process_history_id)
                if not process_history_id.process_history_line_ids:
                    process_history_id.sudo().unlink()
        return True

    # ===========================================================================
    # Cron Order Status Update ERP To WooCommerce
    # ===========================================================================

    def woocommerce_connector_update_order_status_to_ecommerce(self, multi_ecommerce_connector_id):
        sale_order_obj = self.env['sale.order']
        sale_order_obj.update_sale_order_information_erp_to_woocommerce(multi_ecommerce_connector_id)
        return True

    def woocommerce_connector_action_generic_export_update_process_ecommerce(self):
        operation_type = self._context.get("operation", "")

        if operation_type == "wiz_category_export":
            self.fetch_and_export_or_update_category_to_woocommerce()

        elif operation_type == "wiz_tags_export":
            self.fetch_and_export_or_update_product_tags_to_woocommerce()

        elif operation_type == "wiz_coupons_export":
            self.fetch_and_export_or_update_coupons_to_woocommerce()

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def fetch_and_export_or_update_category_to_woocommerce(self):
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_category_obj._name)

        active_woocommerce_product_category_ids = self._context.get('active_ids')
        if active_woocommerce_product_category_ids and self._context.get('operation') == 'wiz_category_export':
            multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search(
                [('active', '=', True), ('state', '=', 'fully_integrated'),
                 ('ecommerce_connector', '=', 'woocommerce_connector')])
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                setu_woocommerce_product_category_ids = setu_woocommerce_product_category_obj.search([(
                    'multi_ecommerce_connector_id', '=',
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                    ('is_product_category_exported_in_woocommerce', '=', False),
                    ('id', 'in', active_woocommerce_product_category_ids)])
                if setu_woocommerce_product_category_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                                     multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_product_category_obj.export_product_category_in_woocommerce(
                        multi_ecommerce_connector_id, setu_woocommerce_product_category_ids, process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
            update_records = setu_woocommerce_product_category_obj.browse(active_woocommerce_product_category_ids)
            need_to_update_records = update_records.filtered(lambda x: x.need_to_update == True)
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                pending_update_product_category_ids = setu_woocommerce_product_category_obj.search(
                    [('woocommerce_category_id', '!=', False),
                     ('multi_ecommerce_connector_id', '=',
                      multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                     ('is_product_category_exported_in_woocommerce', '=', True),
                     ('id', 'in', need_to_update_records.ids)])
                if pending_update_product_category_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                     multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_product_category_obj.update_product_category_in_woocommerce(
                        multi_ecommerce_connector_id, pending_update_product_category_ids, process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
        else:
            pending_update_woocommerce_coupons_ids = setu_woocommerce_product_category_obj.search(
                [('woocommerce_category_id', '!=', False),
                 ('multi_ecommerce_connector_id', '=', self.multi_ecommerce_connector_id.id),
                 ('is_product_category_exported_in_woocommerce', '=', True)])
            if pending_update_woocommerce_coupons_ids:
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                 self.multi_ecommerce_connector_id,
                                                                                                 model_id)
                setu_woocommerce_product_category_obj.update_product_category_in_woocommerce(
                    self.multi_ecommerce_connector_id,
                    pending_update_woocommerce_coupons_ids,
                    process_history_id)
                if not process_history_id.process_history_line_ids:
                    process_history_id.sudo().unlink()
            return True

    def fetch_and_export_or_update_product_tags_to_woocommerce(self):
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_tags_obj._name)

        active_woocommerce_product_tag_ids = self._context.get('active_ids')
        if active_woocommerce_product_tag_ids and self._context.get("operation", "") == "wiz_tags_export":
            multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search(
                [('active', '=', True), ('state', '=', 'fully_integrated'),
                 ('ecommerce_connector', '=', 'woocommerce_connector')])
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                pending_export_woocommerce_ids = setu_woocommerce_product_tags_obj.search(
                    [("id", "in", active_woocommerce_product_tag_ids),
                     ("is_product_tags_exported_in_woocommerce", "=", False),
                     ("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id)])
                if pending_export_woocommerce_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                                     self.multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_product_tags_obj.process_to_export_product_tags_erp_to_woocommerce(
                        multi_ecommerce_connector_id, pending_export_woocommerce_ids, process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
            browseable_records = setu_woocommerce_product_tags_obj.browse(active_woocommerce_product_tag_ids)
            to_be_update_records = browseable_records.filtered(lambda x: x.need_to_update == True)
            multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search(
                [('active', '=', True), ('state', '=', 'fully_integrated')])
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                pending_update_woocommerce_tag_ids = setu_woocommerce_product_tags_obj.search(
                    [("id", "in", to_be_update_records.ids),
                     ("is_product_tags_exported_in_woocommerce", "=", True),
                     ("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id)])
                if pending_update_woocommerce_tag_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                     multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_product_tags_obj.process_to_update_product_tags_erp_to_woocommerce(
                        multi_ecommerce_connector_id, pending_update_woocommerce_tag_ids, process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
        else:
            pending_update_woocommerce_tag_ids = setu_woocommerce_product_tags_obj.search(
                [('multi_ecommerce_connector_id', '=', self.multi_ecommerce_connector_id.id),
                 ('is_product_tags_exported_in_woocommerce', '=', True)])
            if pending_update_woocommerce_tag_ids:
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                 self.multi_ecommerce_connector_id,
                                                                                                 model_id)
                setu_woocommerce_product_tags_obj.process_to_update_product_tags_erp_to_woocommerce(
                    self.multi_ecommerce_connector_id,
                    pending_update_woocommerce_tag_ids,
                    process_history_id)
                if not process_history_id.process_history_line_ids:
                    process_history_id.sudo().unlink()
            return True

    def fetch_and_export_or_update_coupons_to_woocommerce(self):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_woocommerce_coupons_obj = self.env['setu.woocommerce.coupons']
        setu_multi_ecommerce_connector_obj = self.env['setu.multi.ecommerce.connector']
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_coupons_obj._name)

        active_woocommerce_coupons_ids = self._context.get('active_ids')
        if active_woocommerce_coupons_ids and self._context.get('operation', '') == 'wiz_coupons_export':
            multi_ecommerce_connector_ids = setu_multi_ecommerce_connector_obj.search(
                [('active', '=', True), ('state', '=', 'fully_integrated'),
                 ('ecommerce_connector', '=', 'woocommerce_connector')])
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                setu_woocommerce_coupons_ids = setu_woocommerce_coupons_obj.search([(
                    'multi_ecommerce_connector_id', '=',
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                    ('is_coupon_exported_in_woocommerce',
                     '=', False), ('id', 'in',
                                   active_woocommerce_coupons_ids)])
                if setu_woocommerce_coupons_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                                     multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_coupons_obj.export_erp_woocommerce_coupons(multi_ecommerce_connector_id,
                                                                                setu_woocommerce_coupons_ids,
                                                                                process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
            browseable_records = setu_woocommerce_coupons_obj.browse(active_woocommerce_coupons_ids)
            to_be_update_records = browseable_records.filtered(lambda x: x.need_to_update == True)
            for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
                pending_update_woocommerce_coupons_ids = setu_woocommerce_coupons_obj.search(
                    [('id', 'in', to_be_update_records.ids), ('woocommerce_coupon_id', '!=', False),
                     ('is_coupon_exported_in_woocommerce', '=', True),
                     ('multi_ecommerce_connector_id', '=',
                      multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
                if pending_update_woocommerce_coupons_ids:
                    process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                     multi_ecommerce_connector_id,
                                                                                                     model_id)
                    setu_woocommerce_coupons_obj.update_erp_woocommerce_coupons(multi_ecommerce_connector_id,
                                                                                pending_update_woocommerce_coupons_ids,
                                                                                process_history_id)
                    if not process_history_id.process_history_line_ids:
                        process_history_id.sudo().unlink()
        else:
            pending_update_woocommerce_coupons_ids = setu_woocommerce_coupons_obj.search(
                [('woocommerce_coupon_id', '!=', False),
                 ('multi_ecommerce_connector_id', '=', self.multi_ecommerce_connector_id.id),
                 ('is_coupon_exported_in_woocommerce', '=', True)])
            if pending_update_woocommerce_coupons_ids:
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                 self.multi_ecommerce_connector_id,
                                                                                                 model_id)
                setu_woocommerce_coupons_obj.update_erp_woocommerce_coupons(self.multi_ecommerce_connector_id,
                                                                            pending_update_woocommerce_coupons_ids,
                                                                            process_history_id)
                if not process_history_id.process_history_line_ids:
                    process_history_id.sudo().unlink()

    # ===============================================================================
    # Auto Export Product Stock From ERP To WooCommerce
    # ===============================================================================

    def woocommerce_connector_update_stock_to_ecommerce(self, multi_ecommerce_connector_id):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_variant_obj.fetch_and_export_product_stock_erp_to_woocommerce(
            multi_ecommerce_connector_id, multi_ecommerce_connector_id.woocommerce_last_update_product_stock)

        return True
