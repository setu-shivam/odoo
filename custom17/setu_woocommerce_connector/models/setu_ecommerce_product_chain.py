from odoo import fields, models, api
import json
from datetime import datetime


class SetuEcommerceProductChain(models.Model):
    _inherit = 'setu.ecommerce.product.chain'

    def create_woocommerce_product_chain(self, multi_ecommerce_connector_id, is_skip_existing_product_update,
                                         after_date, before_date):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']

        ecommerce_product_chain_id = False
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)

        setu_woocommerce_product_category_obj.fetch_and_create_product_category_woocommerce_to_erp(
            multi_ecommerce_connector_id)
        setu_woocommerce_product_attributes_obj.fetch_and_create_product_attributes_woocommerce_to_erp(
            multi_ecommerce_connector_id)
        setu_woocommerce_product_tags_obj.fetch_and_create_product_tags_woocommerce_to_erp(multi_ecommerce_connector_id)

        setu_woocommerce_product_template_ids = setu_woocommerce_product_template_obj.import_and_sync_woocommerce_product_template_erp(
            multi_ecommerce_connector_id, process_history_id, after_date=after_date, before_date=before_date)

        if setu_woocommerce_product_template_ids:
            ecommerce_product_chain_id = self.process_for_create_woocommerce_product_chain(
                setu_woocommerce_product_template_ids, multi_ecommerce_connector_id, is_skip_existing_product_update,
                record_created_from='import_process')

        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()
        multi_ecommerce_connector_id.woocommerce_last_product_import = datetime.now()
        return ecommerce_product_chain_id

    def process_for_create_woocommerce_product_chain(self, setu_woocommerce_product_template_ids,
                                                     multi_ecommerce_connector_id, is_skip_existing_product_update,
                                                     record_created_from):

        setu_woocommerce_product_chain_obj = self.env['setu.ecommerce.product.chain']
        setu_woocommerce_product_chain_line_obj = self.env['setu.ecommerce.product.chain.line']

        ecommerce_product_chain_id = self.ecommerce_process_create_product_chain(multi_ecommerce_connector_id,
                                                                                 record_created_from,
                                                                                 is_skip_existing_product_update)
        chain_lst = [ecommerce_product_chain_id.id]
        ecommerce_product_chain_vals = self.ecommerce_process_create_product_chain_line_vals(
            multi_ecommerce_connector_id, ecommerce_product_chain_id)

        for setu_woocommerce_product_template_id in setu_woocommerce_product_template_ids:
            ecommerce_product_chain_vals.update(
                {'product_chain_line_data': json.dumps(setu_woocommerce_product_template_id),
                 'ecommerce_product_id': setu_woocommerce_product_template_id.get('id'),
                 'last_product_chain_update_date': setu_woocommerce_product_template_id.get(
                     'date_modified'),
                 'name': setu_woocommerce_product_template_id.get('name')})

            setu_woocommerce_product_chain_line_obj.create(ecommerce_product_chain_vals)
            if len(ecommerce_product_chain_id.setu_ecommerce_product_chain_line_ids) == 100:
                ecommerce_product_chain_id = self.ecommerce_process_create_product_chain(multi_ecommerce_connector_id,
                                                                                         record_created_from,
                                                                                         is_skip_existing_product_update)
                chain_lst.append(ecommerce_product_chain_id.id)
                ecommerce_product_chain_vals = self.ecommerce_process_create_product_chain_line_vals(
                    multi_ecommerce_connector_id, ecommerce_product_chain_id)
                continue

        for ecommerce_product_chain_id in chain_lst:
            browse_chain_id = setu_woocommerce_product_chain_obj.browse(ecommerce_product_chain_id)
            if not browse_chain_id.setu_ecommerce_product_chain_line_ids:
                browse_chain_id.sudo().unlink()
        return chain_lst

    def create_or_update_product_via_webhook(self, request_json, multi_ecommerce_connector_id, woo_api_connect):

        if request_json.get("type") == "variable":
            params = {"per_page": 100}
            response = woo_api_connect.get("products/%s/variations" % (request_json.get("id")), params=params)
            variants_data = response.json()
            total_pages = response.headers.get("X-WP-TotalPages")
            if int(total_pages) > 1:
                for page in range(2, int(total_pages) + 1):
                    params["page"] = page
                    response = woo_api_connect.get("products/%s/variations" % (request_json.get("id")), params=params)
                    variants_data += response.json()
            if isinstance(variants_data, list):
                request_json.update({"variations": variants_data})
        product_chain_id = self.sudo().process_for_create_woocommerce_product_chain([request_json],
                                                                                    multi_ecommerce_connector_id, False,
                                                                                    "webhook")
        product_chain = self.env['setu.ecommerce.product.chain'].browse(product_chain_id)
        product_chain.setu_ecommerce_product_chain_line_ids.ecommerce_process_product_chain_line()

    def create_woocommerce_product_chain_for_specific_products(self, parameter, import_specific_template_ids,
                                                               multi_ecommerce_connector_id):
        setu_process_history_obj = self.env['setu.process.history']
        setu_process_history_line_obj = self.env['setu.process.history.line']

        products_list = []
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        products = import_specific_template_ids.split(',')
        for product in products:
            woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
            try:
                order_api_response = woo_api_connect.get("products/%s" % product)
            except Exception as e:
                message = "Requested resource doesn't exist or missing requested information on " \
                          "WooCommerce store. %s %s" % (multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            if order_api_response.status_code not in [200, 201]:
                message = "Invalid Request Format %s" % (order_api_response.json().get('message'))
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            order_data_json_lsts = order_api_response.json()
            products_list.append(order_data_json_lsts)
            total_pages = int(len(products) / 10)

            if int(total_pages) > 1:
                page_data = []
                for page in range(2, int(total_pages) + 1):
                    parameter["page"] = page
                    response = woo_api_connect.get("orders", params=parameter)
                    page_data = response.json()
                products_list += page_data
        return products_list
