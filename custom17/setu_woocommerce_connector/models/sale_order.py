# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import ast
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_woocommerce_order_status(self):
        for order_id in self:
            if order_id.multi_ecommerce_connector_id:
                pickings = order_id.picking_ids.filtered(lambda x: x.state != "cancel")
                if pickings:
                    outgoing_picking = pickings.filtered(lambda x: x.location_dest_id.usage == "customer")
                    if all(outgoing_picking.mapped("is_delivery_updated_in_woocommerce")):
                        order_id.is_order_updated_in_woocommerce = True
                        continue
                if order_id.state != 'draft':
                    move_ids = self.env["stock.move"].search(
                        [("picking_id", "=", False), ("sale_line_id", "in", order_id.order_line.ids)])
                    state = set(move_ids.mapped('state'))
                    if len(set(state)) == 1 and 'done' in set(state):
                        order_id.is_order_updated_in_woocommerce = True
                        continue
                order_id.is_order_updated_in_woocommerce = False
                continue
            order_id.is_order_updated_in_woocommerce = False

    def _search_ecommerce_order_ids(self, operator, value):
        query = """select so.id from stock_picking sp inner join sale_order so on so.procurement_group_id=sp.group_id 
        inner join stock_location on stock_location.id = sp.location_dest_id and stock_location.usage='customer' 
        where sp.is_delivery_updated_in_woocommerce %s true and sp.state != 'cancel' """ % (
            operator)
        if operator == '=':
            query += """union all select so.id from sale_order as so inner join sale_order_line as sl on sl.order_id 
            = so.id inner join stock_move as sm on sm.sale_line_id = sl.id  where sm.picking_id is NULL and sm.state 
            = 'done' and so.multi_ecommerce_connector_id notnull """

        self._cr.execute(query)
        results = self._cr.fetchall()
        order_ids = []
        for result_tuple in results:
            order_ids.append(result_tuple[0])
        order_ids = list(set(order_ids))
        return [('id', 'in', order_ids)]

    is_order_updated_in_woocommerce = fields.Boolean(string="Order Updated In WooCommerce",
                                                     compute="_get_woocommerce_order_status",
                                                     search="_search_ecommerce_order_ids", copy=False)
    is_order_cancelled_in_woocommerce = fields.Boolean(string="Order Cancelled In WooCommerce", default=False,
                                                       copy=False)
    ecommerce_order_id = fields.Char(string="WooCommerce Order Reference", help="WooCommerce Order Reference",
                                     copy=False)
    woocommerce_order_number = fields.Char(string="WooCommerce Order Number", help="WooCommerce Order Number",
                                           copy=False)
    woocommerce_transaction_id = fields.Char(string="Order Transaction ID", help="WooCommerce Order Transaction Id",
                                             copy=False)
    woocommerce_order_status = fields.Selection([("pending", "Pending"), ("processing", "Processing"),
                                                 ("on-hold", "On hold"), ("completed", "Completed"),
                                                 ("cancelled", "Cancelled"), ("refunded", "Refunded")], copy=False,
                                                tracking=True)
    setu_woocommerce_payment_gateway_id = fields.Many2one("setu.woocommerce.payment.gateway", string="Payment Gateway")
    setu_woocommerce_coupons_ids = fields.Many2many("setu.woocommerce.coupons", 'sale_order_woocommerce_coupons_rel',
                                                    'sale_order_id', 'woocommerce_coupons_id', string="Coupons",
                                                    copy=False)

    # ===========================================================================
    # Import Woocommerce Sale Order Process via Chain
    # ===========================================================================

    @api.model
    def process_import_sale_order_chain_based(self, order_process_chain_ids, process_history_id):
        woo_coupon_obj = self.env["setu.woocommerce.coupons"]
        setu_woocommerce_sale_process_configuration_obj = self.env["setu.woocommerce.sale.process.configuration"]
        setu_woocommerce_payment_gateway_obj = self.env["setu.woocommerce.payment.gateway"]
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_sale_order_automation_obj = self.env["setu.sale.order.automation"]
        delivery_carrier_obj = self.env["delivery.carrier"]

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        new_orders = self
        multi_ecommerce_connector_id = False
        commit_count = 0
        woo_taxes = {}
        for order_process_chain_line_id in order_process_chain_ids:
            commit_count += 1
            if commit_count == 5:
                order_process_chain_line_id.setu_ecommerce_order_chain_id.is_chain_in_process = True
                self._cr.commit()
                commit_count = 0
            if multi_ecommerce_connector_id != order_process_chain_line_id.multi_ecommerce_connector_id:
                multi_ecommerce_connector_id = order_process_chain_line_id.multi_ecommerce_connector_id

            if not order_process_chain_line_id.order_chain_line_data:
                order_process_chain_line_id.state = "fail"
                continue

            order_data_dict = ast.literal_eval(order_process_chain_line_id.order_chain_line_data)
            order_process_chain_line_id.last_order_chain_line_process_date = fields.Datetime.now()
            existing_order_id = self.search([("multi_ecommerce_connector_id", "=",
                                              multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                                             ("ecommerce_order_id", "=", order_data_dict.get("id")),
                                             ("woocommerce_order_number", "=", order_data_dict.get("number"))]).ids

            if not existing_order_id:
                existing_order_id = self.search([("multi_ecommerce_connector_id", '=',
                                                  multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                                                 ("client_order_ref", "=", order_data_dict.get("number"))]).ids

            if existing_order_id:
                order_process_chain_line_id.state = "done"
                continue

            if order_data_dict.get("transaction_id"):
                woocommerce_financial_status = "paid"
            elif order_data_dict.get("date_paid") and order_data_dict.get(
                    "payment_method") != "cod" and order_data_dict.get("status") == "processing":
                woocommerce_financial_status = "paid"
            else:
                woocommerce_financial_status = "not_paid"

            payment_gateway_id = self.create_or_update_woocommerce_payment_gateway(multi_ecommerce_connector_id,
                                                                                   order_data_dict)
            no_payment_gateway = self.check_order_payment_details(order_data_dict)

            if payment_gateway_id:
                woocommerce_sale_process_configuration_id = setu_woocommerce_sale_process_configuration_obj.search([(
                    "multi_ecommerce_connector_id",
                    "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                    (
                        "woocommerce_financial_status",
                        "=",
                        woocommerce_financial_status),
                    (
                        "setu_woocommerce_payment_gateway_id",
                        "=",
                        payment_gateway_id and payment_gateway_id.id)],
                    limit=1)

            elif no_payment_gateway:
                payment_gateway_id = setu_woocommerce_payment_gateway_obj.search([("code", "=", "no_payment_method"), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
                woocommerce_sale_process_configuration_id = setu_woocommerce_sale_process_configuration_obj.search([(
                    "multi_ecommerce_connector_id",
                    "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                    (
                        "woocommerce_financial_status",
                        "=",
                        woocommerce_financial_status),
                    (
                        "setu_woocommerce_payment_gateway_id",
                        "=",
                        payment_gateway_id and payment_gateway_id.id)],
                    limit=1)
            else:
                message = """- Current payment method is not available in system. Please check appropriate 
                WooCommerce response. """
                setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                            order_process_chain_line_id,
                                                                                            process_history_id)
                order_process_chain_line_id.write({"state": "fail"})
                continue

            if not woocommerce_sale_process_configuration_id:
                message = """
                The system tries to find ‘Workflow Automation’ based on a combination of ‘Payment Gateway’ 
                (such as Manual, Credit Card, Paypal, etc.) and ‘WooCommerce Financial Status’ 
                (such as Paid, Pending, etc.). For this order, Payment Gateway is %s and Financial Status is 
                %s which is not configured.
                You can navigate to WooCommerce Integration > ‘Order Process Setup’ and configure it.	
                """ % (
                    order_data_dict.get("payment_method"), woocommerce_financial_status
                )
                setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                            order_process_chain_line_id,
                                                                                            process_history_id)
                continue

            setu_sale_order_automation_id = woocommerce_sale_process_configuration_id.setu_sale_order_automation_id
            if not setu_sale_order_automation_id.picking_policy:
                message = """
                    ‘Workflow Automation’ must be set up in order to import the order.  
                    You can configure it from WooCommerce Configuration > Order Process Setup
                """
                setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                            order_process_chain_line_id,
                                                                                            process_history_id)
                continue

            partner_id, partner_shipping_id, partner_billing_id = self.prepare_woocommerce_customer_and_addresses(
                order_data_dict, multi_ecommerce_connector_id, order_process_chain_line_id, process_history_id, )

            if not partner_id:
                continue

            order_vals = self.prepare_woocommerce_order_vals(order_data_dict, multi_ecommerce_connector_id, partner_id,
                                                             partner_shipping_id, partner_billing_id,
                                                             setu_sale_order_automation_id, payment_gateway_id)
            order_vals.update({"payment_term_id": woocommerce_sale_process_configuration_id.account_payment_term_id.id})
            sale_order_id = self.create(order_vals)

            tax_included = order_data_dict.get("prices_include_tax")

            order_lines, woo_taxes = self.create_woocommerce_order_line(order_process_chain_line_id,
                                                                        order_data_dict.get("line_items"),
                                                                        sale_order_id, tax_included, process_history_id,
                                                                        woo_taxes)

            if not order_lines:
                sale_order_id.sudo().unlink()
                order_process_chain_line_id.state = "fail"
                continue

            for shipping_line in order_data_dict.get("shipping_lines"):
                delivery_method = shipping_line.get("method_title")
                if delivery_method:
                    carrier_id = delivery_carrier_obj.search([("woocommerce_delivery_code", "=", delivery_method)],
                                                             limit=1)
                    if not carrier_id:
                        carrier_id = delivery_carrier_obj.search([("name", "=", delivery_method)], limit=1)
                    if not carrier_id:
                        carrier_id = delivery_carrier_obj.search(["|", ("name", "ilike", delivery_method), (
                            "woocommerce_delivery_code", "ilike", delivery_method)], limit=1)
                    if not carrier_id:
                        carrier_id = delivery_carrier_obj.create(
                            {"name": delivery_method, "woocommerce_delivery_code": delivery_method,
                             "fixed_price": shipping_line.get("total"),
                             "product_id": multi_ecommerce_connector_id.shipping_product_id.id})

                    shipping_product = carrier_id.product_id
                    sale_order_id.write({"carrier_id": carrier_id.id})
                    taxes = []
                    if woo_taxes:
                        line_taxes = shipping_line.get("taxes")
                        for tax in line_taxes:
                            taxes.append(woo_taxes[tax["id"]])

                    if tax_included:
                        total_shipping = float(shipping_line.get("total", 0.0)) + float(
                            shipping_line.get("total_tax", 0.0))
                    else:
                        total_shipping = float(shipping_line.get("total", 0.0))
                    self.prepare_create_woocommerce_order_line_vals(shipping_line.get("id"), shipping_product, 1,
                                                                    sale_order_id, total_shipping, taxes, tax_included,
                                                                    multi_ecommerce_connector_id, True)
            for fee_line in order_data_dict.get("fee_lines"):
                if tax_included:
                    total_fee = float(fee_line.get("total", 0.0)) + float(fee_line.get("total_tax", 0.0))
                else:
                    total_fee = float(fee_line.get("total", 0.0))
                if total_fee:
                    taxes = []
                    if woo_taxes:
                        line_taxes = fee_line.get("taxes")
                        for tax in line_taxes:
                            taxes.append(woo_taxes[tax["id"]])
                    self.prepare_create_woocommerce_order_line_vals(
                        fee_line.get("id"),
                        multi_ecommerce_connector_id.custom_service_product_id,
                        1, sale_order_id, total_fee, taxes, tax_included,
                        multi_ecommerce_connector_id)

            woocommerce_coupons_lst = []
            for coupon_line_id in order_data_dict.get("coupon_lines"):
                for coupon_meta_dict in coupon_line_id.get('meta_data'):
                    coupon_code = coupon_meta_dict.get('value').get('code')
                    woo_coupon_id = coupon_meta_dict.get('value').get('id')
                    coupon_id = woo_coupon_obj.search([("code", "=", coupon_code), (
                        "multi_ecommerce_connector_id", "=",
                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                                                       ('is_coupon_exported_in_woocommerce', '=', True),
                                                       ('woocommerce_coupon_id', '=', woo_coupon_id)])
                    if coupon_id:
                        woocommerce_coupons_lst.append(coupon_id.id)
                    else:
                        message = "The coupon {0} could not be added as it is not imported in odoo.".format(
                            coupon_line_id["code"])
                        sale_order_id.message_post(body=message)
            sale_order_id.setu_woocommerce_coupons_ids = [(6, 0, woocommerce_coupons_lst)]

            if order_data_dict.get('status') == 'completed':
                sale_order_id.setu_sale_order_automation_id.automated_confirm_shipped_order(sale_order_id)
            else:
                setu_sale_order_automation_obj.sale_order_automation(sale_order_id.setu_sale_order_automation_id.id,
                                                                     sale_order_id.ids)
            new_orders += sale_order_id
            order_process_chain_line_id.write({"sale_order_id": sale_order_id.id, "state": "done"})
        order_process_chain_ids.setu_ecommerce_order_chain_id.is_chain_in_process = False
        return new_orders

    @api.model
    def create_or_update_woocommerce_payment_gateway(self, multi_ecommerce_connector_id, order_dict):
        setu_woocommerce_payment_gateway_obj = self.env["setu.woocommerce.payment.gateway"]

        code = order_dict.get("payment_method", "")
        name = order_dict.get("payment_method_title", "")

        if not code:
            return False

        woocommerce_payment_gateway_id = setu_woocommerce_payment_gateway_obj.search([("code", "=", code), (
            "multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                                                                     limit=1)
        if woocommerce_payment_gateway_id:
            woocommerce_payment_gateway_id.name = name
        else:
            woocommerce_payment_gateway_id = setu_woocommerce_payment_gateway_obj.create(
                {"code": code, "name": name,
                 "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
        return woocommerce_payment_gateway_id

    def prepare_woocommerce_order_vals(self, order_dict, multi_ecommerce_connector_id, partner_id, partner_shipping_id,
                                       partner_billing_id, sale_order_automation_id, woocommerce_payment_gateway_id):

        order_date = order_dict.get("date_created_gmt")

        price_list_id = self.search_woocommerce_order_price_list(order_dict, multi_ecommerce_connector_id)

        order_vals = {"partner_id": partner_id.ids[0],
                      "partner_shipping_id": partner_shipping_id.ids[0],
                      "partner_invoice_id": partner_billing_id.ids[0],
                      "warehouse_id": multi_ecommerce_connector_id.odoo_warehouse_id.id,
                      "company_id": multi_ecommerce_connector_id.odoo_company_id.id,
                      "pricelist_id": price_list_id and price_list_id.id,
                      "date_order": order_date.replace("T", " "),
                      "state": "draft"}

        woocommerce_order_vals = self.preparation_of_sale_order_values(order_vals)

        woo_order_number = order_dict.get("number")
        woocommerce_order_vals.update({
            "note": order_dict.get("customer_note"),
            "ecommerce_order_id": order_dict.get("id"),
            "woocommerce_order_status": order_dict.get("status"),
            "woocommerce_transaction_id": order_dict.get("transaction_id", ""),
            "woocommerce_order_number": woo_order_number,
            "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
            "team_id": multi_ecommerce_connector_id.crm_team_id.id if multi_ecommerce_connector_id.crm_team_id else False,
            "picking_policy": sale_order_automation_id and sale_order_automation_id.picking_policy,
            "setu_sale_order_automation_id": sale_order_automation_id and sale_order_automation_id.id,
            "setu_woocommerce_payment_gateway_id": woocommerce_payment_gateway_id.id if woocommerce_payment_gateway_id else False,
            "partner_shipping_id": partner_shipping_id.ids[0],
            "client_order_ref": woo_order_number})

        if not multi_ecommerce_connector_id.is_use_odoo_order_prefix:
            if multi_ecommerce_connector_id.order_prefix:
                name = "%s_%s" % (multi_ecommerce_connector_id.order_prefix, woo_order_number)
            else:
                name = woo_order_number
            woocommerce_order_vals.update({"name": name})
        return woocommerce_order_vals

    def search_woocommerce_order_price_list(self, order_dict, multi_ecommerce_connector_id):
        currency_obj = self.env["res.currency"]
        product_price_list_obj = self.env['product.pricelist']
        order_currency = order_dict.get("currency")

        currency_id = currency_obj.search([('name', '=', order_currency)], limit=1)
        if not currency_id:
            currency_id = currency_obj.search([('name', '=', order_currency), ('active', '=', False)], limit=1)
            currency_id.write({'active': True})
        if multi_ecommerce_connector_id.odoo_pricelist_id.currency_id.id == currency_id.id:
            return multi_ecommerce_connector_id.odoo_pricelist_id
        odoo_pricelist_id = product_price_list_obj.search([('currency_id', '=', currency_id.id)], limit=1)
        if odoo_pricelist_id:
            return odoo_pricelist_id

        odoo_pricelist_id = product_price_list_obj.create(
            {'name': currency_id.name, 'currency_id': currency_id.id,
             'company_id': multi_ecommerce_connector_id.odoo_company_id.id})
        return odoo_pricelist_id

    @api.model
    def create_woocommerce_tax(self, tax, tax_included, multi_ecommerce_connector_id):
        account_tax_obj = self.env["account.tax"]
        title = tax["name"]
        rate = tax["rate"]

        if tax_included:
            name = "%s (%s %% included)" % (title, rate)
        else:
            name = "%s (%s %% excluded)" % (title, rate)

        odoo_tax = account_tax_obj.create(
            {"name": name, "amount": float(rate), "type_tax_use": "sale", "price_include": tax_included,
             "company_id": multi_ecommerce_connector_id.odoo_company_id.id})
        odoo_tax.mapped("invoice_repartition_line_ids").write(
            {"account_id":multi_ecommerce_connector_id.default_invoice_tax_account_id.id})
        # multi_ecommerce_connector_id.invoice_tax_account_id.id
        odoo_tax.mapped("refund_repartition_line_ids").write(
            {"account_id":multi_ecommerce_connector_id.default_credit_tax_account_id.id })
        # multi_ecommerce_connector_id.credit_note_tax_account_id.id
        return odoo_tax

    @api.model
    def create_and_find_woocommerce_taxes(self, taxes, tax_included, multi_ecommerce_connector_id):
        tax_obj = self.env["account.tax"]
        tax_ids = []
        for tax in taxes:
            rate = float(tax.get("rate"))
            tax_id = tax_obj.search(
                [("price_include", "=", tax_included), ("type_tax_use", "=", "sale"), ("amount", "=", rate),
                 ("company_id", "=", multi_ecommerce_connector_id.odoo_company_id.id)], limit=1)
            if not tax_id:
                tax_id = self.create_woocommerce_tax(tax, tax_included, multi_ecommerce_connector_id)
            if tax_id:
                tax_ids.append(tax_id.id)
        return tax_ids

    @api.model
    def prepare_create_woocommerce_order_line_vals(self, line_id, product, quantity, order, price, taxes, tax_included,
                                                   multi_ecommerce_connector_id, is_shipping=False):
        sale_order_line_obj = self.env["sale.order.line"]
        line_vals = {"name": product.name,
                     "product_id": product.id,
                     "product_uom": product.uom_id.id if product.uom_id else False,
                     "order_id": order.id,
                     "order_qty": quantity,
                     "price_unit": price,
                     "is_delivery": is_shipping,
                     "company_id": multi_ecommerce_connector_id.odoo_company_id.id}
        woocommerce_order_line_vals = sale_order_line_obj.preparation_of_sale_order_line_vals(line_vals)

        if multi_ecommerce_connector_id.order_odoo_tax_behavior == "follow_e_commerce_tax_create_odoo":
            tax_ids = self.create_and_find_woocommerce_taxes(taxes, tax_included, multi_ecommerce_connector_id)
            woocommerce_order_line_vals.update({"tax_id": [(6, 0, tax_ids)]})

        woocommerce_order_line_vals.update({"woocommerce_order_line_id": line_id})
        return sale_order_line_obj.create(woocommerce_order_line_vals)

    def prepare_woocommerce_customer_and_addresses(self, order_response, multi_ecommerce_connector_id, chain_line_id,
                                                   process_history_id):
        res_partner_obj = self.env["res.partner"]

        partner = order_response.get("billing") and res_partner_obj.create_main_res_partner_woocommerce(
            order_response.get("billing"), multi_ecommerce_connector_id, False, process_history_id)
        if not partner:
            if chain_line_id:
                chain_line_id.write({"state": "fail", "last_order_chain_line_process_date": datetime.now()})
            return False, False, False

        if partner.parent_id:
            partner = partner.parent_id

        invoice_address = order_response.get("billing") and res_partner_obj.create_child_woocommerce_customer(
            order_response.get("billing"), partner, "invoice") or partner
        delivery_address = order_response.get("shipping") and res_partner_obj.create_child_woocommerce_customer(
            order_response.get("shipping"), partner, "delivery") or partner

        if not partner and invoice_address and delivery_address:
            partner = invoice_address
        if not partner and not delivery_address and invoice_address:
            partner = invoice_address
            delivery_address = invoice_address
        if not partner and not invoice_address and delivery_address:
            partner = delivery_address
            invoice_address = delivery_address
        return partner, delivery_address, invoice_address

    @api.model
    def create_woocommerce_order_line(self, order_chain_line_id, order_chain_line_data, sale_order, tax_included,
                                      process_history_id, woocommerce_taxes):

        setu_process_history_line_obj = self.env['setu.process.history.line']
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        order_lines_lst = []
        for order_chain_line_dict in order_chain_line_data:
            taxes = []
            woocommerce_product_id = self.find_or_create_woocommerce_product(order_chain_line_id, order_chain_line_dict,
                                                                             process_history_id)

            if not woocommerce_product_id:
                message = "Product is not found for sale order. Please check the product for order."
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False, woocommerce_taxes

            odoo_product_id = woocommerce_product_id.odoo_product_id

            if tax_included:
                actual_unit_price = (float(order_chain_line_dict.get("subtotal_tax")) + float(
                    order_chain_line_dict.get("subtotal"))) / float(order_chain_line_dict.get("quantity"))
            else:
                actual_unit_price = float(order_chain_line_dict.get("subtotal")) / float(
                    order_chain_line_dict.get("quantity"))

            if order_chain_line_id.multi_ecommerce_connector_id.order_odoo_tax_behavior == "follow_e_commerce_tax_create_odoo":
                line_taxes = order_chain_line_dict.get("taxes")
                for tax in line_taxes:
                    if tax["id"] in woocommerce_taxes.keys():
                        taxes.append(woocommerce_taxes[tax["id"]])
                    else:
                        woo_taxes = self.get_tax_ids(sale_order.multi_ecommerce_connector_id, tax["id"],
                                                     woocommerce_taxes)
                        if tax["id"] in woo_taxes.keys():
                            taxes.append(woo_taxes[tax["id"]])
                        else:
                            message = """Tax is not found for sale order in WooCommerce Store.
                            Please verify tax details on WooCommerce"""
                            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                                  process_history_id)
                            return False, woocommerce_taxes

            multi_ecommerce_connector_id = order_chain_line_id.multi_ecommerce_connector_id
            order_line_id = self.prepare_create_woocommerce_order_line_vals(order_chain_line_dict.get("id"),
                                                                            odoo_product_id,
                                                                            order_chain_line_dict.get("quantity"),
                                                                            sale_order, actual_unit_price, taxes,
                                                                            tax_included, multi_ecommerce_connector_id)
            order_lines_lst.append(order_line_id)

            line_discount = float(order_chain_line_dict.get('subtotal')) - float(
                order_chain_line_dict.get('total')) or 0
            if line_discount > 0:
                if tax_included:
                    tax_discount = float(order_chain_line_dict.get("subtotal_tax", 0.0)) - float(
                        order_chain_line_dict.get("total_tax", 0.0)) or 0
                    line_discount = tax_discount + line_discount

                discount_line = self.prepare_create_woocommerce_order_line_vals(
                    False,
                    order_chain_line_id.setu_ecommerce_order_chain_id.multi_ecommerce_connector_id.discount_product_id,
                    1, sale_order, line_discount * -1,
                    taxes, tax_included,
                    multi_ecommerce_connector_id)
                discount_line.write({'name': 'Discount for ' + order_line_id.name})
                if order_chain_line_id.multi_ecommerce_connector_id.order_odoo_tax_behavior == 'odoo_tax':
                    discount_line.tax_id = order_line_id.tax_id

        return order_lines_lst, woocommerce_taxes

    @api.model
    def find_or_create_woocommerce_product(self, order_chain_line_id, order_chain_line_dict, process_history_id):

        setu_woocommerce_product_template_obj = self.env["setu.woocommerce.product.template"]
        multi_ecommerce_connector_id = order_chain_line_id.multi_ecommerce_connector_id

        woocommerce_product_id = order_chain_line_dict.get("variation_id") if order_chain_line_dict.get(
            "variation_id") else order_chain_line_dict.get("product_id")
        woocommerce_product_id = \
            setu_woocommerce_product_template_obj.find_odoo_product_variant(multi_ecommerce_connector_id,
                                                                            order_chain_line_dict.get("sku"),
                                                                            woocommerce_product_id)[0]

        if not woocommerce_product_id and multi_ecommerce_connector_id.is_auto_create_product:
            product_data = setu_woocommerce_product_template_obj.import_and_sync_woocommerce_product_template_erp(
                multi_ecommerce_connector_id, process_history_id, order_chain_line_dict.get("product_id"))
            setu_woocommerce_product_template_obj.fetch_and_create_woocommerce_product(product_data,
                                                                                       multi_ecommerce_connector_id,
                                                                                       process_history_id,
                                                                                       woocommerce_product_id,
                                                                                       order_chain_line_id=order_chain_line_id)
            woocommerce_product_id = \
                setu_woocommerce_product_template_obj.find_odoo_product_variant(multi_ecommerce_connector_id,
                                                                                order_chain_line_dict.get("sku"),
                                                                                woocommerce_product_id)[0]
        return woocommerce_product_id

    @api.model
    def get_tax_ids(self, multi_ecommerce_connector_id, tax_id, woo_taxes):
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        params = {"_fields": "id,name,rate,shipping", "per_page": 100, "page": 1}
        try:
            tax_api_response = woo_api_connect.get("taxes/%s" % tax_id, params=params)
            if tax_api_response.status_code != 200:
                return tax_api_response.json().get("message", tax_api_response.reason)
            tax_api_response_json_converted = tax_api_response.json()
        except:
            return woo_taxes
        woo_taxes.update({tax_api_response_json_converted["id"]: tax_api_response_json_converted})
        return woo_taxes

    @api.model
    def check_order_payment_details(self, order_data):
        total_discount = 0

        total = order_data.get("total")
        if order_data.get("coupon_lines"):
            total_discount = order_data.get("discount_total")

        if float(total) == 0 and float(total_discount) > 0:
            return True
        return False

    # ===========================================================================
    # Update Woocommerce Sale Order Process via Chain
    # ===========================================================================

    @api.model
    def update_created_sale_order_via_chain_process(self, order_process_chain_id, process_history_id):
        message = ""
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        multi_ecommerce_connector_id = order_process_chain_id.multi_ecommerce_connector_id
        order_data = ast.literal_eval(order_process_chain_id.order_chain_line_data)
        woocommerce_status = order_data.get("status")
        existing_sale_order_id = self.search([("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id),
                                              ("ecommerce_order_id", "=", order_data.get("id"))])

        if woocommerce_status == "cancelled" and existing_sale_order_id.state != "cancel":
            cancelled = existing_sale_order_id.make_cancel_sale_order_for_woocommerce()
            if not cancelled:
                message = "You can not cancel Done Delivery Order.".format(existing_sale_order_id.name)

        elif woocommerce_status == "refunded":
            refunded = existing_sale_order_id.make_sale_order_refund_for_woocommerce(order_data.get("refunds"))
            if refunded[0] == 0:

                message = "ERP Invoice not found. Please Create Invoice first then Create Refund."
            elif refunded[0] == 1:
                message = "ERP Invoice found but it is not in posted state. Please first invoice into posted" \
                          " state then after update order."
        elif woocommerce_status == "completed":
            completed = existing_sale_order_id.complete_validate_woocommerce_order()
            if isinstance(completed, bool) and not completed:
                message = "Doesn’t have sufficient quantity to validate the delivery order."
            elif not completed:
                message = "Doesn’t have enough quantity to validate the delivery order.  {0}".format(completed)

        if message:
            setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                        order_process_chain_id,
                                                                                        process_history_id)
        else:
            order_process_chain_id.state = "done"
            existing_sale_order_id.woocommerce_order_status = woocommerce_status
        return existing_sale_order_id

    def make_cancel_sale_order_for_woocommerce(self):
        if "done" in self.picking_ids.mapped("state"):
            return False
        self.action_cancel()
        return True

    def complete_validate_woocommerce_order(self):
        if not self.state == "sale":
            self.action_confirm()
        return self.complete_picking_for_woocommerce(
            self.picking_ids.filtered(lambda x: x.location_dest_id.usage == "customer"))

    def complete_picking_for_woocommerce(self, pickings):
        for picking in pickings.filtered(lambda x: x.state == "done"):
            picking.updated_in_woo = True
        for picking in pickings.filtered(lambda x: x.state != "done"):
            if picking.state != "assigned":
                if picking.move_lines.move_orig_ids:
                    completed = self.complete_picking_for_woocommerce(picking.move_lines.move_orig_ids.picking_id)
                    if not completed:
                        return False
                picking.action_assign()
                if picking.state != "assigned":
                    return False
            result = picking.button_validate()
            if isinstance(result, dict):
                if result.get("res_model", "") == "stock.immediate.transfer":
                    immediate_transfer = self.env["stock.immediate.transfer"].browse(result.get("res_id"))
                    immediate_transfer.process()
                elif result.get("res_model", "") == "stock.backorder.confirmation":
                    backorder = self.env["stock.backorder.confirmation"].browse(result.get("res_id"))
                    backorder._process()
            else:
                return result
        return True

    def make_sale_order_refund_for_woocommerce(self, refunds_data):
        if not self.invoice_ids:
            return [0]
        total_refund = 0.0
        for refund in refunds_data:
            total_refund += float(refund.get("total", 0)) * -1
        invoices = self.invoice_ids.filtered(lambda x: x.type == "out_invoice")
        for invoice in invoices:
            if not invoice.state == "posted":
                return [1]
        if self.amount_total == total_refund:
            move_reversal = self.env["account.move.reversal"].create({"refund_method": "cancel",
                                                                      "reason": "Refunded from woocommerce" if len(
                                                                          refunds_data) > 1 else refunds_data[0].get(
                                                                          "reason")})
            move_reversal.with_context({"active_model": "account.move",
                                        "active_ids": invoices.ids}).reverse_moves()
            return [True]
        return [2]

    # ===========================================================================
    # Cancel Woocommerce Sale Order Process
    # ===========================================================================

    def action_open_cancel_wizard_woocommerce(self):
        view = self.env.ref('setu_woocommerce_connector.setu_woocommerce_order_cancel_refund_wiz_form_view')
        context = dict(self._context)
        context.update({'active_model': 'sale.order', 'active_id': self.id, 'active_ids': self.ids})
        return {
            'name': _('Cancel Order In WooCommerce'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'setu.woocommerce.order.cancel.refund.wiz',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context}

    # ===========================================================================
    # Create Sale Order Via Webhook
    # ===========================================================================

    @api.model
    def process_to_create_sale_order_via_webhook(self, order_data, multi_ecommerce_connector_id, update_order=False):
        setu_woocommerce_order_chain_obj = self.env["setu.ecommerce.order.chain"]
        order_chain_id = setu_woocommerce_order_chain_obj.ecommerce_process_create_order_chain(
            multi_ecommerce_connector_id, [order_data], "webhook")
        self._cr.commit()
        if order_chain_id:
            if update_order and self.search_read(
                    [("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id),
                     ("ecommerce_order_id", "=", order_data.get("id")),
                     ("woocommerce_order_number", "=", order_data.get("number"))], ["id"]):
                order_chain_id.setu_ecommerce_order_chain_line_ids.ecommerce_process_order_chain_line(update_order)
            else:
                order_chain_id.setu_ecommerce_order_chain_line_ids.ecommerce_process_order_chain_line()
        return True

    # ===========================================================================
    # Update Order Status ERP To WooCommerce
    # ===========================================================================

    @api.model
    def update_sale_order_information_erp_to_woocommerce(self, multi_ecommerce_connector_id):
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env['setu.process.history.line']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)

        sales_order_ids = self.search([("warehouse_id", "=", multi_ecommerce_connector_id.odoo_warehouse_id.id),
                                       ("ecommerce_order_id", "!=", False),
                                       ("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id),
                                       ('is_order_updated_in_woocommerce', '!=', True)])
        count = 0
        for sale_order_id in sales_order_ids:
            count += 1
            if count > 50:
                self._cr.commit()
                count = 1
            data = {"status": "completed"}
            order_completed = False
            for picking_id in sale_order_id.picking_ids:
                if picking_id.is_delivery_updated_in_woocommerce or picking_id.state != "done" or picking_id.location_dest_id.usage != "customer":
                    continue

                order_api_response = woo_api_connect.put("orders/%s" % sale_order_id.ecommerce_order_id, data)
                if order_api_response.status_code not in [200, 201]:
                    message = "Error while updating order status %s,  %s" % (
                        sale_order_id.name, order_api_response.content)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                picking_id.write({"is_delivery_updated_in_woocommerce": True})
                order_completed = True

            if not sale_order_id.picking_ids and sale_order_id.state == "sale":
                order_api_response = woo_api_connect.put("orders/%s" % sale_order_id.ecommerce_order_id, data)

                if order_api_response.status_code not in [200, 201]:
                    message = "Error while updating order status %s,  %s" % (
                        sale_order_id.name, order_api_response.content)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                order_completed = True

            if order_completed:
                sale_order_id.woocommerce_order_status = "completed"
        return True

    def process_to_import_specific_woocommerce_orders(self, parameter, import_specific_order_ids,
                                                      multi_ecommerce_connector_id):
        setu_process_history_obj = self.env['setu.process.history']
        setu_process_history_line_obj = self.env['setu.process.history.line']

        orders_list = []
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                         multi_ecommerce_connector_id,
                                                                                         model_id)
        orders = import_specific_order_ids.split(',')
        for order in orders:
            woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
            try:
                order_api_response = woo_api_connect.get("orders/%s" % order)
            except Exception as e:
                message = "Requested resource doesn't exist or missing requested information on WooCommerce store. %s %s" % (
                    multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id)
                return False
            if order_api_response.status_code not in [200, 201]:
                message = "Invalid Request Format %s" % (str(order_api_response.content))
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            order_data_json_lst = order_api_response.json()
            orders_list.append(order_data_json_lst)
            total_pages = int(len(orders) / 10)

            if int(total_pages) > 1:
                page_data = []
                for page in range(2, int(total_pages) + 1):
                    parameter["page"] = page
                    response = woo_api_connect.get("orders", params=parameter)
                    page_data = response.json()
                orders_list += page_data
        return orders_list
