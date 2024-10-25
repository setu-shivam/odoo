# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger("Woo")


class SetuWooCommerceWebhooksMain(http.Controller):

    def fetch_multi_ecommerce_connector_details(self):
        # request_json = request.get_json_data()
        request_json = request.dispatcher.jsonrequest
        headers = request.httprequest.headers
        host = headers.get("X-WC-Webhook-Source").rstrip('/')
        multi_woocommerce_connector_id = request.env["setu.multi.ecommerce.connector"].sudo().search(
            [("woocommerce_host", "ilike", host), ('ecommerce_connector', '=', 'woocommerce_connector')])
        return request_json, multi_woocommerce_connector_id

    # ORDER Webhooks
    @http.route("/setu_create_order_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def create_order_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        if multi_ecommerce_connector_id.active and request_json.get(
                "status") in multi_ecommerce_connector_id.setu_woocommerce_order_status_ids.mapped("status"):
            request.env["sale.order"].sudo().process_to_create_sale_order_via_webhook(request_json,
                                                                                      multi_ecommerce_connector_id,
                                                                                      True)
        return

    @http.route("/setu_update_order_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def update_order_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        if multi_ecommerce_connector_id.active:
            if request.env["sale.order"].sudo().search_read([
                ("multi_ecommerce_connector_id", "=",
                 multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                ("ecommerce_order_id", "=", request_json.get("id")),
                ("woocommerce_order_number", "=", request_json.get("number"))], ["id"]):
                request.env["sale.order"].sudo().process_to_create_sale_order_via_webhook(request_json,
                                                                                          multi_ecommerce_connector_id,
                                                                                          True)
            elif request_json.get(
                    "status") in multi_ecommerce_connector_id.setu_woocommerce_order_status_ids.mapped("status"):
                request.env["sale.order"].sudo().process_to_create_sale_order_via_webhook(
                    request_json,
                    multi_ecommerce_connector_id,
                    True)
        return

    # Product Webhooks
    @http.route("/setu_create_product_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def create_product_webhook(self):
        self.product_webhook_process()

    @http.route("/setu_update_product_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def update_product_webhook(self):
        self.product_webhook_process()

    @http.route("/setu_restore_product_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def restore_product_webhook(self):
        self.product_webhook_process()

    @http.route("/setu_delete_product_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def delete_product_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        setu_woocommerce_product_template_id = request.env["setu.woocommerce.product.template"].sudo().search(
            [("woocommerce_product_tmpl_id", "=", request_json.get('id')),
             ("multi_ecommerce_connector_id", "=",
              multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
            limit=1)
        if setu_woocommerce_product_template_id:
            setu_woocommerce_product_template_id.write({'active': False})
        return

    def product_webhook_process(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        setu_woocommerce_product_template_id = request.env["setu.woocommerce.product.template"].sudo().with_context(
            active_test=False).search([("woocommerce_product_tmpl_id", "=", request_json.get('id')),
                                       ("multi_ecommerce_connector_id", "=",
                                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                      limit=1)

        if setu_woocommerce_product_template_id and multi_ecommerce_connector_id.active:
            request.env["setu.ecommerce.product.chain"].sudo().create_or_update_product_via_webhook(
                request_json,
                multi_ecommerce_connector_id,
                woo_api_connect)

        elif request_json.get("status") == "publish" and request_json.get(
                "type") != "variation" and multi_ecommerce_connector_id.active:
            request.env["setu.ecommerce.product.chain"].sudo().create_or_update_product_via_webhook(
                request_json,
                multi_ecommerce_connector_id,
                woo_api_connect)
        return

    @http.route("/check_webhook", csrf=False, auth="public", type="json")
    def check_webhook(self):
        request_json = request.jsonrequest
        headers = request.httprequest.headers
        event = headers.get("X-Wc-Webhook-Event")
        return

    @http.route(["/setu_create_customer_webhook_woo_odoo", "/setu_update_customer_webhook_woo_odoo"], csrf=False,
                auth="public", type="json")
    def create_customer_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        res_partner_id = request.env['res.partner'].sudo().get_woocommerce_partner(multi_ecommerce_connector_id,
                                                                                   request_json)

        is_billing_address = any(request_json.get('billing').values())
        is_shipping_address = any(request_json.get('shipping').values())
        if not res_partner_id and not is_billing_address:
            request.env['res.partner'].sudo().prepare_create_partner_via_webhook(multi_ecommerce_connector_id,
                                                                                     request_json,
                                                                                     True if is_shipping_address else False,
                                                                                     False)

        elif res_partner_id and res_partner_id.type == 'invoice' and not is_billing_address:
            request.env['res.partner'].sudo().find_res_partner_with_address_details(request_json, res_partner_id,
                                                                                    multi_ecommerce_connector_id,
                                                                                    is_shipping_address)
        else:
            request.env['setu.woocommerce.customer.chain'].sudo().create_or_update_customer_via_webhook(
                multi_ecommerce_connector_id, request_json, "webhook")
        return

    @http.route("/setu_create_coupon_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def create_coupon_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        request.env["setu.woocommerce.coupon.chain"].sudo().create_woocommerce_coupon_chain_via_webhook(request_json,
                                                                                                        multi_ecommerce_connector_id)

    @http.route("/setu_update_coupon_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def update_coupon_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        request.env["setu.woocommerce.coupon.chain"].sudo().create_woocommerce_coupon_chain_via_webhook(request_json,
                                                                                                        multi_ecommerce_connector_id)

    @http.route("/setu_delete_coupon_webhook_woo_odoo", csrf=False, auth="public", type="json")
    def delete_coupon_webhook(self):
        request_json, multi_ecommerce_connector_id = self.fetch_multi_ecommerce_connector_details()
        woocommerce_coupons_id = request.env["setu.woocommerce.coupons"].sudo().search(
            ["&", "|", ('woocommerce_coupon_id', '=', request_json.get("id")), ('code', '=', request_json.get("code")),
             ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
        if woocommerce_coupons_id and multi_ecommerce_connector_id.active:
            woocommerce_coupons_id.write({'active': False})
        return
