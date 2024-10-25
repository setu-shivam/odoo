# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)

    def partner_search_by_email(self, email):
        partner_id = self.search([('email', '=ilike', email), ('customer_rank', '>', 0)], limit=1)
        return partner_id

    def find_odoo_country(self, country_info):
        res_country_obj = self.env['res.country']
        res_country_id = res_country_obj.search(
            ['|', ('code', '=ilike', country_info), ('name', '=ilike', country_info)], limit=1)
        return res_country_id

    def find_odoo_country_state(self, country_info, state_info, country_id=False):
        res_country_state_obj = self.env['res.country.state']
        if not country_id:
            country_id = self.find_odoo_country(country_info)
        else:
            country_id = country_id
        state_id = res_country_state_obj.search(['|', ('name', '=ilike', state_info), ('code', '=ilike', state_info),
                                                 ('country_id', '=', country_id and country_id.id or False)], limit=1)
        if not state_id and country_id:
            if state_info:
                state_id = res_country_state_obj.create(
                    {'name': state_info, 'code': state_info, 'country_id': country_id.id})
            else:
                state_id = res_country_state_obj
        return state_id

    def _available_erp_partner(self, partner_vals, address_list, extra_where_clause=[]):
        domain = []
        if address_list and partner_vals:
            if extra_where_clause:
                domain += extra_where_clause
            for key in address_list:
                if not partner_vals.get(key):
                    continue
                (key in partner_vals) and domain.append((key, '=', partner_vals.get(key)))
            return domain and self.search(domain, limit=1) or False
        return False

    def search_partner_by_email_phone(self, res_partner, email, phone):
        if email:
            res_partner = self.search([("email", "=", email)], limit=1)
        if not res_partner and phone:
            res_partner = self.search([("phone", "=", phone)], limit=1)
        if res_partner and res_partner.parent_id:
            res_partner = res_partner.parent_id
        return res_partner

    def update_partner_name_vals(self, partner_vals, first_name, last_name, email, phone):
        name = ("%s %s" % (first_name, last_name)).strip()
        if name == "":
            if email:
                name = email
            elif phone:
                name = phone
        partner_vals.update({"name": name})
        return partner_vals
