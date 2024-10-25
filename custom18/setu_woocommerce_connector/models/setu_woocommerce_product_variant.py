from odoo import fields, models, api
from odoo.tools.misc import split_every
from datetime import datetime, timedelta
import requests


class SetuWooCommerceProductVariant(models.Model):
    _name = 'setu.woocommerce.product.variant'
    _description = 'WooCommerce Product Variant'

    active = fields.Boolean(string='Active', default=True)
    is_product_variant_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    is_woocommerce_manage_stock = fields.Boolean(string="Is Manage Stock?",
                                                 help="Enable stock management at product level in WooCommerce",
                                                 default=True)
    name = fields.Char(string="Variant Name", translate=True)
    woocommerce_product_variant_id = fields.Char(string="WooCommerce Variant ID",
                                                 help="Unique identifier for the resource.")
    default_code = fields.Char(string="Default Code")
    product_variant_created_at = fields.Datetime(string="Created At", help="The date the product was created")
    product_variant_modified_at = fields.Datetime(string="Last Modified At",
                                                  help="The date the product was last modified")
    product_url = fields.Text(string="Product URL")
    description = fields.Text(string="Description", translate=True)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False, required=True)
    setu_woocommerce_product_template_id = fields.Many2one("setu.woocommerce.product.template",
                                                           string="WooCommerce Template", required=True,
                                                           ondelete="cascade")
    odoo_product_id = fields.Many2one("product.product", string="Product Variant", required=True, ondelete="cascade")
    setu_woocommerce_product_image_ids = fields.One2many("setu.woocommerce.product.image",
                                                         "setu_woocommerce_product_variant_id",
                                                         string="Variant Image IDS")
    is_woocommerce_product_image_url = fields.Boolean(string="Is Woo Product Image URL?",
                                                      related="multi_ecommerce_connector_id.is_woocommerce_image_url")

    def fetch_and_create_product_stock_woocommerce_to_erp(self, multi_ecommerce_connector_id):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        stock_quant_obj = self.env['stock.quant']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        products_stock_lst = []
        quants = []
        try:
            woocommerce_product_variant_ids = self.search([('is_product_variant_exported_in_woocommerce', '=', True), (
                'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            sku = woocommerce_product_variant_ids.mapped('default_code')
            product_fields = 'id,name,sku,manage_stock,stock_quantity'

            for sku_chunk in split_every(100, sku):
                str_sku = ",".join(sku_chunk)
                stock_api_response = woo_api_connect.get("products", params={'sku': str_sku, '_fields': product_fields,
                                                                             'per_page': 100})

                if stock_api_response.status_code not in [200, 201]:
                    message = "Invalid Response Format, %s" % stock_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)

                stock_api_response_data = stock_api_response.json()
                for stock_api_response in stock_api_response_data:
                    stock_vals_add_dict = {}
                    woocommerce_product_variant_id = woocommerce_product_variant_ids.filtered(
                        lambda prod_id: prod_id.default_code == stock_api_response.get('sku'))

                    if woocommerce_product_variant_id:
                        if stock_api_response.get('manage_stock') and stock_api_response.get('stock_quantity'):
                            if woocommerce_product_variant_id.odoo_product_id.type == 'consu':
                                qty = stock_api_response.get('stock_quantity')
                                stock_vals_add_dict.update({'product_qty': qty})
                                stock_vals_add_dict.update(
                                    {'product_id': woocommerce_product_variant_id.odoo_product_id})
                                products_stock_lst.append(stock_vals_add_dict)
                    else:
                        message = "Product Not Found In ERP, %s" % (stock_api_response.get('sku'))
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)
        except Exception as e:
            message = "Requests to resources that don't exist or are missing import Product Stock to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)

        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()

        if products_stock_lst:
            quants = stock_quant_obj.create_ecommerce_stock_inventory(products_stock_lst,
                                                                      multi_ecommerce_connector_id.odoo_warehouse_id.lot_stock_id,
                                                                      multi_ecommerce_connector_id.is_auto_validate_inventory)
            if quants:
                browsed_quants = stock_quant_obj.browse(quants)
                browsed_quants.write({'is_ecommerce_inventory_adjustment': True,
                                      'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
        return quants

    # ===============================================================================
    # Export Product Stock From ERP To WooCommerce
    # ===============================================================================

    def fetch_and_export_product_stock_erp_to_woocommerce(self, multi_ecommerce_connector_id, export_stock_from_date):
        product_obj = self.env['product.product']
        if not export_stock_from_date:
            export_stock_from_date = datetime.now() - timedelta(30)

        product_ids = product_obj.product_stock_movement(export_stock_from_date,
                                                         multi_ecommerce_connector_id.odoo_company_id)

        woocommerce_product_template_ids = self.search([('odoo_product_id', 'in', product_ids), (
            'is_woocommerce_manage_stock', '=', True)]).setu_woocommerce_product_template_id.filtered(
            lambda x: x.multi_ecommerce_connector_id == multi_ecommerce_connector_id and x.is_product_template_exported_in_woocommerce == True)
        if woocommerce_product_template_ids:
            self.with_context(update_stock_inventory=product_ids).export_product_stock_to_woocommerce(
                multi_ecommerce_connector_id, woocommerce_product_template_ids)
        return True

    def export_product_stock_to_woocommerce(self, multi_ecommerce_connector_id, woocommerce_product_template_ids=False):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        product_product_obj = self.env['product.product']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)

        if multi_ecommerce_connector_id.is_manage_multiple_woocommerce_stock_export:
            warehouses = multi_ecommerce_connector_id.export_stock_woocommerce_warehouse_ids
        else:
            warehouses = multi_ecommerce_connector_id.odoo_warehouse_id

        if not warehouses:
            message = "No Warehouse found for Export Stock in WooCommerce: %s" % multi_ecommerce_connector_id.name
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if not woocommerce_product_template_ids:
            return False

        odoo_product_ids = woocommerce_product_template_ids.mapped('setu_woocommerce_product_variant_ids').mapped(
            'odoo_product_id').ids
        export_product_stock = product_product_obj.find_import_export_product_stock_field(multi_ecommerce_connector_id,
                                                                                          odoo_product_ids, warehouses)

        for woocommerce_product_template_id in woocommerce_product_template_ids.filtered(
                lambda x: x.product_tmpl_type == 'variable'):
            product_template_vals = {'id': woocommerce_product_template_id.woocommerce_product_tmpl_id,
                                     'variations': []}
            for woocommerce_product_variant_id in woocommerce_product_template_id.setu_woocommerce_product_variant_ids:
                if woocommerce_product_variant_id.woocommerce_product_variant_id and woocommerce_product_variant_id.odoo_product_id.type == 'consu' and woocommerce_product_variant_id.is_woocommerce_manage_stock:
                    if woocommerce_product_variant_id.odoo_product_id.id in self._context.get('update_stock_inventory'):
                        quantity = export_product_stock.get(woocommerce_product_variant_id.odoo_product_id.id, 0)
                        product_template_vals.get('variations').append(
                            {'id': woocommerce_product_variant_id.woocommerce_product_variant_id, 'manage_stock': True,
                             'stock_quantity': int(quantity)})

            if product_template_vals.get('variations'):
                variant_batches = self.export_product_stock_via_batch_module(product_template_vals.get('variations'))
                for woo_variants in variant_batches:
                    woo_export_stock_api_response = woo_api_connect.post(
                        'products/%s/variations/batch' % (product_template_vals.get('id')), {'update': woo_variants})

                    if woo_export_stock_api_response.status_code not in [200, 201]:
                        message = "Invalid Request Format, %s" % woo_export_stock_api_response.content
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)

        woo_product_template_ids = woocommerce_product_template_ids.filtered(lambda x: x.product_tmpl_type == 'simple')
        woo_product_template_batch_ids = self.export_product_stock_via_batch_module(woo_product_template_ids)
        for woo_product_template_batch_id in woo_product_template_batch_ids:
            batch_product_update_dict = {'update': []}
            batch_product_update_lst = []
            for woo_product_template_id in woo_product_template_batch_id:
                product_template_vals = {'id': woo_product_template_id.woocommerce_product_tmpl_id, 'variations': []}
                if woo_product_template_id.setu_woocommerce_product_variant_ids.is_woocommerce_manage_stock:
                    quantity = export_product_stock.get(
                        woo_product_template_id.setu_woocommerce_product_variant_ids[0].odoo_product_id.id, 0)
                    product_template_vals.update({'manage_stock': True, 'stock_quantity': int(quantity)})
                    batch_product_update_lst.append(product_template_vals)

            if batch_product_update_lst:
                batch_product_update_dict.update({'update': batch_product_update_lst})
                woo_export_stock_api_response = woo_api_connect.post('products/batch', batch_product_update_dict)

                if not isinstance(woo_export_stock_api_response, requests.models.Response):
                    message = "Invalid Response Format, %s" % woo_export_stock_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                if woo_export_stock_api_response.status_code not in [200, 201]:
                    message = "Invalid Request Format, %s" % woo_export_stock_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                try:
                    woo_export_stock_api_data = woo_export_stock_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing export Product Stock to WooCommerce for %s %s" % multi_ecommerce_connector_id.name, e
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)

                if woo_export_stock_api_data.get('data', {}) and woo_export_stock_api_data.get('data', {}).get(
                        'status') != 200:
                    message = woo_export_stock_api_data.get('message')
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)

        multi_ecommerce_connector_id.write({'woocommerce_last_update_product_stock': datetime.now()})

        return True

    def export_product_stock_via_batch_module(self, data):
        batches = []
        start, end = 0, 100
        if len(data) > 100:
            while True:
                data_batch = data[start:end]
                if not data_batch:
                    break
                temp = end + 100
                start, end = end, temp
                if data_batch:
                    batches.append(data_batch)
        else:
            batches.append(data)
        return batches
