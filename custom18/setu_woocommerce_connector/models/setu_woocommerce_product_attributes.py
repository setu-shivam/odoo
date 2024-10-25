from odoo import fields, models, api
import requests


class SetuWooCommerceProductAttributes(models.Model):
    _name = 'setu.woocommerce.product.attributes'
    _description = 'WooCommerce Product Attributes'

    is_product_attributes_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    active = fields.Boolean(string="active", default=True)
    is_attributes_enable_disable = fields.Boolean(string="Enable archives?", help="Enable/Disable attribute archives")

    woocommerce_attribute_id = fields.Char(string="Woo Attribute ID", help="Unique identifier for the resource.")
    name = fields.Char(string='Name', required=True, translate=True, help="Attribute name")
    slug = fields.Char(string='Slug', help="An alphanumeric identifier for the resource unique to its type",
                       translate=True)

    order_by = fields.Selection(
        [('menu_order', 'Custom Ordering'), ('name', 'Name'), ('name_num', 'Name(numeric)'), ('id', 'Term ID')],
        default="menu_order", string='Default sort order')
    attribute_type = fields.Selection([('select', 'Select')], string='Attribute Type', default='select')

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', required=True)
    attribute_id = fields.Many2one('product.attribute', string='Attribute', required=True, copy=False)

    def fetch_and_create_product_attributes_woocommerce_to_erp(self, multi_ecommerce_connector_id):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        self.process_for_import_product_attributes_woocommerce_to_erp(multi_ecommerce_connector_id, process_history_id)

        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()
        return True

    def process_for_import_product_attributes_woocommerce_to_erp(self, multi_ecommerce_connector_id,
                                                                 process_history_id):
        setu_woocommerce_product_attribute_terms_obj = self.env['setu.woocommerce.product.attribute.terms']
        odoo_product_attribute_obj = self.env['product.attribute']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env["setu.process.history.line"]

        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        woo_product_attributes_api_response = woo_api_connect.get("products/attributes", params={'per_page': 100})
        try:
            woo_product_attributes_api_response_data = woo_product_attributes_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing import attributes to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if not isinstance(woo_product_attributes_api_response_data, list):
            message = "Invalid Response Format, %s" % woo_product_attributes_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True

        total_pages = woo_product_attributes_api_response and woo_product_attributes_api_response.headers.get(
            'x-wp-totalpages') or 1
        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                woo_product_attributes_api_response_data += multi_ecommerce_connector_id.process_import_all_records(
                    woo_api_connect,
                    multi_ecommerce_connector_id,
                    list_of_page,
                    process_history_id,
                    model_id,
                    method='products/attributes')

        if woo_product_attributes_api_response.status_code in [201, 200]:
            for woo_product_attributes_api_response_dict in woo_product_attributes_api_response_data:
                existing_woocommerce_product_attribute_id = self.search(
                    [('woocommerce_attribute_id', '=', woo_product_attributes_api_response_dict.get('id')), (
                        'multi_ecommerce_connector_id', '=',
                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                     ('is_product_attributes_exported_in_woocommerce', '=', True)], limit=1)
                if existing_woocommerce_product_attribute_id:
                    continue

                odoo_product_attribute_id = odoo_product_attribute_obj.search(
                    [('name', '=ilike', woo_product_attributes_api_response_dict.get('name'))], limit=1)
                if not odoo_product_attribute_id:
                    odoo_product_attribute_id = odoo_product_attribute_obj.create(
                        {'name': woo_product_attributes_api_response_dict.get('name')})

                existing_woocommerce_product_attribute_id = self.search(
                    [('attribute_id', '=', odoo_product_attribute_id and odoo_product_attribute_id.id), (
                        'multi_ecommerce_connector_id', '=',
                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                     ('is_product_attributes_exported_in_woocommerce', '=', False)], limit=1)

                if existing_woocommerce_product_attribute_id:
                    existing_woocommerce_product_attribute_id.write(
                        {'woocommerce_attribute_id': woo_product_attributes_api_response_dict.get('id'),
                         'order_by': woo_product_attributes_api_response_dict.get('order_by'),
                         'slug': woo_product_attributes_api_response_dict.get('slug'), 'exported_in_woo': True,
                         'is_attributes_enable_disable': woo_product_attributes_api_response_dict.get('has_archives')})

                else:
                    self.create({'name': woo_product_attributes_api_response_dict.get('name'),
                                 'woocommerce_attribute_id': woo_product_attributes_api_response_dict.get('id'),
                                 'order_by': woo_product_attributes_api_response_dict.get('order_by'),
                                 'slug': woo_product_attributes_api_response_dict.get('slug'),
                                 'is_attributes_enable_disable': woo_product_attributes_api_response_dict.get(
                                     'has_archives'),
                                 'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                                 'attribute_id': odoo_product_attribute_id and odoo_product_attribute_id.id,
                                 'is_product_attributes_exported_in_woocommerce': True})

        else:
            message = "Invalid Response Format, %s" % woo_product_attributes_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True

        self._cr.commit()
        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_attribute_terms_obj._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         self.multi_ecommerce_connector_id,
                                                                                         model_id)
        setu_woocommerce_product_attribute_terms_obj.create_and_sync_product_attribute_terms(
            multi_ecommerce_connector_id, process_history_id)
        return True

    def process_via_product_attributes_export_and_update(self, odoo_attribute_id, multi_ecommerce_connector_id,
                                                         process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()

        woocommerce_product_attributes_id = self.search(
            [('attribute_id', '=', odoo_attribute_id and odoo_attribute_id.id),
             ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
             ('is_product_attributes_exported_in_woocommerce', '=', True)], limit=1)

        if woocommerce_product_attributes_id and woocommerce_product_attributes_id.woocommerce_attribute_id:
            return {odoo_attribute_id.id: woocommerce_product_attributes_id.woocommerce_attribute_id}
        attribute_data = {'name': odoo_attribute_id.name, 'type': 'select'}

        attributes_api_response = woo_api_connect.post("products/attributes", attribute_data)
        if not isinstance(attributes_api_response, requests.models.Response):
            message = "Invalid Response format %s" % attributes_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if attributes_api_response.status_code == 400:
            self.process_for_import_product_attributes_woocommerce_to_erp(multi_ecommerce_connector_id,
                                                                          process_history_id)
            woocommerce_product_attributes_id = self.search(
                [('attribute_id', '=', odoo_attribute_id and odoo_attribute_id.id), (
                    'multi_ecommerce_connector_id', '=',
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                 ('is_product_attributes_exported_in_woocommerce', '=', True)], limit=1)
            if woocommerce_product_attributes_id and woocommerce_product_attributes_id.woocommerce_attribute_id:
                return {odoo_attribute_id.id: woocommerce_product_attributes_id.woocommerce_attribute_id}

        if attributes_api_response.status_code not in [200, 201]:
            message = "Invalid Request Format %s" % attributes_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        attribute_api_response_json = attributes_api_response.json()
        self.create({'name': odoo_attribute_id and odoo_attribute_id.name or attribute_api_response_json.get('name'),
                     'woocommerce_attribute_id': attribute_api_response_json.get('id'),
                     'order_by': attribute_api_response_json.get('order_by'),
                     'slug': attribute_api_response_json.get('slug'),
                     'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                     'attribute_id': odoo_attribute_id.id,
                     'is_product_attributes_exported_in_woocommerce': True,
                     'is_attributes_enable_disable': attribute_api_response_json.get('has_archives')})
        return {odoo_attribute_id.id: attribute_api_response_json.get('id')}
