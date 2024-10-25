from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuWooCommerceWebhook(models.Model):
    _name = 'setu.woocommerce.webhook'
    _description = 'Woocommerce Webhook'

    name = fields.Char(string="Webhook Name")
    woocommerce_webhook_url = fields.Char(string="Woocommerce Webhook URL")
    woocommerce_webhook_id = fields.Char(string="Webhook ID", copy=False, size=100)
    operations = fields.Selection([("order.created", "When Order is Created"),
                                   ("order.updated", "When Order is Updated"),
                                   ("product.created", "When Product is Created"),
                                   ("product.updated", "When Product is Updated"),
                                   ("product.deleted", "When Product is Deleted"),
                                   ("product.restored", "When Product is Restored"),
                                   ("customer.created", "When Customer is Created"),
                                   ("customer.updated", "When Customer is Updated"),
                                   ("coupon.created", "When Coupon is Created"),
                                   ("coupon.updated", "When Coupon is Updated"),
                                   ("coupon.deleted", "When Coupon is Deleted")], string="Operations")
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', ondelete="cascade")
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)
    state = fields.Selection([('active', 'Active'), ('disabled', 'Disabled'), ('paused', 'Paused')], default='disabled',
                             string="Hook State")

    @api.model
    def create(self, vals):
        available_webhook = self.search_read([("operations", "=", vals.get("operations")), (
            "multi_ecommerce_connector_id", "=", vals.get("multi_ecommerce_connector_id"))], ["id"])
        if available_webhook:
            raise ValidationError(_(
                "The webhook has already been created for the same operation. "
                "You cannot create multiple webhooks for the same operation."))
        res = super(SetuWooCommerceWebhook, self).create(vals)
        res.create_and_prepare_woocommerce_webhook()
        return res

    def create_and_prepare_woocommerce_webhook(self):
        operations = self.operations
        multi_ecommerce_connector_id = self.multi_ecommerce_connector_id
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        woocommerce_webhook_url = self.get_webhook_url()
        if woocommerce_webhook_url[:woocommerce_webhook_url.find(":")] == 'http':
            raise ValidationError(_("Address protocol http:// is not supported for creating the webhooks."
                                    "Only instances having SSL connection https:// are permitted."))

        webhook_data = {"name": self.name, "topic": operations, "state": "active",
                        "delivery_url": woocommerce_webhook_url}

        if self.woocommerce_webhook_id:
            response = woo_api_connect.get("webhooks/" + str(self.woocommerce_webhook_id))
            if response.status_code == 200:
                self.state = response.json().get("status")
            else:
                self.woocommerce_webhook_id = 0
                self.sudo().unlink()
            return True

        response = woo_api_connect.post("webhooks", webhook_data)
        if response.status_code in [200, 201]:
            webhook_json_response = response.json()
            self.write({"woocommerce_webhook_id": webhook_json_response.get("id"),
                        "state": webhook_json_response.get("status"),
                        "woocommerce_webhook_url": woocommerce_webhook_url})
            return True
        raise ValidationError(
            _("Due to some request error. Webhook not configuration yet. Please check the response below \n" + str(
                response.status_code) + "\n" + response.reason))

    def get_webhook_url(self):
        operations = self.operations
        if operations == "order.created":
            webhook_url = self.get_base_url() + "/setu_create_order_webhook_woo_odoo"
        elif operations == "order.updated":
            webhook_url = self.get_base_url() + "/setu_update_order_webhook_woo_odoo"
        elif operations == "product.created":
            webhook_url = self.get_base_url() + "/setu_create_product_webhook_woo_odoo"
        elif operations == "product.updated":
            webhook_url = self.get_base_url() + "/setu_update_product_webhook_woo_odoo"
        elif operations == "product.deleted":
            webhook_url = self.get_base_url() + "/setu_delete_product_webhook_woo_odoo"
        elif operations == "product.restored":
            webhook_url = self.get_base_url() + "/setu_restore_product_webhook_woo_odoo"
        elif operations == "customer.created":
            webhook_url = self.get_base_url() + "/setu_create_customer_webhook_woo_odoo"
        elif operations == "customer.updated":
            webhook_url = self.get_base_url() + "/setu_update_customer_webhook_woo_odoo"
        elif operations == "coupon.created":
            webhook_url = self.get_base_url() + "/setu_create_coupon_webhook_woo_odoo"
        elif operations == "coupon.updated":
            webhook_url = self.get_base_url() + "/setu_update_coupon_webhook_woo_odoo"
        elif operations == "coupon.deleted":
            webhook_url = self.get_base_url() + "/setu_delete_coupon_webhook_woo_odoo"
        return webhook_url

    def unlink(self):
        woocommerce_webhook_ids = self.mapped("woocommerce_webhook_id")
        if woocommerce_webhook_ids:
            woo_api_connect = self.multi_ecommerce_connector_id.connect_with_woocommerce()
            data = {"delete": woocommerce_webhook_ids}

            response = woo_api_connect.post("webhooks/batch", data)
            if response.status_code not in [200, 201]:
                raise ValidationError(
                    _("Due to some request error. Webhook not delete yet. Please check the response below \n" + str(
                        response.status_code) + "\n" + response.reason))

        return super(SetuWooCommerceWebhook, self).unlink()

    def toggle_status(self, state=False):
        woo_api_connect = self.multi_ecommerce_connector_id.connect_with_woocommerce()
        for record_webhook_id in self:
            state = state if state else "paused" if record_webhook_id.state == "active" else "active"
            response = woo_api_connect.put("webhooks/" + str(record_webhook_id.woocommerce_webhook_id),
                                           {"status": state})
            if response.status_code in [200, 201]:
                record_webhook_id.state = state
            else:
                raise ValidationError(
                    _("Due to some request error. Webhook status not change yet. Please check the response below \n" + str(
                        response.status_code) + "\n" + response.reason))
        return True
