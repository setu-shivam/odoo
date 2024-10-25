# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_woocommerce_customer = fields.Boolean(string="Is WooCommerce Customer", default=False)
    woocommerce_customer_id = fields.Char(string="WooCommerce Customer ID")
    woocommerce_company_name = fields.Char(string="WooCommerce Company Name", translate=True)

    def create_main_res_partner_woocommerce(self, vals, multi_ecommerce_connector_id, customer_chain_line_id,
                                            process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']

        address_list = ["name", "street", "street2", "city", "zip", "email", "phone", "state_id", "country_id"]

        woocommerce_customer_id = vals.get("id", False)
        first_name = vals.get("first_name", "")
        last_name = vals.get("last_name", "")
        customer_email = vals.get("email", "")
        woocommerce_company_name = vals.get("company")

        if not first_name and not last_name and not customer_email:
            message = "First name, Last name and Email are not found in customer response."
            model_id = setu_process_history_line_obj.get_model_id("res.partner")
            setu_process_history_line_obj.woocommerce_create_customer_process_history_line(message, model_id,
                                                                                           customer_chain_line_id,
                                                                                           process_history_id)
            return False

        name = ""
        if first_name:
            name = "%s" % first_name
        if last_name:
            name += " %s" % last_name if name else "%s" % last_name
        if not name and customer_email:
            name = customer_email

        if woocommerce_customer_id:
            partner_id = self.find_existing_woocommerce_customer(woocommerce_customer_id, multi_ecommerce_connector_id)
            if partner_id:
                return partner_id

        if customer_email:
            partner_id = self.partner_search_by_email(customer_email)
            if partner_id:
                if not (partner_id.is_woocommerce_customer and partner_id.is_woocommerce_customer):
                    partner_id.write({"is_woocommerce_customer": True,
                                      "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                                      "woocommerce_customer_id": woocommerce_customer_id})
                    return partner_id

        partner_vals = self.prepare_customer_create_woocommerce_vals(vals)
        if woocommerce_company_name:
            address_list.append("company_name")
            partner_vals.update({"company_name": woocommerce_company_name})

        existing_partner_id = self._available_erp_partner(partner_vals, address_list,
                                                          [("parent_id", "=", False), ("type", "=", "contact")])
        if existing_partner_id:
            return existing_partner_id

        partner_vals.update({"name": name,
                             "woocommerce_customer_id": woocommerce_customer_id,
                             "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                             "email": customer_email,
                             "customer_rank": 1,
                             "is_woocommerce_customer": True,
                             "woocommerce_company_name": woocommerce_company_name,
                             "type": "contact"})

        partner_id = self.create(partner_vals)
        return partner_id

    def prepare_customer_create_woocommerce_vals(self, vals):
        first_name = vals.get("first_name")
        last_name = vals.get("last_name")
        name = "%s %s" % (first_name, last_name)

        postcode = vals.get("postcode")
        state_code = vals.get("state")
        country_code = vals.get("country")
        country_id = self.find_odoo_country(country_code)
        state_id = self.find_odoo_country_state(country_code, state_code)
        partner_vals = {"email": vals.get("email") or False, "name": name,
                        "phone": vals.get("phone"), "street": vals.get("address_1"),
                        "street2": vals.get("address_2"), "city": vals.get("city"),
                        "zip": postcode, "state_id": state_id and state_id.id or False,
                        "country_id": country_id and country_id.id or False, "is_company": False}

        return partner_vals

    def create_child_woocommerce_customer(self, woocommerce_customer_data, parent_partner, partner_type="contact"):

        first_name = woocommerce_customer_data.get("first_name")
        last_name = woocommerce_customer_data.get("last_name")

        if not first_name and not last_name:
            return False

        company_name = woocommerce_customer_data.get("company")
        partner_vals = self.prepare_customer_create_woocommerce_vals(woocommerce_customer_data)
        address_list = ["name", "street", "street2", "city", "zip", "email", "phone", "state_id", "country_id"]

        if company_name:
            address_list.append("company_name")
            partner_vals.update({"company_name": company_name})

        if partner_type == "contact":
            partner_vals.update({"type": "contact"})

        existing_partner_id = self._available_erp_partner(partner_vals, address_list,
                                                          [("parent_id", "=", parent_partner.id),
                                                           ("type", "=", parent_partner.type)])

        if not existing_partner_id:
            existing_partner_id = self._available_erp_partner(partner_vals, address_list,
                                                              [("parent_id", "=", parent_partner.id)])

        if existing_partner_id:
            return existing_partner_id

        partner_vals.update({"type": partner_type, "parent_id": parent_partner.id,
                             "woocommerce_customer_id": woocommerce_customer_data.get("id", False),
                             "multi_ecommerce_connector_id": parent_partner.multi_ecommerce_connector_id and parent_partner.multi_ecommerce_connector_id.id,
                             "is_woocommerce_customer": True})

        new_create_partner_id = self.create(partner_vals)

        company_name and new_create_partner_id.write({"company_name": company_name})
        return new_create_partner_id

    def find_existing_woocommerce_customer(self, woocommerce_customer_id, multi_ecommerce_connector_id):
        partner_id = self.search([("woocommerce_customer_id", "=", woocommerce_customer_id), (
            "multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                 limit=1)
        if partner_id:
            return partner_id

    def get_woocommerce_partner(self, multi_ecommerce_connector_id, customer_dict):
        odoo_partner_id = self.search([('woocommerce_customer_id', '=', customer_dict.get('id')), (
            'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)]) if customer_dict.get(
            'id') else False
        if not odoo_partner_id:
            odoo_partner_id = self.search([('email', '=', customer_dict.get('email')), ('parent_id', '=', False)],
                                          limit=1)
        return odoo_partner_id

    def prepare_create_partner_via_webhook(self, multi_ecommerce_connector_id, response, is_shipping_address,
                                           partner_id=False):
        if not partner_id:
            partner_vals = {
                'name': response.get('username'),
                'email': response.get('email'),
                'customer_rank': 1,
                'is_woocommerce_customer': True,
                'type': 'invoice',
                'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                'company_type': 'company'
            }
            partner_id = self.create(partner_vals)
        if partner_id:
            if is_shipping_address:
                parent_id = partner_id
                if partner_id.parent_id:
                    parent_id = partner_id.parent_id
                shipping_partner_id = self.env['res.partner'].create_child_woocommerce_customer(
                    response.get('shipping'), parent_id, partner_type='delivery')
                if not shipping_partner_id.parent_id:
                    shipping_partner_id.write({'parent_id': parent_id.id})
        return True

    def find_res_partner_with_address_details(self, response, partner_id, is_shipping_address):
        if partner_id:
            if is_shipping_address:
                parent_id = partner_id
                if partner_id.parent_id:
                    parent_id = partner_id.parent_id
                shipping_partner_id = self.env['res.partner'].create_child_woocommerce_customer(
                    response.get('shipping'), parent_id, partner_type='delivery')
                if not shipping_partner_id.parent_id:
                    shipping_partner_id.write({'parent_id': partner_id.id})
        return True
