from odoo import fields, models, api
import requests
import base64
from .img_file_upload import ImageUploader


class SetuWooCommerceProductCategory(models.Model):
    _name = 'setu.woocommerce.product.category'
    _description = 'WooCommerce Product Category'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_display_name'
    _order = 'complete_display_name'

    is_product_category_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    need_to_update = fields.Boolean(string='Need To Update?')
    name = fields.Char(string='Name', required=True, translate=True, help="Category name.")
    description = fields.Char(string='Description', translate=True, help="HTML description of the resource.")
    slug = fields.Char(string='Slug', help="An alphanumeric identifier for the resource unique to its type.",
                       translate=True)
    woocommerce_category_id = fields.Char(string='WooCommerce Category ID', readonly=True,
                                          help="Unique identifier for the resource.")
    url = fields.Char(string='Image URL', translate=True)
    response_url = fields.Char(string='Response URL', help="URL from WooCommerce", translate=True)
    complete_display_name = fields.Char(string='Complete Name', compute='_compute_complete_name', recursive=True,
                                        store=True, translate=True)
    display = fields.Selection(
        [('default', 'Default'), ('products', 'Products'), ('subcategories', 'Sub Categories'), ('both', 'Both')],
        string="Display Type", default='default', help="Category archive display type")
    image = fields.Binary('Image')
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False, required=True)
    parent_id = fields.Many2one('setu.woocommerce.product.category', string='Parent', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    is_woocommerce_product_image_url = fields.Boolean(string="Is Product Image URL ?",
                                                      related="multi_ecommerce_connector_id.is_sync_woocommerce_product_images")

    def write(self, vals):
        vals.update({'need_to_update': True})
        res = super(SetuWooCommerceProductCategory, self).write(vals)
        return res

    @api.depends('name', 'parent_id.complete_display_name')
    def _compute_complete_name(self):
        for category_id in self:
            if category_id.parent_id:
                category_id.complete_display_name = '%s / %s' % (
                    category_id.parent_id.complete_display_name, category_id.name)
            else:
                category_id.complete_display_name = category_id.name

    def fetch_and_create_product_category_woocommerce_to_erp(self, multi_ecommerce_connector_id):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        import_product_with_image = multi_ecommerce_connector_id.is_sync_woocommerce_product_images
        self.process_for_import_product_category_woocommerce_to_erp(multi_ecommerce_connector_id, process_history_id,
                                                                    woocommerce_product_category_id=False,
                                                                    woocommerce_product_category_name=False,
                                                                    import_product_with_image=import_product_with_image)

        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()
        return True

    def process_for_import_product_category_woocommerce_to_erp(self, multi_ecommerce_connector_id, process_history_id,
                                                               woocommerce_product_category_id=False,
                                                               woocommerce_product_category_name=False,
                                                               import_product_with_image=True):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        if woocommerce_product_category_id and woocommerce_product_category_id.is_product_category_exported_in_woocommerce:
            category_api_response = woo_api_connect.get(
                "products/categories/%s" % woocommerce_product_category_id.woocommerce_category_id)
            if not isinstance(category_api_response, requests.models.Response):
                if not isinstance(category_api_response, requests.models.Response):
                    message = "Invalid Request Format %s" % category_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                return True
            if category_api_response.status_code == 404:
                self.export_product_category_in_woocommerce(multi_ecommerce_connector_id,
                                                            [woocommerce_product_category_id], process_history_id)
                return True
        elif woocommerce_product_category_id and not woocommerce_product_category_id.is_product_category_exported_in_woocommerce:
            erp_woocommerce_product_category_id = self.woocommerce_product_category_create_and_update_erp(
                multi_ecommerce_connector_id, process_history_id, woocommerce_product_category_id,
                import_product_with_image)
            if erp_woocommerce_product_category_id:
                return erp_woocommerce_product_category_id
            else:
                self.export_product_category_in_woocommerce(multi_ecommerce_connector_id,
                                                            [woocommerce_product_category_id], process_history_id)
                return True
        elif not woocommerce_product_category_id and woocommerce_product_category_name:
            erp_woocommerce_product_category_id = self.woocommerce_product_category_create_and_update_erp(
                multi_ecommerce_connector_id, process_history_id, model_id, woocommerce_product_category_name,
                import_product_with_image)
            return erp_woocommerce_product_category_id
        else:
            category_api_response = woo_api_connect.get("products/categories", params={'per_page': 100})
            if not isinstance(category_api_response, requests.models.Response):
                message = "Invalid Request Format %s" % category_api_response
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True
            if category_api_response.status_code not in [200, 201]:
                message = category_api_response.content
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True

        total_pages = category_api_response and category_api_response.headers.get('x-wp-totalpages') or 1
        try:
            category_data_json = category_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or missing importing request category to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if woocommerce_product_category_id:
            category_response = [category_data_json]
        else:
            category_response = category_data_json
        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                category_response += multi_ecommerce_connector_id.process_import_all_records(woo_api_connect,
                                                                                             multi_ecommerce_connector_id,
                                                                                             list_of_page,
                                                                                             process_history_id,
                                                                                             model_id,
                                                                                             method='products/categories')
        finished_category_list = []
        for category_data in category_response:
            if not isinstance(category_data, dict):
                continue
            if category_data.get('id', False) in finished_category_list:
                continue
            category_data_list = []
            category_data_list.append(category_data)
            for category_data_dict in category_data_list:
                if not isinstance(category_data_dict, dict):
                    continue
                if category_data_dict.get('parent'):
                    parent_category_id = list(
                        filter(lambda category_id: category_id['id'] == category_data_dict.get('parent'),
                               category_response))
                    if parent_category_id:
                        parent_category_id = parent_category_id[0]
                    else:
                        parent_category_response = woo_api_connect.get(
                            "products/categories/%s" % (category_data_dict.get('parent')))
                        if not isinstance(parent_category_response, requests.models.Response):
                            message = "Invalid request format %s" % (parent_category_response)
                            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                  process_history_id)
                            continue
                        try:
                            parent_category_data_json = parent_category_response.json()
                        except Exception as e:
                            message = "Requests to resources that don't exist or missing importing request parent category %s for Woocommerce %s %s" % (
                                category_data_dict.get('name'), multi_ecommerce_connector_id.name, e)
                            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                  process_history_id)
                            continue

                        parent_category_id = parent_category_data_json
                    if parent_category_id not in category_data_list:
                        category_data_list.append(parent_category_id)

            category_data_list.reverse()
            for child_data_dict in category_data_list:
                if not isinstance(child_data_dict, dict):
                    continue
                if child_data_dict.get('id') in finished_category_list:
                    continue

                woocommerce_category_id = child_data_dict.get('id')
                woocommerce_category_name = child_data_dict.get('name')
                woocommerce_category_display = child_data_dict.get('display')
                woocommerce_category_slug = child_data_dict.get('slug')
                woocommerce_category_parent_id = child_data_dict.get('parent')
                parent_id = False
                binary_img_data = False
                if woocommerce_category_parent_id:
                    parent_id = self.search([('woocommerce_category_id', '=', child_data_dict.get('parent')),
                                             ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)],
                                            limit=1)
                vals = {'name': woocommerce_category_name,
                        'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                        'display': woocommerce_category_display,
                        'slug': woocommerce_category_slug, 'is_product_category_exported_in_woocommerce': True,
                        'parent_id': parent_id and parent_id.id, 'description': child_data_dict.get('description', '')}

                if import_product_with_image:
                    res_image = child_data_dict.get('image') and child_data_dict.get('image').get('src', '')
                    if multi_ecommerce_connector_id.is_sync_woocommerce_product_images:
                        res_image and vals.update({'response_url': res_image})
                    else:
                        if res_image:
                            try:
                                res_img = requests.get(res_image, stream=True, verify=False, timeout=10)
                                if res_img.status_code == 200:
                                    binary_img_data = base64.b64encode(res_img.content)
                            except Exception:
                                message = "Requests to resources that don't exist or are missing importing request category to WooCommerce for %s %s" % (
                                    multi_ecommerce_connector_id.name, e)
                                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                      process_history_id)
                                pass
                        binary_img_data and vals.update({'image': binary_img_data})
                vals.update({'woocommerce_category_id': woocommerce_category_id, 'slug': woocommerce_category_slug})
                existing_product_category_id = self.search([
                    ('woocommerce_category_id', '=', woocommerce_category_id),
                    ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
                if not existing_product_category_id:
                    existing_product_category_id = self.search([('slug', '=', woocommerce_category_slug), (
                        'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
                if existing_product_category_id:
                    existing_product_category_id.write(vals)
                else:
                    self.create(vals)
                finished_category_list.append(child_data_dict.get('id', False))
        return True

    def woocommerce_product_category_create_and_update_erp(self, multi_ecommerce_connector_id, process_history_id,
                                                           woocommerce_product_category_id, import_product_with_image):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        product_category_lst = []
        product_category_name_lst = []
        existing_product_category_id = False
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        category_api_response = woo_api_connect.get("products/categories?fields=id,name,parent")
        if not isinstance(category_api_response, requests.models.Response):
            message = "Invalid request format %s" % (category_api_response.content)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False
        if category_api_response.status_code not in [200, 201]:
            message = "Invalid request format %s" % (category_api_response.content)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False
        try:
            category_data_json = category_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or missing importing request data to WooCommerce Category %s for %s %s" % (
                woocommerce_product_category_id.name, multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False
        name_based_category_ids = list(
            filter(lambda category_id: category_id['name'].lower() == woocommerce_product_category_id.name.lower(),
                   category_data_json))
        if name_based_category_ids:
            name_based_category_id = name_based_category_ids[0]
            product_category_lst.append(name_based_category_id.get('id'))
            product_category_name_lst.append(woocommerce_product_category_id.name.lower())
        for product_category_id in product_category_lst:
            id_based_category_ids = list(
                filter(lambda category_id: category_id['id'] == product_category_id, category_data_json))
            if id_based_category_ids:
                id_based_category_id = id_based_category_ids[0]
                if id_based_category_id.get('parent') and id_based_category_id.get(
                        'parent') not in product_category_lst:
                    id_based_category_id.append(id_based_category_id.get('parent'))
                    id_based_category_parent_id = list(
                        filter(lambda category_id: category_id['id'] == id_based_category_id.get('parent'),
                               category_data_json))
                    id_based_category_parent_id and product_category_name_lst.append(
                        id_based_category_parent_id[0].get('name').lower())

        product_category_lst.reverse()
        for single_product_category_id in product_category_lst:
            single_category_api_response = woo_api_connect.get("products/categories/%s" % (single_product_category_id))
            if not isinstance(single_category_api_response, requests.models.Response):
                message = "Invalid Response format %s" % single_category_api_response
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            if single_category_api_response.status_code not in [200, 201]:
                message = "Invalid Request Format %s" % single_category_api_response.content
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            try:
                single_category_data_json = single_category_api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or missing importing request category to WooCommerce Category %s for %s %s" % (
                    single_product_category_id, multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue

            single_product_category_dict = {'id': single_category_data_json.get('id'),
                                            'name': single_category_data_json.get('name')}
            single_product_category_name = single_product_category_dict.get('name')
            if single_product_category_name.lower() in product_category_name_lst:
                single_product_category_id_response = woo_api_connect.get(
                    "products/categories/%s" % (single_product_category_dict.get('id')))
                if not isinstance(single_product_category_id_response, requests.models.Response):
                    message = "Invalid Request Format %s" % (single_product_category_id_response.content)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                try:
                    id_by_single_response_data_json = single_product_category_id_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or missing importing request category to WooCommerce Category %s for %s %s" % (
                        single_product_category_dict.get('id'), multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue

                single_response_parent_id = id_by_single_response_data_json.get('parent')
                parent_id = False
                binary_img_data = False
                if single_response_parent_id:
                    parent_id = self.search([('woocommerce_category_id', '=', single_response_parent_id),
                                             ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)],
                                            limit=1).id
                vals = {'name': single_product_category_name,
                        'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                        'parent_id': parent_id,
                        'woocommerce_category_id': single_product_category_dict.get('id'),
                        'display': id_by_single_response_data_json.get('display'),
                        'slug': id_by_single_response_data_json.get('slug'),
                        'is_product_category_exported_in_woocommerce': True,
                        'description': id_by_single_response_data_json.get('description', '')}

                if import_product_with_image:
                    res_image = id_by_single_response_data_json.get('image') and id_by_single_response_data_json.get(
                        'image').get('src', '')
                    if multi_ecommerce_connector_id.is_sync_woocommerce_product_images:
                        res_image and vals.update({'response_url': res_image})
                    else:
                        if res_image:
                            try:
                                res_img = requests.get(res_image, stream=True, verify=False, timeout=10)
                                if res_img.status_code == 200:
                                    binary_img_data = base64.b64encode(res_img.content)
                            except Exception:
                                message = "Requests to resources that don't exist or are missing importing request category to WooCommerce for %s %s" % (
                                    multi_ecommerce_connector_id.name, e)
                                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                      process_history_id)
                                pass
                        binary_img_data and vals.update({'image': binary_img_data})
                existing_product_category_id = self.search(
                    [('woocommerce_category_id', '=', single_product_category_dict.get('id')),
                     ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
                if not existing_product_category_id:
                    existing_product_category_id = self.search(
                        [('slug', '=', id_by_single_response_data_json.get('slug')),
                         ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
                if existing_product_category_id:
                    existing_product_category_id.write(vals)
                else:
                    existing_product_category_id = self.create(vals)
        return existing_product_category_id

    @api.model
    def export_product_category_in_woocommerce(self, multi_ecommerce_connector_id, woocommerce_product_category_ids,
                                               process_history_id):

        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        for woocommerce_product_category_id in woocommerce_product_category_ids:
            if woocommerce_product_category_id.woocommerce_category_id:
                category_api_response = woo_api_connect.get(
                    "products/categories/%s" % (woocommerce_product_category_id.woocommerce_category_id))
                if not isinstance(category_api_response, requests.models.Response):
                    message = "Invalid Response Format %s" % category_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if category_api_response.status_code not in [200, 201, 404]:
                    message = "Invalid Request Format %s" % category_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
            category_data_list = []
            category_data_list.append(woocommerce_product_category_id)
            for category_data_id in category_data_list:
                if category_data_id.parent_id and category_data_id.parent_id not in category_data_list and not category_data_id.parent_id.woocommerce_category_id:
                    category_data_list.append(category_data_id.parent_id)

            category_data_list.reverse()
            for woocommerce_product_category_id in category_data_list:
                url_image = ''
                if multi_ecommerce_connector_id.is_sync_woocommerce_product_images:
                    if woocommerce_product_category_id.response_url:
                        try:
                            img = requests.get(woocommerce_product_category_id.response_url, stream=True, verify=False,
                                               timeout=10)
                            if img.status_code == 200:
                                url_image = woocommerce_product_category_id.response_url
                            elif woocommerce_product_category_id.url:
                                url_image = woocommerce_product_category_id.url
                        except Exception:
                            url_image = woocommerce_product_category_id.url or ''
                    elif woocommerce_product_category_id.url:
                        url_image = woocommerce_product_category_id.url
                else:
                    res = {}
                    if woocommerce_product_category_id.image:
                        res = ImageUploader.upload_image(multi_ecommerce_connector_id,
                                                           woocommerce_product_category_id.image, "%s_%s" % (
                                                               woocommerce_product_category_id.name,
                                                               woocommerce_product_category_id.id))
                    url_image = res and res.get('url', False) or ''
                payload_dict = {'name': str(woocommerce_product_category_id.name),
                                'description': str(woocommerce_product_category_id.description or ''),
                                'display': str(woocommerce_product_category_id.display), }
                if woocommerce_product_category_id.slug:
                    payload_dict.update({'slug': str(woocommerce_product_category_id.slug)})
                url_image and payload_dict.update({'image': url_image})
                payload_dict.update({'image': {'src': url_image}})
                woocommerce_product_category_id.parent_id.woocommerce_category_id and payload_dict.update(
                    {'parent': woocommerce_product_category_id.parent_id.woocommerce_category_id})
                data = payload_dict
                batch_category_api_response = woo_api_connect.post("products/categories", data)
                if not isinstance(batch_category_api_response, requests.models.Response):
                    continue
                if batch_category_api_response.status_code not in [200, 201]:
                    if batch_category_api_response.status_code == 500:
                        try:
                            batch_category_data_json = batch_category_api_response.json()
                        except Exception as e:
                            message = "Requests to resources that don't exist or missing importing request category to WooCommerce for %s %s" % (
                                multi_ecommerce_connector_id.name, e)
                            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                  process_history_id)
                            continue
                        if isinstance(batch_category_data_json, dict) and batch_category_data_json.get('code') == 'term_exists':
                            woocommerce_product_category_id.write({'woocommerce_category_id': batch_category_data_json.get('data'),'is_product_category_exported_in_woocommerce': True})
                            continue
                    else:
                        message = batch_category_api_response.content
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,  process_history_id)
                        continue
                try:
                    batch_category_data_json = batch_category_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing importing request category WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if not isinstance(batch_category_data_json, dict):
                    message = "Requests to resources that don't exist or are missing importing request category to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue

                woocommerce_category_id = batch_category_data_json and batch_category_data_json.get('id', False)
                slug = batch_category_data_json and batch_category_data_json.get('slug', '')
                response_data = {}
                if multi_ecommerce_connector_id.is_sync_woocommerce_product_images:
                    response_url = batch_category_data_json and batch_category_data_json.get(
                        'image') and batch_category_data_json.get('image', {}).get('src', '') or ''
                    response_data.update({'response_url': response_url or ''})
                if woocommerce_category_id:
                    response_data.update({'woocommerce_category_id': woocommerce_category_id, 'slug': slug,
                                          'is_product_category_exported_in_woocommerce': True})
                    woocommerce_product_category_id.write(response_data)
        return True

    def update_product_category_in_woocommerce(self, multi_ecommerce_connector_id, pending_update_category_ids,
                                               process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']

        pending_update_category_lst = []

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()

        for pending_update_category_id in pending_update_category_ids:
            if pending_update_category_id.need_to_update:
                if pending_update_category_id in pending_update_category_lst:
                    continue
                update_category_lst = []
                update_category_lst.append(pending_update_category_id)
                for product_category_id in update_category_lst:
                    if product_category_id.parent_id and product_category_id.parent_id not in update_category_lst and product_category_id.parent_id not in pending_update_category_lst:
                        self.process_for_import_product_category_woocommerce_to_erp(multi_ecommerce_connector_id, process_history_id, woocommerce_product_category_id=product_category_id.parent_id)
                        update_category_lst.append(product_category_id.parent_id)

                update_category_lst.reverse()
                for woocommerce_product_category_id in update_category_lst:
                    url_image = ''
                    res = {}
                    if woocommerce_product_category_id.image:
                        res = ImageUploader.upload_image(multi_ecommerce_connector_id,
                                                           woocommerce_product_category_id.image, "%s_%s" % (
                                                               woocommerce_product_category_id.name,
                                                               woocommerce_product_category_id.id))
                    url_image = res and res.get('url', False) or ''

                    payload_data = {'name': str(woocommerce_product_category_id.name),
                                    'display': str(woocommerce_product_category_id.display),
                                    'description': str(woocommerce_product_category_id.description or '')}

                    if woocommerce_product_category_id.slug:
                        payload_data.update({'slug': str(woocommerce_product_category_id.slug)})
                    woocommerce_product_category_id.parent_id.woocommerce_category_id and payload_data.update(
                        {'parent': woocommerce_product_category_id.parent_id.woocommerce_category_id})

                    payload_data.update({'id': woocommerce_product_category_id.woocommerce_category_id})
                category_api_response = woo_api_connect.post('products/categories/batch', {'update': [payload_data]})
                if not isinstance(category_api_response, requests.models.Response):
                    message = "Invalid Response Format %s" % category_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if category_api_response.status_code not in [200, 201]:
                    message = "Invalid Request Format %s" % category_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                try:
                    category_api_data_response = category_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing updating category to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if not isinstance(category_api_data_response, dict):
                    message = "Invalid Response format %s" % category_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                pending_update_category_lst.append(woocommerce_product_category_id)
            if not process_history_id.process_history_line_ids:
                process_history_id.sudo().unlink()
        return True

    def process_via_product_category_export_and_update(self, woocommerce_product_tmpl_id, multi_ecommerce_connector_id,
                                                       process_history_id):
        woocommerce_product_category_lst = []
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()

        for woocommerce_product_category_id in woocommerce_product_tmpl_id.setu_woocommerce_product_category_ids:
            if not woocommerce_product_category_id.woocommerce_category_id:
                woocommerce_product_category_id.process_for_import_product_category_woocommerce_to_erp(
                    multi_ecommerce_connector_id, process_history_id,
                    woocommerce_product_category_id=woocommerce_product_category_id)
                woocommerce_product_category_id.woocommerce_category_id and woocommerce_product_category_lst.append(
                    woocommerce_product_category_id.woocommerce_category_id)
            else:
                category_api_response = woo_api_connect.get(
                    "products/categories/%s" % woocommerce_product_category_id.woocommerce_category_id)
                if not isinstance(category_api_response, requests.models.Response):
                    message = "Invalid Response format %s" % category_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                try:
                    category_api_response_json = category_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing exporting category to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                if category_api_response_json and category_api_response_json.get('id'):
                    woocommerce_product_category_lst.append(woocommerce_product_category_id.woocommerce_category_id)
                else:
                    if woocommerce_product_tmpl_id.is_product_template_exported_in_woocommerce:
                        woocommerce_product_category_id.export_product_category_in_woocommerce(
                            multi_ecommerce_connector_id, [woocommerce_product_category_id], process_history_id)
                    else:
                        woocommerce_product_category_id.process_for_import_product_category_woocommerce_to_erp(
                            multi_ecommerce_connector_id, process_history_id,
                            woocommerce_product_category_id=woocommerce_product_category_id)
                    woocommerce_product_category_id.woocommerce_category_id and woocommerce_product_category_lst.append(
                        woocommerce_product_category_id.woocommerce_category_id)
        return woocommerce_product_category_lst
