from odoo import fields, models, api
import requests


class SetuWooCommerceProductTags(models.Model):
    _name = 'setu.woocommerce.product.tags'
    _description = 'WooCommerce Product Tags'
    _order = 'name'

    is_product_tags_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    name = fields.Char(string="Name", required=True, help="Tag name", translate=True)
    woocommerce_tag_id = fields.Char(string="WooCommerce Tags ID", help="Unique identifier for the resource.")
    description = fields.Text(string='Description', help="HTML description of the resource", translate=True)
    slug = fields.Char(string='Slug', help="An alphanumeric identifier for the resource unique to its type.",
                       translate=True)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False, required=True)
    need_to_update = fields.Boolean(string='Need To Update?')

    def write(self, vals):
        vals.update({'need_to_update': True})
        res = super(SetuWooCommerceProductTags, self).write(vals)
        return res

    def fetch_and_create_product_tags_woocommerce_to_erp(self, multi_ecommerce_connector_id):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        self.process_for_import_product_tags_woocommerce_to_erp(multi_ecommerce_connector_id, process_history_id)
        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()
        return True

    def process_for_import_product_tags_woocommerce_to_erp(self, multi_ecommerce_connector_id, process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        tags_api_response = woo_api_connect.get("products/tags", params={"per_page": 100})

        if not isinstance(tags_api_response, requests.models.Response):
            message = "Invalid Response Format %s" % tags_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True
        if tags_api_response.status_code not in [200, 201]:
            message = "Invalid Request Format %s" % tags_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return True

        total_pages = tags_api_response and tags_api_response.headers.get('x-wp-totalpages', 0) or 1
        try:
            tag_data_json = tags_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing importing tags to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        all_import_tag_list = tag_data_json
        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                all_import_tag_list += multi_ecommerce_connector_id.process_import_all_records(woo_api_connect,
                                                                                               multi_ecommerce_connector_id,
                                                                                               list_of_page,
                                                                                               process_history_id,
                                                                                               model_id,
                                                                                               method='products/tags')
        for data_import_tags_id in all_import_tag_list:
            if not isinstance(data_import_tags_id, dict):
                continue
            woocommerce_tag_id = data_import_tags_id.get('id')
            name = data_import_tags_id.get('name')
            description = data_import_tags_id.get('description')
            slug = data_import_tags_id.get('slug')
            existing_product_tag_id = self.search([('woocommerce_tag_id', '=', woocommerce_tag_id), (
                'multi_ecommerce_connector_id', '=',
                multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)], limit=1)
            if not existing_product_tag_id:
                existing_product_tag_id = self.search([('slug', '=', slug),
                                                       ('multi_ecommerce_connector_id', '=',
                                                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                                      limit=1)
            if existing_product_tag_id:
                existing_product_tag_id.write(
                    {'woocommerce_tag_id': woocommerce_tag_id, 'name': name, 'description': description, 'slug': slug,
                     'is_product_tags_exported_in_woocommerce': True})
            else:
                self.create({'woocommerce_tag_id': woocommerce_tag_id, 'name': name, 'description': description,
                             'slug': slug, 'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                             'is_product_tags_exported_in_woocommerce': True})
        return True

    @api.model
    def process_to_update_product_tags_erp_to_woocommerce(self, multi_ecommerce_connector_ids, product_tags_ids,
                                                          process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        tag_data_json = []
        for multi_ecommerce_connector_id in multi_ecommerce_connector_ids:
            woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
            upload_product_list = []
            for product_tags_id in product_tags_ids.filtered(
                    lambda x: x.multi_ecommerce_connector_id == multi_ecommerce_connector_id):
                if product_tags_id.need_to_update:
                    payload = {"id": product_tags_id.woocommerce_tag_id, "name": product_tags_id.name,
                               "description": str(product_tags_id.description or ""),
                               "slug": str(product_tags_id.slug or "")}
                    upload_product_list.append(payload)

            data = {"update": upload_product_list}
            tags_api_response = woo_api_connect.post("products/tags/batch", data)
            if not isinstance(tags_api_response, requests.models.Response):
                message = "Invalid Response format %s" % (tags_api_response)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            if tags_api_response.status_code not in [200, 201]:
                if tags_api_response.status_code == 500:
                    try:
                        tag_data_json = tags_api_response.json()
                    except Exception as e:
                        message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                            multi_ecommerce_connector_id.name, e)
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)
                    if isinstance(tag_data_json, dict) and tag_data_json.get("code") == "term_exists":
                        return False
                    else:
                        message = tags_api_response.content
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)
            try:
                tag_data_json = tags_api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                    multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False

            if tag_data_json:
                updated_product_tags_list = tag_data_json.get("update")
                if updated_product_tags_list:
                    for data_updated_product_tags_id in updated_product_tags_list:
                        existing_product_tag_id = product_tags_ids.filtered(
                            lambda x: x.woocommerce_tag_id == data_updated_product_tags_id.get(
                                "id") and x.multi_ecommerce_connector_id == multi_ecommerce_connector_id)
                        if existing_product_tag_id:
                            existing_product_tag_id.write({"slug": data_updated_product_tags_id.get("slug", "")})
        return True

    @api.model
    def process_to_export_product_tags_erp_to_woocommerce(self, multi_ecommerce_connector_id, product_tags_ids,
                                                          process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        product_tag_list = []
        for product_tags_id in product_tags_ids.filtered(
                lambda x: x.multi_ecommerce_connector_id == multi_ecommerce_connector_id):
            payload_data = {"name": product_tags_id.name, "description": str(product_tags_id.description or ""),
                            "slug": str(product_tags_id.slug or "")}
            product_tag_list.append(payload_data)

        data = {"create": product_tag_list}
        tags_api_response = woo_api_connect.post("products/tags/batch", data)
        if not isinstance(tags_api_response, requests.models.Response):
            message = "Invalid request format %s" % (tags_api_response.content)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                  process_history_id)
            return False
        if tags_api_response.status_code not in [200, 201]:
            if tags_api_response.status_code == 500:
                try:
                    tag_data_json = tags_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                if isinstance(tag_data_json, dict) and tag_data_json.get("code") == "term_exists":
                    product_tags_id.write({"woocommerce_tag_id": tag_data_json.get("data"),
                                           "is_product_tags_exported_in_woocommerce": True})
                else:
                    message = tags_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
            else:
                message = tags_api_response.content
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
        try:
            tag_data_json = tags_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)

            return False
        exported_product_tags = tag_data_json.get("create")
        for exported_product_tag_id in exported_product_tags:
            pending_exported_tag_id = product_tags_ids.filtered(
                lambda tag_id: tag_id.name == exported_product_tag_id.get(
                    "name") and tag_id.multi_ecommerce_connector_id == multi_ecommerce_connector_id)
            if exported_product_tag_id.get("id", False) and pending_exported_tag_id:
                pending_exported_tag_id.write({"woocommerce_tag_id": exported_product_tag_id.get("id", False),
                                               "is_product_tags_exported_in_woocommerce": True,
                                               "slug": exported_product_tag_id.get("slug", "")})
        return True

    def process_via_product_tag_export_and_update(self, woocommerce_product_template_id, multi_ecommerce_connector_id,
                                                  process_history_id):
        woocommerce_product_tag_lst = []
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        for woocommerce_product_tag_id in woocommerce_product_template_id.setu_woocommerce_product_tag_ids:
            if not woocommerce_product_tag_id.woocommerce_tag_id:
                woocommerce_product_tag_id.export_product_tags_in_woocommerce(multi_ecommerce_connector_id,
                                                                              woocommerce_product_tag_id,
                                                                              process_history_id)
                woocommerce_product_tag_id.woocommerce_tag_id and woocommerce_product_tag_lst.append(
                    woocommerce_product_tag_id.woocommerce_tag_id)
            else:
                tags_api_response = woo_api_connect.get(
                    "products/tags/%s" % woocommerce_product_tag_id.woocommerce_tag_id)
                if not isinstance(tags_api_response, requests.models.Response):
                    message = "Invalid request format %s" % tags_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                try:
                    tag_data_json = tags_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if tag_data_json and tag_data_json.get('id'):
                    woocommerce_product_tag_lst.append(woocommerce_product_tag_id.woocommerce_tag_id)
                else:
                    woocommerce_product_tag_id.woo_export_product_tags(multi_ecommerce_connector_id,
                                                                       woocommerce_product_tag_id, process_history_id)
                    woocommerce_product_tag_id.woocommerce_tag_id and woocommerce_product_tag_lst.append(
                        woocommerce_product_tag_id.woocommerce_tag_id)
        return woocommerce_product_tag_lst
