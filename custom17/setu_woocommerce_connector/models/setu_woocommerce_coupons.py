from odoo import fields, models, api, _
import requests
import ast


class SetuWooCommerceCoupons(models.Model):
    _name = 'setu.woocommerce.coupons'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'WooCommerce Coupons'
    _rec_name = 'code'

    active = fields.Boolean(string="Active", default=True)
    is_coupon_exported_in_woocommerce = fields.Boolean(string="Synced")
    free_shipping = fields.Boolean(string="Is Free Shipping",
                                   help="If true and if the free shipping method requires a coupon, this coupon will "
                                        "enable free shipping.")
    individual_use = fields.Boolean(string="Is Individual Use",
                                    help="If true, the coupon can only be used individually. Other applied coupons "
                                         "will be removed from the cart.")
    exclude_sale_items = fields.Boolean(string="Is Exclude In Sale Items",
                                        help="If true, this coupon will not be applied to items that have sale prices")
    woocommerce_coupon_id = fields.Char(string="Coupons ID", help="Unique identifier for the Coupons",)
    code = fields.Char(string="Code", required=1, help="Coupon code", translate=True)
    used_by = fields.Char(string="Used By",
                          help="List of user IDs (or guest email addresses) that have used the coupon.", translate=True)
    date_created = fields.Date(string="Date Created", help="The date the coupon was created")
    expiry_date = fields.Date(string="Expiry Date", help="The date the coupon expires")
    description = fields.Text(string='Description', help="Coupon description.", translate=True)
    discount_type = fields.Selection(
        [('percent', 'Percentage Discount'), ('fixed_cart', 'Fixed Cart Discount'), ('smart_coupon', 'Smart Coupon'),
         ('fixed_product', 'Fixed Product Discount')], string="Discount Type",
        default="fixed_cart", help="Determines the type of discount that will be applied.")
    usage_limit = fields.Integer(string="Usage limit", help="How many times the coupon can be used in total.")
    limit_usage_to_x_items = fields.Integer(string="Limit usage to X items",
                                            help="Max number of items in the cart the coupon can be applied to.")
    amount = fields.Float(string="Amount",
                          help="The amount of discount. Should always be numeric, even if setting a percentage.")
    minimum_amount = fields.Float(string="Minimum Spend",
                                  help="Minimum order amount that needs to be in the cart before coupon applies.")
    maximum_amount = fields.Float(string="Maximum Spend", help="Maximum order amount allowed when using the coupon.")
    usage_limit_per_user = fields.Integer(string="Usage limit per user",
                                          help="How many times the coupon can be used per customer.")
    usage_count = fields.Integer(string="Usage Count", help="Number of times the coupon has been used already.")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    setu_woocommerce_product_template_ids = fields.Many2many("setu.woocommerce.product.template",
                                                             'setu_woo_product_tmpl_coupon_rel', 'woo_product_tmpl_id',
                                                             'woo_coupon_id', string="Product Template",
                                                             help="List of product IDs the coupon can be used on.")
    setu_woocommerce_exclude_product_template_ids = fields.Many2many("setu.woocommerce.product.template",
                                                                     'setu_woo_product_tmpl_exclude_product_rel',
                                                                     'woo_product_tmpl_id', 'woo_coupon_id',
                                                                     string="Exclude Products Template",
                                                                     help="List of product IDs the coupon "
                                                                          "cannot be used on.")
    setu_woocommerce_product_variant_ids = fields.Many2many("setu.woocommerce.product.variant",
                                                            'setu_woo_product_variant_coupon_rel',
                                                            'woo_product_variant_id', 'woo_coupon_id',
                                                            string="Product Variants",
                                                            help="List of product variants IDs the "
                                                                 "coupon can be used on.")
    setu_woocommerce_exclude_product_variant_ids = fields.Many2many("setu.woocommerce.product.variant",
                                                                    'setu_woo_product_variant_exclude_product_rel',
                                                                    'woo_exclude_product_variant_id',
                                                                    'woo_exclude_coupon_id',
                                                                    string="Exclude Product Variants",
                                                                    help="List of product variants IDs the "
                                                                         "coupon cannot be used on.")
    need_to_update = fields.Boolean(string='Need To Update?')
    same_coupon_code_id = fields.Many2one('setu.woocommerce.coupons', string='Coupon with same Code',
                                          compute='_compute_same_coupon_code_id', store=False)

    @api.depends('code')
    def _compute_same_coupon_code_id(self):
        for coupon in self:
            # use _origin to deal with onchange()
            coupon_id = coupon._origin.id
            # active_test = False because if a partner has been deactivated you still want to raise the error,
            # so that you can reactivate it instead of creating a new one, which would loose its history.
            coupon = self.with_context(active_test=False).sudo()
            domain = [
                ('code', '=', coupon.code)
            ]
            existing_coupon = coupon.search(domain, limit=1)
            if existing_coupon:
                existing_coupon.same_coupon_code_id = coupon.id
            if coupon_id:
                domain += [('id', '!=', coupon_id)]
            coupon.same_coupon_code_id = bool(coupon) and not coupon.code and coupon.search(domain, limit=1)

    def write(self, vals):
        vals.update({'need_to_update': True})
        res = super(SetuWooCommerceCoupons, self).write(vals)
        return res

    def process_coupon_via_webhook_created(self, chain_lines, process_history_id):
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        multi_ecommerce_connector_id = chain_lines.multi_ecommerce_connector_id
        woocommerce_coupon_lst = []
        commit_count = 0
        for chain_line_id in chain_lines:
            commit_count += 1
            if commit_count == 30:
                chain_line_id.setu_woocommerce_coupon_chain_id.is_chain_in_process = True
                self._cr.commit()
                commit_count = 0
            coupon_data_dict = ast.literal_eval(chain_line_id.coupon_chain_line_data)
            coupon_id = coupon_data_dict.get("id")
            if not coupon_data_dict.get("code"):
                message = "Coupon code not available for coupon ID %s" % (coupon_id)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            code = coupon_data_dict.get("code")
            existing_woocommerce_coupon_id = self.with_context(active_test=False).search(
                [('woocommerce_coupon_id', '=', coupon_id), ('code', '=', code), (
                'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                limit=1)
            coupon_product_ids = coupon_data_dict.get("product_ids")

            setu_woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search(
                [("woocommerce_product_tmpl_id", "in", coupon_product_ids), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            remain_products = list(set(coupon_product_ids) - set(
                list(map(int, setu_woocommerce_product_template_ids.mapped("woocommerce_product_tmpl_id")))))
            setu_woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [("woocommerce_product_variant_id", "in", remain_products), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])

            remain_products = list(set(remain_products) - set(
                list(map(int, setu_woocommerce_product_variant_ids.mapped("woocommerce_product_variant_id")))))
            coupon_exclude_product_id = coupon_data_dict.get("excluded_product_ids")
            exclude_woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search(
                [("woocommerce_product_tmpl_id", "in", coupon_exclude_product_id), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])

            remain_exclude_products = list(set(coupon_exclude_product_id) - set(
                list(map(int, exclude_woocommerce_product_template_ids.mapped("woocommerce_product_tmpl_id")))))

            exclude_woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [("woocommerce_product_variant_id", "in", remain_exclude_products), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            remain_exclude_products = list(set(remain_exclude_products) - set(
                list(map(int, exclude_woocommerce_product_variant_ids.mapped("woocommerce_product_variant_id")))))

            if remain_products or remain_exclude_products:
                message = "Coupons which available on WooCommerce but not import due to'{0}'. " \
                          "Some of the products are not imported in Odoo.".format(
                    code)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)

            vals = self.import_and_sync_coupons_vals(coupon_id, code, coupon_data_dict, multi_ecommerce_connector_id,
                                                     setu_woocommerce_product_template_ids,
                                                     setu_woocommerce_product_variant_ids,
                                                     exclude_woocommerce_product_template_ids,
                                                     exclude_woocommerce_product_variant_ids)
            if not existing_woocommerce_coupon_id:
                existing_woocommerce_coupon_id = self.create(vals)
                chain_line_id.state = 'done'
            else:
                existing_woocommerce_coupon_id.write(vals)
                chain_line_id.state = 'done'
            woocommerce_coupon_lst += existing_woocommerce_coupon_id
            chain_line_id.setu_woocommerce_coupon_chain_id.is_chain_in_process = False
        return woocommerce_coupon_lst

    def fetch_and_create_coupons_woocommerce_to_erp(self, multi_ecommerce_connector_id):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        setu_woocommerce_product_category_obj.fetch_and_create_product_category_woocommerce_to_erp(
            multi_ecommerce_connector_id)

        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        self.process_for_import_coupons_woocommerce_to_erp(multi_ecommerce_connector_id, process_history_id)

        if not process_history_id.process_history_line_ids:
            process_history_id.sudo().unlink()

        return True

    def process_for_import_coupons_woocommerce_to_erp(self, multi_ecommerce_connector_id, process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        coupons_api_response = woo_api_connect.get('coupons', params={"per_page": 100})

        if not isinstance(coupons_api_response, requests.models.Response):
            message = "Invalid Response Format %s" % coupons_api_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(
                message, model_id, process_history_id)
            return True
        if coupons_api_response.status_code not in [200, 201]:
            message = "Invalid Request Format %s" % coupons_api_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(
                message, model_id, process_history_id)
            return True

        total_pages = coupons_api_response and coupons_api_response.headers.get('x-wp-totalpages', 0) or 1
        try:

            coupons_data_json = coupons_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing importing Coupons to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        all_import_coupons_list = coupons_data_json
        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                all_import_coupons_list += multi_ecommerce_connector_id.process_import_all_records(woo_api_connect,
                                                                                                   multi_ecommerce_connector_id,
                                                                                                   list_of_page,
                                                                                                   process_history_id,
                                                                                                   model_id,
                                                                                                   method='coupons')

        for coupon_data_dict in all_import_coupons_list:
            if not isinstance(coupon_data_dict, dict):
                continue

            coupon_id = coupon_data_dict.get("id")
            if not coupon_data_dict.get("code"):
                message = "Coupon code not available for coupon ID %s" % (coupon_id)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            code = coupon_data_dict.get("code")
            existing_woocommerce_coupon_id = self.with_context(active_test=False).search(
                [('woocommerce_coupon_id', '=', coupon_id), ('code', '=', code), (
                    'multi_ecommerce_connector_id', '=',
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                limit=1)
            coupon_product_ids = coupon_data_dict.get("product_ids")

            setu_woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search(
                [("woocommerce_product_tmpl_id", "in", coupon_product_ids), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            remain_products = list(set(coupon_product_ids) - set(
                list(map(int, setu_woocommerce_product_template_ids.mapped("woocommerce_product_tmpl_id")))))
            setu_woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [("woocommerce_product_variant_id", "in", remain_products), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])

            remain_products = list(set(remain_products) - set(
                list(map(int, setu_woocommerce_product_variant_ids.mapped("woocommerce_product_variant_id")))))
            coupon_exclude_product_id = coupon_data_dict.get("excluded_product_ids")
            exclude_woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search(
                [("woocommerce_product_tmpl_id", "in", coupon_exclude_product_id), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])

            remain_exclude_products = list(set(coupon_exclude_product_id) - set(
                list(map(int, exclude_woocommerce_product_template_ids.mapped("woocommerce_product_tmpl_id")))))

            exclude_woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [("woocommerce_product_variant_id", "in", remain_exclude_products), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            remain_exclude_products = list(set(remain_exclude_products) - set(
                list(map(int, exclude_woocommerce_product_variant_ids.mapped("woocommerce_product_variant_id")))))

            if remain_products or remain_exclude_products:
                message = "Coupons which available on WooCommerce but not import due to'{0}'. Some of the products are not imported in Odoo.".format(
                    code)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)

            vals = self.import_and_sync_coupons_vals(coupon_id, code, coupon_data_dict, multi_ecommerce_connector_id,
                                                     setu_woocommerce_product_template_ids,
                                                     setu_woocommerce_product_variant_ids,
                                                     exclude_woocommerce_product_template_ids,
                                                     exclude_woocommerce_product_variant_ids)
            if not existing_woocommerce_coupon_id:
                self.create(vals)
            else:
                existing_woocommerce_coupon_id.write(vals)
        return True

    def import_and_sync_coupons_vals(self, coupon_id, code, coupon_data_dict, multi_ecommerce_connector_id,
                                     setu_woocommerce_product_template_ids, setu_woocommerce_product_variant_ids,
                                     exclude_woocommerce_product_template_ids, exclude_woocommerce_product_variant_ids):
        coupons_vals = {
            'woocommerce_coupon_id': coupon_id,
            'code': code,
            'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
            'is_coupon_exported_in_woocommerce': True,
            'description': coupon_data_dict.get("description"),
            'discount_type': coupon_data_dict.get("discount_type"),
            'amount': coupon_data_dict.get("amount"),
            'free_shipping': coupon_data_dict.get("free_shipping"),
            'expiry_date': coupon_data_dict.get("date_expires") or False,
            'minimum_amount': float(coupon_data_dict.get("minimum_amount", 0.0)),
            'maximum_amount': float(coupon_data_dict.get("maximum_amount", 0.0)),
            'individual_use': coupon_data_dict.get("individual_use"),
            'exclude_sale_items': coupon_data_dict.get("exclude_sale_items"),
            'setu_woocommerce_product_template_ids': [(6, False, setu_woocommerce_product_template_ids.ids)],
            'setu_woocommerce_product_variant_ids': [(6, False, setu_woocommerce_product_variant_ids.ids)],
            'setu_woocommerce_exclude_product_template_ids': [(6, False, exclude_woocommerce_product_template_ids.ids)],
            'setu_woocommerce_exclude_product_variant_ids': [(6, False,
                                                              exclude_woocommerce_product_variant_ids.ids)] or '',
            'usage_limit': coupon_data_dict.get("usage_limit"),
            'limit_usage_to_x_items': coupon_data_dict.get("limit_usage_to_x_items"),
            'usage_limit_per_user': coupon_data_dict.get("usage_limit_per_user"),
            'usage_count': coupon_data_dict.get("usage_count"),
            'used_by': coupon_data_dict.get("used_by"),
            'active': True
        }
        return coupons_vals

    def export_erp_woocommerce_coupons(self, multi_ecommerce_connector_id, pending_exported_woocommerce_coupons_ids,
                                       process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        model_id = setu_process_history_line_obj.get_model_id(self._name)

        pending_woocommerce_lst = []
        for pending_exported_woocommerce_coupons_id in pending_exported_woocommerce_coupons_ids:
            woocommerce_include_products_lst = []
            woocommerce_exclude_products_lst = []

            for setu_woocommerce_product_template_id in pending_exported_woocommerce_coupons_id.setu_woocommerce_product_template_ids:
                woocommerce_include_products_lst.append(
                    setu_woocommerce_product_template_id.woocommerce_product_tmpl_id)

            for setu_woocommerce_product_variant_id in pending_exported_woocommerce_coupons_id.setu_woocommerce_product_variant_ids:
                woocommerce_include_products_lst.append(
                    setu_woocommerce_product_variant_id.woocommerce_product_variant_id)

            for exclude_product_tmpl_id in pending_exported_woocommerce_coupons_id.setu_woocommerce_exclude_product_template_ids:
                woocommerce_exclude_products_lst.append(exclude_product_tmpl_id.woocommerce_product_tmpl_id)

            for woocommerce_exclude_product_variant_id in pending_exported_woocommerce_coupons_id.setu_woocommerce_exclude_product_variant_ids:
                woocommerce_exclude_products_lst.append(
                    woocommerce_exclude_product_variant_id.woocommerce_product_variant_id)

            vals = {'code': pending_exported_woocommerce_coupons_id.code,
                    'description': str(pending_exported_woocommerce_coupons_id.description or '') or '',
                    'discount_type': pending_exported_woocommerce_coupons_id.discount_type,
                    'free_shipping': pending_exported_woocommerce_coupons_id.free_shipping,
                    'amount': str(pending_exported_woocommerce_coupons_id.amount),
                    'date_expires': "{}".format(pending_exported_woocommerce_coupons_id.expiry_date or ''),
                    'minimum_amount': str(pending_exported_woocommerce_coupons_id.minimum_amount),
                    'maximum_amount': str(pending_exported_woocommerce_coupons_id.maximum_amount),
                    'individual_use': pending_exported_woocommerce_coupons_id.individual_use,
                    'exclude_sale_items': pending_exported_woocommerce_coupons_id.exclude_sale_items,
                    'product_ids': woocommerce_include_products_lst,
                    'excluded_product_ids': woocommerce_exclude_products_lst,
                    'usage_limit': pending_exported_woocommerce_coupons_id.usage_limit,
                    'limit_usage_to_x_items': pending_exported_woocommerce_coupons_id.limit_usage_to_x_items,
                    'usage_limit_per_user': pending_exported_woocommerce_coupons_id.usage_limit_per_user}

            pending_woocommerce_lst.append(vals)
        coupon_dict = {"create": pending_woocommerce_lst}
        coupons_api_response = woo_api_connect.post("coupons/batch", coupon_dict)

        if not coupons_api_response:
            message = "Invalid Response Format, %s" % (coupons_api_response)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)

        if coupons_api_response.status_code not in [200, 201]:
            message = "Invalid Request Format, %s" % (coupons_api_response.content),
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)

        try:
            coupons_api_json_data = coupons_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing exporting Coupons to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)

        exported_coupon_data_lst = coupons_api_json_data.get("create")
        for exported_coupon_dict in exported_coupon_data_lst:
            pending_exported_woocommerce_coupons_id = pending_exported_woocommerce_coupons_ids.filtered(
                lambda x: x.code.lower() == exported_coupon_dict.get(
                    "code") and x.multi_ecommerce_connector_id.id == multi_ecommerce_connector_id.id)

            if exported_coupon_dict.get("id", False) and pending_exported_woocommerce_coupons_id:
                pending_exported_woocommerce_coupons_id.write({"woocommerce_coupon_id": exported_coupon_dict.get("id"),
                                                               "is_coupon_exported_in_woocommerce": True})

        return True

    def update_erp_woocommerce_coupons(self, multi_ecommerce_connector_id, pending_update_woocommerce_coupons_ids,
                                       process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        pending_woocommerce_lst = []
        for update_woocommerce_coupons_id in pending_update_woocommerce_coupons_ids:
            if update_woocommerce_coupons_id.need_to_update:
                woocommerce_include_products_lst = []
                woocommerce_exclude_products_lst = []

                for setu_woocommerce_product_template_id in update_woocommerce_coupons_id.setu_woocommerce_product_template_ids:
                    woocommerce_include_products_lst.append(
                        setu_woocommerce_product_template_id.woocommerce_product_tmpl_id)

                for setu_woocommerce_product_variant_id in update_woocommerce_coupons_id.setu_woocommerce_product_variant_ids:
                    woocommerce_include_products_lst.append(
                        setu_woocommerce_product_variant_id.woocommerce_product_variant_id)

                for exclude_product_tmpl_id in update_woocommerce_coupons_id.setu_woocommerce_exclude_product_template_ids:
                    woocommerce_exclude_products_lst.append(exclude_product_tmpl_id.woocommerce_product_tmpl_id)

                for woocommerce_exclude_product_variant_id in update_woocommerce_coupons_id.setu_woocommerce_exclude_product_variant_ids:
                    woocommerce_exclude_products_lst.append(
                        woocommerce_exclude_product_variant_id.woocommerce_product_variant_id)

                vals = {'code': update_woocommerce_coupons_id.code,
                        'description': str(update_woocommerce_coupons_id.description or '') or '',
                        'discount_type': update_woocommerce_coupons_id.discount_type,
                        'free_shipping': update_woocommerce_coupons_id.free_shipping,
                        'amount': str(update_woocommerce_coupons_id.amount),
                        'date_expires': "{}".format(update_woocommerce_coupons_id.expiry_date or ''),
                        'minimum_amount': str(update_woocommerce_coupons_id.minimum_amount),
                        'maximum_amount': str(update_woocommerce_coupons_id.maximum_amount),
                        'individual_use': update_woocommerce_coupons_id.individual_use,
                        'exclude_sale_items': update_woocommerce_coupons_id.exclude_sale_items,
                        'product_ids': woocommerce_include_products_lst,
                        'excluded_product_ids': woocommerce_exclude_products_lst,
                        'usage_limit': update_woocommerce_coupons_id.usage_limit,
                        'limit_usage_to_x_items': update_woocommerce_coupons_id.limit_usage_to_x_items,
                        'usage_limit_per_user': update_woocommerce_coupons_id.usage_limit_per_user}

                vals.update({'id': update_woocommerce_coupons_id.woocommerce_coupon_id})
                pending_woocommerce_lst.append(vals)

        coupons_api_response = woo_api_connect.put("coupons/batch", {'update': pending_woocommerce_lst})
        if not isinstance(coupons_api_response, requests.models.Response):
            message = "Invalid Response Format, %s" % (coupons_api_response)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if coupons_api_response.status_code not in [200, 201]:
            if coupons_api_response.status_code == 500:
                try:
                    coupons_api_json_data = coupons_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing exporting Coupons to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    return False
                message = coupons_api_response.content
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
        try:
            coupons_api_json_data = coupons_api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing exporting Coupons to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False
        return True
