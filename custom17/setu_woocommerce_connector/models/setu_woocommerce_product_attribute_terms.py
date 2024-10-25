from odoo import fields, models, api
import requests


class SetuWooCommerceProductAttributeTerms(models.Model):
    _name = 'setu.woocommerce.product.attribute.terms'
    _description = 'WooCommerce Product Attribute Terms'

    is_product_attribute_terms_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    name = fields.Char(string='Name', translate=True, help="Term name")
    woocommerce_attribute_term_id = fields.Char(string="WooCommerce Attribute Term ID",
                                                help="Unique identifier for the resource.")
    description = fields.Char(string='Description', help="HTML description of the resource.", translate=True)
    slug = fields.Char(string='Slug', help="An alphanumeric identifier for the resource unique to its type.",
                       translate=True)
    count = fields.Integer(string="Count", help="Number of published products for the resource.")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', required=True)
    setu_woocommerce_product_attributes_id = fields.Many2one('setu.woocommerce.product.attributes',
                                                             string='WooCommerce Attributes', copy=False)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, copy=False)
    attribute_value_id = fields.Many2one('product.attribute.value', string='Attribute Value', required=True, copy=False)

    def create_and_sync_product_attribute_terms(self, multi_ecommerce_connector_id, process_history_id):
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        odoo_attribute_value_obj = self.env['product.attribute.value']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()

        woocommerce_product_attributes_ids = setu_woocommerce_product_attributes_obj.search(
            [('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])

        for woocommerce_product_attributes_id in woocommerce_product_attributes_ids:
            attribute_terms_api_response = woo_api_connect.get(
                "products/attributes/%s/terms" % woocommerce_product_attributes_id.woocommerce_attribute_id,
                params={'per_page': 100})
            try:
                attributes_term_data_lst = attribute_terms_api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing import attribute terms to " \
                          "WooCommerce for %s %s" % (multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            if not isinstance(attributes_term_data_lst, list):
                message = "Invalid Response Format %s" % attributes_term_data_lst
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue

            total_pages = attribute_terms_api_response and attribute_terms_api_response.headers.get(
                'x-wp-totalpages') or 1

            if int(total_pages) >= 2:
                for list_of_page in range(2, int(total_pages) + 1):
                    attributes_term_data_lst += self.process_import_all_attribute_terms(woo_api_connect,
                                                                                        multi_ecommerce_connector_id,
                                                                                        list_of_page,
                                                                                        process_history_id,
                                                                                        woocommerce_product_attributes_id)
            if attribute_terms_api_response.status_code in [201, 200]:
                for attribute_term_data_dict in attributes_term_data_lst:
                    existing_attribute_term_id = self.search(
                        [('woocommerce_attribute_term_id', '=', attribute_term_data_dict.get('id')), (
                            'setu_woocommerce_product_attributes_id', '=',
                            multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                         ('is_product_attribute_terms_exported_in_woocommerce', '=', True)], limit=1)
                    if existing_attribute_term_id:
                        continue

                    odoo_attribute_value_id = odoo_attribute_value_obj.search(
                        [('name', '=ilike', attribute_term_data_dict.get('name')),
                         ('attribute_id', '=', woocommerce_product_attributes_id.attribute_id.id)], limit=1)
                    if not odoo_attribute_value_id:
                        odoo_attribute_value_id = odoo_attribute_value_obj.with_context(active_id=False).create(
                            {'name': attribute_term_data_dict.get('name'),
                             'attribute_id': woocommerce_product_attributes_id.attribute_id.id})

                    existing_attribute_term_id = self.search(
                        [('attribute_value_id', '=', odoo_attribute_value_id.id),
                         ('attribute_id', '=', woocommerce_product_attributes_id.attribute_id.id),
                         ('setu_woocommerce_product_attributes_id', '=', woocommerce_product_attributes_id.id),
                         ('multi_ecommerce_connector_id', '=',
                          multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                         ('is_product_attribute_terms_exported_in_woocommerce', '=', False)], limit=1)

                    if existing_attribute_term_id:
                        existing_attribute_term_id.write(
                            {'woocommerce_attribute_term_id': attribute_term_data_dict.get('id'),
                             'count': attribute_term_data_dict.get('count'),
                             'slug': attribute_term_data_dict.get('slug'),
                             'is_product_attribute_terms_exported_in_woocommerce': True})
                    else:
                        self.create(
                            {'name': attribute_term_data_dict.get('name'),
                             'woocommerce_attribute_term_id': attribute_term_data_dict.get('id'),
                             'slug': attribute_term_data_dict.get('slug'),
                             'count': attribute_term_data_dict.get('count'),
                             'is_product_attribute_terms_exported_in_woocommerce': True,
                             'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                             'attribute_value_id': odoo_attribute_value_id.id,
                             'setu_woocommerce_product_attributes_id': woocommerce_product_attributes_id and woocommerce_product_attributes_id.id,
                             'attribute_id': woocommerce_product_attributes_id.attribute_id.id})
            else:
                message = "Invalid Request Format %s" % attribute_terms_api_response.content
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
        return True

    def process_import_all_attribute_terms(self, woo_api_connect, multi_ecommerce_connector_id, list_of_page,
                                           process_history_id, woocommerce_product_attributes_id):
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_attribute_terms_api_response = woo_api_connect.get(
            "products/attributes/%s/terms" % woocommerce_product_attributes_id.woocommerce_attribute_id,
            params={'per_page': 100, 'page': list_of_page})

        if not isinstance(woo_attribute_terms_api_response, requests.models.Response):
            message = "Invalid Response Format, %s" % woo_attribute_terms_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return []
        if woo_attribute_terms_api_response.status_code not in [200, 201]:
            message = "Invalid Request Format, %s" % woo_attribute_terms_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return []
        try:
            woo_attribute_terms_api_response_data = woo_attribute_terms_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing import attribute terms to" \
                      " WooCommerce for %s %s" % (multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return []
        return woo_attribute_terms_api_response_data
