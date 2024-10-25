import json

from odoo import fields, models, api, _
from .. import woocommerce
import requests
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError


class SetuMultiEcommerceConnector(models.Model):
    _inherit = 'setu.multi.ecommerce.connector'

    @api.model
    def _get_woocommerce_set_order_status(self):
        order_status = self.env.ref('setu_woocommerce_connector.setu_woocommerce_order_status_processing')
        return [(6, 0, [order_status.id])] if order_status else False

    def _get_woocommerce_number_of_multi_connector_count(self):
        for record_id in self:
            record_id.setu_woocommerce_payment_gateway_count = len(record_id.setu_woocommerce_payment_gateway_ids)

    @api.model
    def _woo_tz_get(self):
        return _tz_get(self)

    is_sync_woocommerce_product_images = fields.Boolean(string="Sync WooCommerce Images", default=True)
    is_manage_multiple_woocommerce_stock_export = fields.Boolean(string="Manage Multiple Stock", default=False)
    is_woocommerce_image_url = fields.Boolean(string="Image URL")
    woocommerce_verify_ssl = fields.Boolean(string="Verify SSL", default=False)
    woocommerce_host = fields.Char(string="Host")
    woocommerce_consumer_key = fields.Char(string="Consumer Key")
    woocommerce_consumer_secret = fields.Char(string="Consumer Secret")
    woocommerce_admin_username = fields.Char(string="Username")
    woocommerce_admin_password = fields.Char(string="Password")
    woocommerce_last_product_import = fields.Datetime(string="Last Date Product Import")
    woocommerce_last_order_import_date = fields.Datetime(string="Last Order Import Date",
                                                         help="This date is used to import order from this date.")
    woocommerce_last_update_product_stock = fields.Datetime(string="Last Product Stock Export")
    woocommerce_last_customer_import = fields.Datetime(string="Last Date Customer Import")
    woocommerce_version_control = fields.Selection([("wc/v3", "3.5+")], string="WooCommerce Version", default="wc/v3")
    woocommerce_attribute_type = fields.Selection([("select", "Select"), ("text", "Text")], string="Attribute Type",
                                                  default="select")
    woocommerce_store_timezone = fields.Selection("_woo_tz_get", help="Timezone of Store for requesting data.")
    ecommerce_connector = fields.Selection(selection_add=[('woocommerce_connector', 'WooCommerce')],
                                           default='woocommerce_connector', string="e-Commerce Connector",
                                           ondelete={'woocommerce_connector': 'set default'})
    woocommerce_weight_uom_id = fields.Many2one("uom.uom", string="Weight UoM",
                                                default=lambda self: self.env.ref("uom.product_uom_kgm"))
    setu_woocommerce_sale_order_process_ids = fields.One2many('setu.woocommerce.sale.process.configuration',
                                                              'multi_ecommerce_connector_id',
                                                              string="Order Process Configuration")
    setu_woocommerce_webhook_ids = fields.One2many("setu.woocommerce.webhook", "multi_ecommerce_connector_id",
                                                   string="Webhooks")
    setu_woocommerce_order_status_ids = fields.Many2many('setu.woocommerce.order.status',
                                                         'setu_woocommerce_ecommerce_connector_order_status_rel',
                                                         'multi_ecommerce_connector_id', 'woocommerce_order_status_id',
                                                         string="Woocommerce Order Status",
                                                         default=_get_woocommerce_set_order_status)
    export_stock_woocommerce_warehouse_ids = fields.Many2many('stock.warehouse',
                                                              'setu_woocommerce_connector_stock_warehouse_rel',
                                                              'multi_ecommerce_connector_id', 'stock_warehouse_id',
                                                              string='Warehouses')

    # ===========================================================================
    # DashBoard OF Woo Fields and Methods
    # ===========================================================================

    def _get_number_of_woocommerce_connector_count(self):
        for record_id in self:
            record_id.woocommerce_product_count = len(record_id.setu_woocommerce_product_template_ids)
            record_id.woocommerce_sale_order_count = len(record_id.woocommerce_sale_order_ids.filtered(
                lambda sale: sale.multi_ecommerce_connector_id.ecommerce_connector == 'woocommerce_connector'))
            record_id.woocommerce_account_move_count = len(record_id.woocommerce_account_move_ids.filtered(
                lambda mv: mv.multi_ecommerce_connector_id.ecommerce_connector == 'woocommerce_connector'))
            record_id.setu_woocommerce_payment_gateway_count = len(record_id.setu_woocommerce_payment_gateway_ids)

    setu_woocommerce_product_template_ids = fields.One2many('setu.woocommerce.product.template',
                                                            'multi_ecommerce_connector_id', string="Products")
    woocommerce_product_count = fields.Integer(compute='_get_number_of_woocommerce_connector_count', string="Product")
    woocommerce_sale_order_ids = fields.One2many('sale.order', 'multi_ecommerce_connector_id', string="Orders")
    woocommerce_sale_order_count = fields.Integer(compute='_get_number_of_woocommerce_connector_count',
                                                  string="Sale Order Count")
    woocommerce_account_move_ids = fields.One2many('account.move', 'multi_ecommerce_connector_id',
                                                   string="Invoices")
    woocommerce_account_move_count = fields.Integer(compute='_get_number_of_multi_connector_count', string="Invoice")
    setu_woocommerce_payment_gateway_ids = fields.One2many('setu.woocommerce.payment.gateway',
                                                           'multi_ecommerce_connector_id',
                                                           string="Payment Gateway")
    setu_woocommerce_payment_gateway_count = fields.Integer(compute='_get_number_of_woocommerce_connector_count',
                                                            string="Payment Count")

    def action_woocommerce_product_count(self):
        action = self.env.ref(
            'setu_woocommerce_connector.setu_woocommerce_multi_ecommerce_connector_product_template_action').sudo().read()[
            0]
        return action

    def action_woocommerce_sale_order_count(self):
        action = \
            self.env.ref(
                'setu_woocommerce_connector.setu_woocommerce_multi_ecommerce_connector_sale_action').sudo().read()[
                0]
        return action

    def action_woocommerce_account_move_account(self):
        action = self.env.ref(
            'setu_woocommerce_connector.setu_woocommerce_multi_ecommerce_connector_account_move_action').sudo().read()[
            0]
        return action

    _sql_constraints = [('unique_woocommerce_host', 'unique(woocommerce_host)',
                         "WooCommerce already exists for given host. Host must be Unique for the WooCommerce!")]

    @api.model
    def connect_with_woocommerce(self):
        wcapi = woocommerce.api.API(url=self.woocommerce_host,
                                    consumer_key=self.woocommerce_consumer_key,
                                    consumer_secret=self.woocommerce_consumer_secret,
                                    verify_ssl=self.woocommerce_verify_ssl,
                                    wp_api=True,
                                    version=self.woocommerce_version_control,
                                    query_string_auth=True,
                                    timeout=600)
        return wcapi

    @api.model
    def create(self, vals):
        connector = self._context.get('default_ecommerce_connector')
        if connector == 'woocommerce_connector':
            if vals.get("woocommerce_host").endswith('/'):
                vals["woocommerce_host"] = vals.get("woocommerce_host").rstrip('/')

            multi_ecommerce_connector_id = super(SetuMultiEcommerceConnector, self).create(vals)
            if multi_ecommerce_connector_id.ecommerce_connector == 'woocommerce_connector':
                odoo_currency_id = multi_ecommerce_connector_id.get_set_woocommerce_currency()
                price_list_id = multi_ecommerce_connector_id.get_set_woocommerce_price_list()
                crm_team_id = multi_ecommerce_connector_id.get_set_woocommerce_crm_team()
                multi_ecommerce_connector_id.write(
                    {'odoo_pricelist_id': price_list_id.id, 'crm_team_id': crm_team_id.id,
                     "odoo_currency_id": odoo_currency_id.id})

            return multi_ecommerce_connector_id
        return super(SetuMultiEcommerceConnector, self).create(vals)

    def get_set_woocommerce_currency(self):
        currency_id = self.fetch_woocommerce_currency_system()
        woo_currency_id = currency_id or self.env.user.currency_id or False
        return woo_currency_id

    def fetch_woocommerce_currency_system(self):
        currency_obj = self.env['res.currency']
        response = self.fetch_woocommerce_store_information()
        currency_code = ""
        currency_symbol = ""
        if not response:
            raise ValidationError(_("Response not proper format Please check the validate data."))

        currency_code = response.get('settings').get('currency', False)
        currency_symbol = response.get('settings').get('currency_symbol', False)

        if not (currency_code and currency_symbol):
            return False

        currency_id = currency_obj.search([('name', '=', currency_code)])
        if not currency_id:
            currency_id = currency_obj.search([('name', '=', currency_code), ('active', '!=', True)])
            currency_id.active = True
        if not currency_id:
            raise ValidationError(
                _("Currency {} not found in ERP. Please make sure currency is created for {} and is in active state.".format(
                    currency_code, currency_code)))

        return currency_id

    def fetch_woocommerce_store_information(self):
        try:
            wcapi = self.connect_with_woocommerce()
            res = wcapi.get("system_status")
            if not isinstance(res, requests.models.Response):
                raise ValidationError(_("Response not proper format Please check the validate data."))
            if res.status_code not in [200, 201]:
                # print("Hello")
                raise ValidationError(_("Reqeust not proper format Please check the validate data. %s" % res.content))
            try:
                response = res.json()
            except Exception as e:
                raise ValidationError(
                    _("Requests to resources that don't exist or are missing importing system information WooCommerce for %s %s" % self.name,
                      e))
            return response
        except Exception as e:
            raise ValidationError(_("Connection Failed. Configuration is missing or incorrect"))

    def get_set_woocommerce_price_list(self):
        price_list_obj = self.env['product.pricelist']
        vals = {'name': "{} Pricelist".format(self.name),
                'currency_id': self.odoo_currency_id and self.odoo_currency_id.id or False,
                "company_id": self.odoo_company_id.id}
        price_list_id = price_list_obj.create(vals)
        return price_list_id

    def get_set_woocommerce_crm_team(self):
        crm_team_obj = self.env['crm.team']
        vals = {'name': self.name, }
                # 'use_quotations': True}
        crm_team_id = crm_team_obj.create(vals)
        return crm_team_id

    def connection_woocommerce_connector(self):
        self.ensure_one()
        setu_woocommerce_payment_gateway_obj = self.env['setu.woocommerce.payment.gateway']

        wcapi = self.connect_with_woocommerce()
        res = wcapi.get("system_status")
        if not isinstance(res, requests.models.Response):
            raise ValidationError(_("Response not proper format Please check the validate data."))
        if res.status_code not in [200, 201]:
            raise ValidationError(_("Reqeust not proper format Please check the validate data. %s" % res.content))
        else:
            no_payment_method_id = setu_woocommerce_payment_gateway_obj.search(
                [("code", "=", "no_payment_method"), ("multi_ecommerce_connector_id", "=", self.id)])
            if not no_payment_method_id:
                setu_woocommerce_payment_gateway_obj.create({"name": "No Payment Method", "code": "no_payment_method",
                                                             "multi_ecommerce_connector_id": self.id})
            self.create_sale_process_configuration()

        self.write({'state': 'integrated'})
        return {"type": "ir.actions.client", "tag": "reload"}

    def create_sale_process_configuration(self):
        setu_woocommerce_payment_gateway_obj = self.env['setu.woocommerce.payment.gateway']
        setu_woocommerce_sale_process_configuration_obj = self.env['setu.woocommerce.sale.process.configuration']

        setu_woocommerce_payment_gateway_ids = setu_woocommerce_payment_gateway_obj.search(
            [("multi_ecommerce_connector_id", "=", self.id)])

        for setu_woocommerce_payment_gateway_id in setu_woocommerce_payment_gateway_ids:
            setu_woocommerce_sale_process_configuration_ids = setu_woocommerce_sale_process_configuration_obj.search(
                [('multi_ecommerce_connector_id', '=', self.id),
                 ('setu_woocommerce_payment_gateway_id', '=', setu_woocommerce_payment_gateway_id.id),
                 ('woocommerce_financial_status', 'in', ['paid', 'not_paid'])]).ids
            if setu_woocommerce_sale_process_configuration_ids:
                continue

            paid_vals = {'multi_ecommerce_connector_id': self.id,
                         'setu_woocommerce_payment_gateway_id': setu_woocommerce_payment_gateway_id.id,
                         'woocommerce_financial_status': "paid"}
            setu_woocommerce_sale_process_configuration_obj.create(paid_vals)
            not_paid_vals = {'multi_ecommerce_connector_id': self.id,
                             'setu_woocommerce_payment_gateway_id': setu_woocommerce_payment_gateway_id.id,
                             'woocommerce_financial_status': "not_paid"}
            setu_woocommerce_sale_process_configuration_obj.create(not_paid_vals)
        return True

    def woocommerce_connector_fully_integrate(self):
        if not (
                self.odoo_company_id or self.odoo_warehouse_id or self.stock_field_id or self.odoo_pricelist_id or self.setu_woocommerce_order_status_ids):
            raise ValidationError(
                _('Please select appropriate required fields such like company, warehouse, price list etc.'))
        if self.setu_woocommerce_payment_gateway_ids:
            if not self.setu_woocommerce_sale_order_process_ids:
                raise ValidationError(_('order process not configuration. Please configure order process. '))
        self.state = 'fully_integrated'
        return True

    def woocommerce_connector_toggle_active_value(self):
        setu_woocommerce_product_template_obj = self.env["setu.woocommerce.product.template"]
        setu_woocommerce_sale_order_process_configuration_obj = self.env["setu.woocommerce.sale.process.configuration"]
        setu_woocommerce_payment_gateway_obj = self.env["setu.woocommerce.payment.gateway"]
        setu_woocommerce_webhook_obj = self.env["setu.woocommerce.webhook"]
        setu_auto_delete_process_obj = self.env['setu.auto.delete.process']
        domain = [("multi_ecommerce_connector_id", "=", self.id)]

        if self.active:
            active = {"active": False}
            self.write(active)
            self.woocommerce_deactive_active_cron()
            setu_woocommerce_webhook_obj.search(domain).unlink()
            setu_auto_delete_process_obj.auto_delete_process(is_delete_chain_process=True)
        else:
            active = {"active": True}
            domain.append(("active", "=", False))
            self.write(active)
        setu_woocommerce_product_template_obj.search(domain).write(active)
        setu_woocommerce_sale_order_process_configuration_obj.search(domain).write(active)
        setu_woocommerce_payment_gateway_obj.search(domain).write(active)
        return True

    def woocommerce_deactive_active_cron(self):
        try:
            ir_stock_cron_id = self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_export_inventory_ecommerce_connector_%d' % self.id)
        except:
            ir_stock_cron_id = False
        try:
            ir_order_cron_id = self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_import_order_ecommerce_connector_%d' % self.id)
        except:
            ir_order_cron_id = False
        try:
            ir_order_status_cron_id = self.env.ref(
                'setu_woocommerce_connector.ir_cron_woocommerce_auto_update_order_status_ecommerce_connector_%d' % self.id)
        except:
            ir_order_status_cron_id = False
        if ir_stock_cron_id:
            ir_stock_cron_id.write({'active': False})
        if ir_order_cron_id:
            ir_order_cron_id.write({'active': False})
        if ir_order_status_cron_id:
            ir_order_status_cron_id.write({'active': False})

    def woocommerce_update_webhooks(self):
        for woocommerce_webhook_id in self.setu_woocommerce_webhook_ids:
            woocommerce_webhook_id.create_and_prepare_woocommerce_webhook()
        return True

    def process_import_all_records(self, woo_api_connect, multi_ecommerce_connector_id, list_of_page,
                                   process_history_id, model_id, method):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        api_response = woo_api_connect.get(method, params={"per_page": 100, 'page': list_of_page})
        if not isinstance(api_response, requests.models.Response):
            message = "Invalid Response Format %s" % api_response
            setu_process_history_line_id = setu_process_history_line_obj.woocommerce_common_process_history_line(
                message, model_id, process_history_id)
            setu_process_history_line_id.write({'record_id': self and self.id or False})
            return []
        if api_response.status_code not in [200, 201]:
            message = "Invalid Request Format %s" % api_response.content
            setu_process_history_line_id = setu_process_history_line_obj.woocommerce_common_process_history_line(
                message, model_id, process_history_id)
            setu_process_history_line_id.write({'record_id': self and self.id or False})
            return []
        try:
            data_json = api_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing exporting tag to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_id = setu_process_history_line_obj.woocommerce_common_process_history_line(
                message, model_id, process_history_id)
            setu_process_history_line_id.write({'record_id': self and self.id or False})
            return []
        return data_json
