import base64
import hashlib
import json
import logging
from datetime import datetime

import pytz
import requests
from odoo import fields, models, api

from .img_file_upload import ImageUploader

_logger = logging.getLogger("ProductTemplateVariant")


class SetuWooCommerceProductTemplate(models.Model):
    _name = 'setu.woocommerce.product.template'
    _description = 'WooCommerce Product Template'

    active = fields.Boolean(string="Active", default=True)
    is_product_template_exported_in_woocommerce = fields.Boolean(string="Synced", default=False)
    is_product_template_published_website = fields.Boolean(string='Available in the website', copy=False)
    is_product_template_taxable = fields.Boolean(string="Taxable", default=True)
    name = fields.Char(string="Name", translate=True)
    woocommerce_product_tmpl_id = fields.Char(string="Woo Template ID",
                                              help="Unique identifier for the resource.")
    product_tmpl_description = fields.Html(string="Description", translate=True, help="Product description")
    product_short_tmpl_description = fields.Html(string="Short Description", translate=True,
                                                 help="Product short description.")
    product_tmpl_created_at = fields.Datetime(string="Created At", help="The date the product was created")
    product_tmpl_modified_at = fields.Datetime(string="Last Modified At", help="The date the product was last modified")
    total_variants_in_woocommerce = fields.Integer("Total Variants in Woo", default=0)
    total_sync_variants = fields.Integer("Total Sync Variants", compute="_compute_total_sync_variants", store=True)
    product_tmpl_type = fields.Selection(
        [('simple', 'Simple'), ('variable', 'Variable'), ('bundle', 'Bundle'), ('grouped', 'Grouped'),
         ('external', 'External')], string='Woo Product Type')
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False, required=True)
    odoo_product_tmpl_id = fields.Many2one("product.template", string="Product Template",# required=True,
                                           ondelete="cascade")
    setu_woocommerce_product_image_ids = fields.One2many("setu.woocommerce.product.image",
                                                         "setu_woocommerce_product_template_id", string="Product Image")
    setu_woocommerce_product_variant_ids = fields.One2many("setu.woocommerce.product.variant",
                                                           "setu_woocommerce_product_template_id",
                                                           string="Products Variant")
    setu_woocommerce_product_tag_ids = fields.Many2many('setu.woocommerce.product.tags',
                                                        'woocommerce_product_template_tags_rel',
                                                        'woocommerce_product_template_id', 'woocommerce_product_tag_id',
                                                        string=" Product Tags")
    setu_woocommerce_product_category_ids = fields.Many2many('setu.woocommerce.product.category',
                                                             'woocommerce_tmpl_product_categ_rel',
                                                             'woocommerce_product_category_id',
                                                             'woocommerce_product_template_id',
                                                             string="Products Categories")

    @api.depends('setu_woocommerce_product_variant_ids.is_product_variant_exported_in_woocommerce',
                 'setu_woocommerce_product_variant_ids.woocommerce_product_variant_id')
    def _compute_total_sync_variants(self):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        for woocommerce_template_id in self:
            woocommerce_product_variant_ids = setu_woocommerce_product_variant_obj.search(
                [('id', 'in', woocommerce_template_id.setu_woocommerce_product_variant_ids.ids),
                 ('is_product_variant_exported_in_woocommerce', '=', True),
                 ('woocommerce_product_variant_id', '!=', False)])
            woocommerce_template_id.total_sync_variants = len(woocommerce_product_variant_ids)

    @api.depends("setu_woocommerce_product_variant_ids")
    def _compute_product_tmpl_type(self):
        for woocommerce_template_id in self:
            if len(woocommerce_template_id.setu_woocommerce_product_variant_ids) > 1:
                woocommerce_template_id.product_tmpl_type = "variable"
            else:
                woocommerce_template_id.product_tmpl_type = "simple"

    @api.onchange("odoo_product_tmpl_id")
    def _onchange_product_tmpl(self):
        for woocommerce_template_id in self:
            woocommerce_template_id.name = woocommerce_template_id.odoo_product_tmpl_id.name

    def write(self, vals):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        if 'active' in vals.keys():
            for woocommerce_template_id in self:
                woocommerce_template_id.setu_woocommerce_product_variant_ids and woocommerce_template_id.setu_woocommerce_product_variant_ids.write(
                    {'active': vals.get('active')})
                if vals.get('active'):
                    woocommerce_variant_ids = setu_woocommerce_product_variant_obj.search([
                        ('setu_woocommerce_product_template_id', '=',
                         woocommerce_template_id and woocommerce_template_id.id),
                        ('multi_ecommerce_connector_id', '=', woocommerce_template_id.multi_ecommerce_connector_id.id),
                        ('active', '=', False)])
                    woocommerce_variant_ids and woocommerce_variant_ids.write({'active': vals.get('active')})
        res = super(SetuWooCommerceProductTemplate, self).write(vals)
        return res

    def process_to_prepare_batch_data(self, data):
        batches = []
        start, end = 0, 50
        if len(data) > 50:
            while True:
                data_batch = data[start:end]
                if not data_batch:
                    break
                temp = end + 50
                start, end = end, temp
                if data_batch:
                    batches.append(data_batch)
        else:
            batches.append(data)
        return batches

    # ===============================================================================
    # Create WooCommerce Product Template & Variant Base On the Chain Process
    # ===============================================================================

    @api.model
    def fetch_and_create_woocommerce_product(self, product_chain_line_ids, multi_ecommerce_connector_id,
                                             process_history_id, is_skip_update_existing_product=False,
                                             order_chain_line_id=False):
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        product_attribute_obj = self.env["product.attribute"]
        product_attribute_value_obj = self.env["product.attribute.value"]
        product_product_obj = self.env["product.product"]
        product_template_obj = self.env['product.template']

        chain_count = 0
        is_sync_product_category_and_tags = False

        model_id = setu_process_history_line_obj.get_model_id(self._name)

        is_import_with_image = multi_ecommerce_connector_id.is_sync_woocommerce_product_images

        if order_chain_line_id:
            setu_woocommerce_product_attributes_obj.fetch_and_create_product_attributes_woocommerce_to_erp(
                multi_ecommerce_connector_id)

        for product_chain_line_id in product_chain_line_ids:
            if chain_count == 10:
                if not order_chain_line_id:
                    product_chain_id = product_chain_line_id and product_chain_line_id.setu_ecommerce_product_chain_id or False
                    if product_chain_id:
                        product_chain_id.is_chain_in_process = True
                self._cr.commit()
                chain_count = 0
            chain_count += 1

            line_failed = False
            need_to_template_update = False
            need_to_template_image_update = False
            if order_chain_line_id:
                woocommerce_product_data = product_chain_line_id
                is_sync_product_category_and_tags = True
            else:
                if product_chain_line_id.setu_ecommerce_product_chain_id.record_created_from == "webhook":
                    is_sync_product_category_and_tags = True
                woocommerce_product_data = json.loads(product_chain_line_id.product_chain_line_data)

            woo_tmpl_id = woocommerce_product_data.get("id")
            woocommerce_product_template_id = self.with_context(active_test=False).search(
                [("woocommerce_product_tmpl_id", "=", woo_tmpl_id), (
                    "multi_ecommerce_connector_id", "=",
                    multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                limit=1)

            template_title = woocommerce_product_data.get("name")

            prepare_template_vals = {"name": template_title,
                                     "woocommerce_product_tmpl_id": woo_tmpl_id,
                                     "multi_ecommerce_connector_id": multi_ecommerce_connector_id.id,
                                     "product_tmpl_modified_at": woocommerce_product_data.get("date_modified").replace(
                                         "T", " "),
                                     "product_short_tmpl_description": woocommerce_product_data.get("short_description",
                                                                                                    ""),
                                     "product_tmpl_description": woocommerce_product_data.get("description", ""),
                                     "is_product_template_published_website": True if woocommerce_product_data[
                                                                                          "status"] == "publish" else False,
                                     "is_product_template_taxable": True if woocommerce_product_data[
                                                                                "tax_status"] == "taxable" else False,
                                     # "setu_woocommerce_product_category_ids": woocommerce_product_data.get(
                                     #     "categories"),
                                     "setu_woocommerce_product_tag_ids": woocommerce_product_data.get("tags"),
                                     "total_variants_in_woocommerce": len(woocommerce_product_data["variations"]),
                                     "product_tmpl_type": woocommerce_product_data["type"],
                                     "active": True}

            if woocommerce_product_data.get("date_created"):
                prepare_template_vals.update(
                    {"product_tmpl_created_at": woocommerce_product_data.get("date_created").replace("T", " ")})

            available_woocommerce_products_ids = {}
            available_odoo_products_ids = {}

            odoo_template_id = woocommerce_product_template_id.odoo_product_tmpl_id

            for variant_data in woocommerce_product_data["variations"]:
                woocommerce_product_variant_id, odoo_product_id = self.find_odoo_product_variant(
                    multi_ecommerce_connector_id, variant_data["sku"], variant_data["id"])
                if woocommerce_product_variant_id:
                    available_woocommerce_products_ids.update({variant_data["id"]: woocommerce_product_variant_id})
                    woocommerce_product_template_id = woocommerce_product_variant_id.setu_woocommerce_product_template_id
                if odoo_product_id:
                    available_odoo_products_ids.update({variant_data["id"]: odoo_product_id})
                    odoo_template_id = odoo_product_id.product_tmpl_id

            prepare_product_dict = {}

            if woocommerce_product_data["variations"]:
                for variant_data in woocommerce_product_data["variations"]:
                    variant_id = variant_data.get("id")
                    product_sku = variant_data.get("sku")
                    variant_price = variant_data.get("regular_price") or variant_data.get("sale_price") or 0.0

                    woocommerce_product_variant_id = available_woocommerce_products_ids.get(variant_id)
                    odoo_product_id = False
                    if woocommerce_product_variant_id:
                        odoo_product_id = woocommerce_product_variant_id.odoo_product_id
                        if is_skip_update_existing_product:
                            continue

                    validate_product, message = self.woocommerce_check_validate_product(woocommerce_product_data,
                                                                                        odoo_product_id,
                                                                                        woocommerce_product_variant_id)
                    if not validate_product:
                        if not order_chain_line_id:
                            setu_process_history_line_obj.woocommerce_create_product_process_history_line(message,
                                                                                                          model_id,
                                                                                                          product_chain_line_id,
                                                                                                          process_history_id)
                        else:
                            setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                        model_id,
                                                                                                        order_chain_line_id,
                                                                                                        process_history_id)
                        if not order_chain_line_id:
                            product_chain_line_id.state = "fail"
                            line_failed = True
                        break
                    if not product_sku:
                        message = "No SKU found for a Variant of {0}.".format(template_title)
                        if not order_chain_line_id:
                            setu_process_history_line_obj.woocommerce_create_product_process_history_line(message,
                                                                                                          model_id,
                                                                                                          product_chain_line_id,
                                                                                                          process_history_id)
                        else:
                            setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                        model_id,
                                                                                                        order_chain_line_id,
                                                                                                        process_history_id)
                        continue
                    prepare_variant_vals = {"name": template_title,
                                            "default_code": product_sku,
                                            "woocommerce_product_variant_id": variant_id,
                                            "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                                            "is_product_variant_exported_in_woocommerce": True,
                                            "product_url": variant_data.get("permalink", ""),
                                            "is_woocommerce_manage_stock": variant_data["manage_stock"],
                                            "product_variant_modified_at": variant_data.get("date_modified").replace(
                                                "T", " "),
                                            "active": True}

                    if variant_data.get("date_created"):
                        prepare_variant_vals.update(
                            {"product_variant_created_at": variant_data.get("date_created").replace("T", " ")})
                    if not woocommerce_product_variant_id:
                        if not woocommerce_product_template_id:
                            if not odoo_template_id and multi_ecommerce_connector_id.is_auto_create_product:
                                odoo_template_id, available_odoo_products_ids = self.create_woocommerce_product_variant(
                                    woocommerce_product_data, multi_ecommerce_connector_id)
                            if not odoo_template_id:
                                message = "%s Template Not found for sku %s in Odoo." % (template_title, product_sku)
                                if not order_chain_line_id:
                                    setu_process_history_line_obj.woocommerce_create_product_process_history_line(
                                        message, model_id, product_chain_line_id, process_history_id)
                                else:
                                    setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                                model_id,
                                                                                                                order_chain_line_id,
                                                                                                                process_history_id)
                                if not order_chain_line_id:
                                    product_chain_line_id.state = "fail"
                                    line_failed = True
                                break
                            final_woocommerce_product_template_vals = self.prepare_woocommerce_product_template_vals(
                                prepare_template_vals, odoo_template_id, is_sync_product_category_and_tags,
                                multi_ecommerce_connector_id, process_history_id)
                            woocommerce_product_template_id = self.create(final_woocommerce_product_template_vals)

                        elif not need_to_template_update:
                            final_woocommerce_product_template_vals = self.prepare_woocommerce_product_template_vals(
                                prepare_template_vals, odoo_template_id, is_sync_product_category_and_tags,
                                multi_ecommerce_connector_id, process_history_id)
                            woocommerce_product_template_id.write(final_woocommerce_product_template_vals)
                        need_to_template_update = True

                        odoo_product_id = available_odoo_products_ids.get(variant_id)
                        if not odoo_product_id:
                            if not multi_ecommerce_connector_id.is_auto_create_product:
                                message = "Product %s Not found for sku %s in Odoo." % (template_title, product_sku)
                                if not order_chain_line_id:
                                    setu_process_history_line_obj.woocommerce_create_product_process_history_line(
                                        message, model_id, product_chain_line_id, process_history_id)
                                else:
                                    setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                                model_id,
                                                                                                                order_chain_line_id,
                                                                                                                process_history_id)
                                if not order_chain_line_id:
                                    product_chain_line_id.state = "fail"
                                    line_failed = True
                                continue

                            if odoo_template_id.attribute_line_ids:
                                attribute_lst = []
                                odoo_attribute_ids = odoo_template_id.attribute_line_ids.attribute_id.ids
                                for attribute_dict in variant_data.get("attributes"):
                                    attribute_id = product_attribute_obj.search_or_create_product_attribute(
                                        attribute_dict["name"])
                                    attribute_lst.append(attribute_id.id)
                                attribute_lst.sort()
                                odoo_attribute_ids.sort()
                                if odoo_attribute_ids != attribute_lst:
                                    message = "Trying adding new attribute for sku %s in system for product %s." % (
                                        product_sku, template_title)
                                    if not order_chain_line_id:
                                        setu_process_history_line_obj.woocommerce_create_product_process_history_line(
                                            message, model_id, product_chain_line_id, process_history_id)
                                    else:
                                        setu_process_history_line_obj.woocommerce_create_order_process_history_line(
                                            message, model_id, order_chain_line_id, process_history_id)
                                    if not order_chain_line_id:
                                        product_chain_line_id.state = "fail"
                                        line_failed = True
                                    break
                                else:
                                    template_attribute_value_domain = self.find_template_attribute_values(
                                        woocommerce_product_data.get("attributes"), variant_data.get("attributes"),
                                        odoo_template_id)
                                    if not template_attribute_value_domain:
                                        for attribute_dict in variant_data.get("attributes"):
                                            attribute_id = product_attribute_obj.search_or_create_product_attribute(
                                                attribute_dict["name"],
                                                attribute_type="radio",
                                                create_variant="always",
                                                is_create_new_attribute=True)
                                            value_id = product_attribute_value_obj.search_or_create_product_attribute_value(
                                                attribute_dict["option"], attribute_id,
                                                is_create_new_attribute_value=True)
                                            attribute_line = odoo_template_id.attribute_line_ids.filtered(
                                                lambda x: x.attribute_id.id == attribute_id.id)
                                            if not value_id.id in attribute_line.value_ids.ids:
                                                attribute_line.value_ids = [(4, value_id.id, False)]
                                        odoo_template_id._create_variant_ids()
                                        template_attribute_value_domain = self.find_template_attribute_values(
                                            woocommerce_product_data.get("attributes"), variant_data.get("attributes"),
                                            odoo_template_id)
                                    template_attribute_value_domain.append(
                                        ("product_tmpl_id", "=", odoo_template_id.id))
                                    odoo_product_id = product_product_obj.search(template_attribute_value_domain)
                                    odoo_product_id.default_code = variant_data["sku"]
                            else:
                                product_vals = {"name": template_title, "type": "consu",
                                                "default_code": variant_data["sku"]}
                                if multi_ecommerce_connector_id.is_use_default_product_description:
                                    product_vals.update({"description_sale": variant_data.get("description", "")})

                                odoo_product_id = product_product_obj.search(
                                    [("default_code", "=", variant_data["sku"]),
                                     ('company_id', '=',
                                      multi_ecommerce_connector_id.odoo_company_id and multi_ecommerce_connector_id.odoo_company_id.id or False)])
                                if not odoo_product_id:
                                    odoo_product_id = product_product_obj.create(product_vals)
                                else:
                                    odoo_product_id.write(product_vals)
                        if odoo_product_id:
                            prepare_variant_vals.update({"odoo_product_id": odoo_product_id.id,
                                                         "setu_woocommerce_product_template_id": woocommerce_product_template_id.id})
                            woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.create(
                                prepare_variant_vals)
                            woocommerce_product_template_id.odoo_product_tmpl_id = odoo_product_id.product_tmpl_id
                        else:
                            message = "It seems new variants or attributes are created on WooCommerce store but " \
                                      "it is not mapped with the Odoo database."
                            if not order_chain_line_id:
                                setu_process_history_line_obj.woocommerce_create_product_process_history_line(message,
                                                                                                              model_id,
                                                                                                              product_chain_line_id,
                                                                                                              process_history_id)
                            else:
                                setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                            model_id,
                                                                                                            order_chain_line_id,
                                                                                                            process_history_id)
                            continue
                    else:
                        if not need_to_template_update:
                            product_tmpl_id = woocommerce_product_template_id.odoo_product_tmpl_id
                            final_woocommerce_product_template_vals = self.prepare_woocommerce_product_template_vals(
                                prepare_template_vals, product_tmpl_id, is_sync_product_category_and_tags,
                                multi_ecommerce_connector_id, process_history_id)
                            woocommerce_product_template_id.write(final_woocommerce_product_template_vals)
                            need_to_template_update = True
                        woocommerce_product_variant_id.write(prepare_variant_vals)

                    multi_ecommerce_connector_id.odoo_pricelist_id.set_product_price_from_pricelist(
                        woocommerce_product_variant_id.odoo_product_id, variant_price)

                    if is_import_with_image:
                        if not woocommerce_product_template_id.odoo_product_tmpl_id.image_1920:
                            prepare_product_dict.update(
                                {'product_tmpl_id': woocommerce_product_template_id.odoo_product_tmpl_id,
                                 'is_image': True})
                        self.woocommerce_product_image_update(woocommerce_product_data["images"], variant_data["image"],
                                                              woocommerce_product_template_id,
                                                              woocommerce_product_variant_id,
                                                              multi_ecommerce_connector_id,
                                                              need_to_template_image_update, prepare_product_dict)
                        need_to_template_image_update = True
            else:
                product_sku = woocommerce_product_data["sku"]
                variant_price = woocommerce_product_data.get("regular_price") or woocommerce_product_data.get(
                    "sale_price") or 0.0

                if not product_sku:
                    message = "SKU/Internal Reference is not set for product '{0}' in the WooCommerce store.".format(
                        template_title)
                    if not order_chain_line_id:
                        setu_process_history_line_obj.woocommerce_create_product_process_history_line(message, model_id,
                                                                                                      product_chain_line_id,
                                                                                                      process_history_id)
                    else:
                        setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                                    order_chain_line_id,
                                                                                                    process_history_id)
                    if not order_chain_line_id:
                        product_chain_line_id.write(
                            {"state": "fail", "last_product_chain_line_process_date": datetime.now()})
                    continue

                woocommerce_product_variant_id, odoo_product_id = self.find_odoo_product_variant(
                    multi_ecommerce_connector_id, product_sku, woo_tmpl_id)
                if woocommerce_product_variant_id and not odoo_product_id:
                    woocommerce_product_template_id = woocommerce_product_variant_id.setu_woocommerce_product_template_id
                    odoo_product_id = woocommerce_product_variant_id.odoo_product_id
                    if is_skip_update_existing_product:
                        product_chain_line_id.state = "done"
                        continue

                if odoo_product_id:
                    odoo_template_id = odoo_product_id.product_tmpl_id

                validate_product, message = self.woocommerce_check_validate_product(woocommerce_product_data,
                                                                                    odoo_product_id,
                                                                                    woocommerce_product_variant_id)

                if not validate_product:
                    if not order_chain_line_id:
                        setu_process_history_line_obj.woocommerce_create_product_process_history_line(message, model_id,
                                                                                                      product_chain_line_id,
                                                                                                      process_history_id)
                    else:
                        setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                                    order_chain_line_id,
                                                                                                    process_history_id)

                    if not order_chain_line_id:
                        product_chain_line_id.state = "fail"
                    continue

                prepare_variant_vals = {"name": template_title,
                                        "default_code": product_sku,
                                        "woocommerce_product_variant_id": woo_tmpl_id,
                                        "multi_ecommerce_connector_id": multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                                        "is_product_variant_exported_in_woocommerce": True,
                                        "product_url": woocommerce_product_data.get("permalink", ""),
                                        "is_woocommerce_manage_stock": woocommerce_product_data["manage_stock"],
                                        "product_variant_modified_at": woocommerce_product_data.get(
                                            "date_modified").replace("T", " "),
                                        "active": True}

                if woocommerce_product_data.get("date_created"):
                    prepare_variant_vals.update(
                        {"product_variant_created_at": woocommerce_product_data.get("date_created").replace("T", " ")})

                if not woocommerce_product_variant_id:
                    if not woocommerce_product_template_id:
                        if not odoo_template_id and multi_ecommerce_connector_id.is_auto_create_product:
                            woo_weight = float(woocommerce_product_data.get("weight") or "0.0")
                            weight = self.convert_weight_by_uom(woo_weight, multi_ecommerce_connector_id,
                                                                import_process=True)
                            odoo_template_vals = {"name": template_title, "type": "consu",
                                                  "default_code": woocommerce_product_data["sku"], "weight": weight}
                            if multi_ecommerce_connector_id.is_use_default_product_description:
                                odoo_template_vals.update(
                                    {"description_sale": woocommerce_product_data.get("description", "")})
                            odoo_template_id = product_template_obj.create(odoo_template_vals)
                            odoo_product_id = odoo_template_id.product_variant_ids

                        if not odoo_template_id:
                            message = "%s Template Not found for sku %s in Odoo." % (template_title, product_sku)
                            if not order_chain_line_id:
                                setu_process_history_line_obj.woocommerce_create_product_process_history_line(message,
                                                                                                              model_id,
                                                                                                              product_chain_line_id,
                                                                                                              process_history_id)
                            else:
                                setu_process_history_line_obj.woocommerce_create_order_process_history_line(message,
                                                                                                            model_id,
                                                                                                            order_chain_line_id,
                                                                                                            process_history_id)
                            if not order_chain_line_id:
                                product_chain_line_id.state = "fail"
                            continue

                        final_woocommerce_product_template_vals = self.prepare_woocommerce_product_template_vals(
                            prepare_template_vals, odoo_template_id, is_sync_product_category_and_tags,
                            multi_ecommerce_connector_id, process_history_id)
                        woocommerce_product_template_id = self.create(final_woocommerce_product_template_vals)
                    prepare_variant_vals.update({"odoo_product_id": odoo_product_id.id,
                                                 "setu_woocommerce_product_template_id": woocommerce_product_template_id.id})
                    woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.create(prepare_variant_vals)
                else:
                    if not need_to_template_update:
                        final_woocommerce_product_template_vals = self.prepare_woocommerce_product_template_vals(
                            prepare_template_vals, odoo_template_id, is_sync_product_category_and_tags,
                            multi_ecommerce_connector_id, process_history_id)
                        woocommerce_product_template_id.write(final_woocommerce_product_template_vals)
                    woocommerce_product_variant_id.write(prepare_variant_vals)

                multi_ecommerce_connector_id.odoo_pricelist_id.set_product_price_from_pricelist(
                    woocommerce_product_variant_id.odoo_product_id, variant_price)
                if is_import_with_image:
                    self.woocommerce_product_image_update(woocommerce_product_data["images"], {},
                                                          woocommerce_product_template_id,
                                                          woocommerce_product_variant_id, multi_ecommerce_connector_id,
                                                          need_to_template_image_update)

            if not order_chain_line_id:
                if woocommerce_product_template_id and not line_failed:
                    product_chain_line_id.write(
                        {"state": "done", "last_product_chain_line_process_date": datetime.now()})

                else:
                    message = "Product title with %s is not seems be a variable product. Please check with the data properly" % (
                        template_title)
                    if not order_chain_line_id:
                        setu_process_history_line_obj.woocommerce_create_product_process_history_line(message, model_id,
                                                                                                      product_chain_line_id,
                                                                                                      process_history_id)
                    else:
                        setu_process_history_line_obj.woocommerce_create_order_process_history_line(message, model_id,
                                                                                                    order_chain_line_id,
                                                                                                    process_history_id)
                    product_chain_line_id.write(
                        {"state": "fail", "last_product_chain_line_process_date": datetime.now()})
                    product_chain_line_id.setu_ecommerce_product_chain_id.is_chain_in_process = False
        return True

    @api.model
    def fetch_and_create_product_variant_image(self, multi_ecommerce_connector_id, woocommerce_variant_id):
        image_id = False
        prepare_woocommerce_variant_dict = {}
        variant_images_ids = woocommerce_variant_id.setu_woocommerce_product_image_ids
        if variant_images_ids:
            if not variant_images_ids[0].setu_woocommerce_product_image_id:
                res = ImageUploader.upload_image(multi_ecommerce_connector_id, variant_images_ids[0].image,
                                                 "%s_%s" % (woocommerce_variant_id.name, woocommerce_variant_id.id))
                image_id = res and res.get('id', False) or ''
            else:
                image_id = variant_images_ids[0].setu_woocommerce_product_image_id
        if image_id:
            prepare_woocommerce_variant_dict.update({"image": {'id': image_id}})
            variant_images_ids[0].setu_woocommerce_product_image_id = image_id
        return prepare_woocommerce_variant_dict

    @api.model
    def prepare_product_variant_data(self, woocommerce_variant_id, multi_ecommerce_connector_id, need_to_update_image):
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        attribute_lst = []
        prepare_woocommerce_variant_dict = {}
        attribute_prepare_dict = {}
        for attribute_value in woocommerce_variant_id.odoo_product_id.product_template_attribute_value_ids:
            if multi_ecommerce_connector_id.woocommerce_attribute_type == 'select':
                woocommerce_product_attributes_id = setu_woocommerce_product_attributes_obj.search(
                    [('name', '=', attribute_value.attribute_id.name), ('multi_ecommerce_connector_id', '=',
                                                                        multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                     ('is_product_attributes_exported_in_woocommerce', '=', True)], limit=1)
                if not woocommerce_product_attributes_id:
                    woocommerce_product_attributes_id = setu_woocommerce_product_attributes_obj.search(
                        [('attribute_id', '=', attribute_value.attribute_id.id), ('multi_ecommerce_connector_id', '=',
                                                                                  multi_ecommerce_connector_id and multi_ecommerce_connector_id.id),
                         ('is_product_attributes_exported_in_woocommerce', '=', True)], limit=1)
                attribute_prepare_dict = {
                    'id': woocommerce_product_attributes_id and woocommerce_product_attributes_id.woocommerce_attribute_id,
                    'option': attribute_value.name}
            if multi_ecommerce_connector_id.woocommerce_attribute_type == 'text':
                attribute_prepare_dict = {'name': attribute_value.attribute_id.name, 'option': attribute_value.name}
            attribute_lst.append(attribute_prepare_dict)
        if need_to_update_image:
            prepare_woocommerce_variant_dict.update(
                self.fetch_and_create_product_variant_image(multi_ecommerce_connector_id, woocommerce_variant_id))
        weight = self.convert_weight_by_uom(woocommerce_variant_id.odoo_product_id.weight, multi_ecommerce_connector_id)
        prepare_woocommerce_variant_dict.update(
            {'attributes': attribute_lst, 'sku': str(woocommerce_variant_id.default_code), 'weight': str(weight),
             "manage_stock": woocommerce_variant_id.is_woocommerce_manage_stock})
        return prepare_woocommerce_variant_dict

    @api.model
    def fetch_odoo_product_price(self, multi_ecommerce_connector_id, woocommerce_variant_id):
        price = multi_ecommerce_connector_id.odoo_pricelist_id.get_product_price_from_pricelist(
            product_id=woocommerce_variant_id.odoo_product_id, partner_id=False)
        return price

    def import_and_sync_woocommerce_product_template_erp(self, multi_ecommerce_connector_id, process_history_id,
                                                         woocommerce_product_tmpl_id=False, after_date=False,
                                                         before_date=False):
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        setu_woocommerce_product_chain_obj = self.env['setu.ecommerce.product.chain']

        model_id = setu_process_history_line_obj.get_model_id(self._name)

        total_number_product_lst = []

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()

        if woocommerce_product_tmpl_id:
            woo_product_tmpl_response = woo_api_connect.get('products/%s' % woocommerce_product_tmpl_id)
        else:
            params = {'per_page': 100}
            if after_date and before_date:
                after_date = pytz.utc.localize(after_date).astimezone(
                    pytz.timezone(multi_ecommerce_connector_id.woocommerce_store_timezone))
                before_date = pytz.utc.localize(before_date).astimezone(
                    pytz.timezone(multi_ecommerce_connector_id.woocommerce_store_timezone))

                params.update({'after': after_date, "before": before_date})
            woo_product_tmpl_response = woo_api_connect.get('products', params=params)

        if not isinstance(woo_product_tmpl_response, requests.models.Response):
            message = "Invalid Response Format, %s" % woo_product_tmpl_response
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        if woo_product_tmpl_response.status_code not in [200, 201]:
            message = "Invalid Request Format, %s" % woo_product_tmpl_response.content
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return False

        total_pages = woo_product_tmpl_response.headers.get('x-wp-totalpages', 0)
        try:
            woo_product_tmpl_response_data = woo_product_tmpl_response.json()
        except Exception as e:
            message = "Requests to resources that don't exist or are missing export Product Stock to WooCommerce for %s %s" % (
                multi_ecommerce_connector_id.name, e)
            setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id, process_history_id)
            return []

        if woocommerce_product_tmpl_id:
            final_convert_response_lst = [woo_product_tmpl_response_data]
        else:
            final_convert_response_lst = woo_product_tmpl_response_data

        if int(total_pages) >= 2:
            for list_of_page in range(2, int(total_pages) + 1):
                final_convert_response_lst += multi_ecommerce_connector_id.process_import_all_records(woo_api_connect,
                                                                                                      multi_ecommerce_connector_id,
                                                                                                      list_of_page,
                                                                                                      process_history_id,
                                                                                                      model_id,
                                                                                                      method='products')
        is_chain_available = False
        product_chain_line_ids = False

        if not woocommerce_product_tmpl_id:
            existing_product_chain_line_id = setu_woocommerce_product_chain_obj.search([(
                'multi_ecommerce_connector_id',
                '=',
                multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
            if existing_product_chain_line_id:
                is_chain_available = True
                product_chain_line_ids = existing_product_chain_line_id.setu_ecommerce_product_chain_line_ids

        already_exist_chain_line_product_id = False
        for response_dict in final_convert_response_lst:
            flag = False
            woo_product_variant_response_convert_json = []
            woocommerce_product_tmpl_id = response_dict.get('id')
            date_modified = response_dict.get('date_modified', False)

            if is_chain_available:
                already_exist_chain_line_product_ids = product_chain_line_ids.filtered(
                    lambda x: int(x.ecommerce_product_id) == woocommerce_product_tmpl_id)
                already_exist_chain_line_product_ids.sorted(lambda x: x.id, True)

                for already_exist_chain_line_product_id in already_exist_chain_line_product_ids:
                    if already_exist_chain_line_product_id.state in ["draft", "done"]:
                        if already_exist_chain_line_product_id.last_product_chain_update_date == date_modified:
                            flag = True
                            break
                        if already_exist_chain_line_product_id.state == "draft":
                            break
                    already_exist_chain_line_product_id = False
                    break
            if flag:
                continue
            if response_dict.get('variations'):
                try:
                    params = {"per_page": 100}
                    woo_product_variant_response = woo_api_connect.get(
                        "products/%s/variations" % (response_dict.get("id")), params=params)
                    woo_product_variant_response_convert_json = woo_product_variant_response.json()
                    variant_total_pages = woo_product_variant_response.headers.get("X-WP-TotalPages")

                    if int(variant_total_pages) > 1:
                        for variant_list_page in range(2, int(variant_total_pages) + 1):
                            params["page"] = variant_list_page
                            woo_product_variant_response_page_response = woo_api_connect.get(
                                "products/%s/variations" % (response_dict.get("id")), params=params)
                            woo_product_variant_response_convert_json += woo_product_variant_response_page_response.json()

                except Exception as e:
                    message = "Requests to resources that don't exist or are missing import product variants from WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
            response_dict.update({'variations': woo_product_variant_response_convert_json})
            if already_exist_chain_line_product_id:
                already_exist_chain_line_product_id.write({'product_chain_line_data': json.dumps(response_dict),
                                                           'last_product_chain_update_date': date_modified})
            else:
                total_number_product_lst.append(response_dict)

        return total_number_product_lst

    def find_odoo_product_variant(self, multi_ecommerce_connector_id, default_code, woocommerce_product_variant_id):

        odoo_product_obj = self.env['product.product']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        if woocommerce_product_variant_id:
            woocommerce_product_variant_id = woocommerce_product_variant_id
        if not woocommerce_product_variant_id:
            woocommerce_product_variant_id = False

        setu_woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.with_context(
            active_test=False).search([('woocommerce_product_variant_id', '=', woocommerce_product_variant_id), (
            'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                      limit=1)
        if not setu_woocommerce_product_variant_id:
            setu_woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.with_context(
                active_test=False).search([('default_code', '=', default_code), (
                'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                          limit=1)

        if not setu_woocommerce_product_variant_id:
            setu_woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.with_context(
                active_test=False).search([('odoo_product_id.default_code', '=', default_code), (
                'multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                                          limit=1)

        if not setu_woocommerce_product_variant_id:
            odoo_product_obj = odoo_product_obj.search([('default_code', '=', default_code), ('company_id', '=',
                                                                                              multi_ecommerce_connector_id.odoo_company_id and multi_ecommerce_connector_id.odoo_company_id.id or False)],
                                                       limit=1)

        return setu_woocommerce_product_variant_id, odoo_product_obj

    def create_woocommerce_product_variant(self, product_template_vals, multi_ecommerce_connector_id):

        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        product_template_obj = self.env['product.template']

        title = ''
        if product_template_vals.get('name', ''):
            title = product_template_vals.get('name')
        if product_template_vals.get('title', ''):
            title = product_template_vals.get('title')

        attribute_line_lst = []

        for product_template_dict in product_template_vals.get('attributes'):
            if not product_template_dict.get('variation'):
                continue
            attribute_name = product_template_dict.get('name')
            attribute_values = product_template_dict.get('options')
            product_attribute_id = product_attribute_obj.search_or_create_product_attribute(attribute_name,
                                                                                            attribute_type='radio',
                                                                                            create_variant='always',
                                                                                            is_create_new_attribute=True)

            product_attribute_id = product_attribute_id.filtered(lambda x: x.name == attribute_name)[0] if len(
                product_attribute_id) > 1 else product_attribute_id

            attribute_value_lst = []

            for attribute_value_dict in attribute_values:
                product_attribute_value_id = product_attribute_value_obj.search_or_create_product_attribute_value(
                    attribute_value_dict, product_attribute_id, is_create_new_attribute_value=True)
                product_attribute_value_id = \
                    product_attribute_value_id.filtered(lambda x: x.name == product_attribute_value_id)[0] if len(
                        product_attribute_value_id) > 1 else product_attribute_value_id
                attribute_value_lst.append(product_attribute_value_id.id)

            if attribute_value_lst:
                attribute_line_ids = [0, False, {'attribute_id': product_attribute_id and product_attribute_id.id,
                                                 'value_ids': [[6, False, attribute_value_lst]]}]
                attribute_line_lst.append(attribute_line_ids)
        if attribute_line_lst:
            product_tmpl_vals = {'name': title, 'type': 'product', 'attribute_line_ids': attribute_line_lst}

            if multi_ecommerce_connector_id.is_use_default_product_description:
                product_tmpl_vals.update({"description_sale": product_template_vals.get("description", "")})
            odoo_product_template_id = product_template_obj.create(product_tmpl_vals)

            existing_odoo_product_ids = self.set_default_code_woocommerce_product_variant(multi_ecommerce_connector_id,
                                                                                          product_template_vals,
                                                                                          odoo_product_template_id)

            if existing_odoo_product_ids:
                return odoo_product_template_id, existing_odoo_product_ids
            return False, False

    def set_default_code_woocommerce_product_variant(self, multi_ecommerce_connector_id, product_template_vals,
                                                     odoo_product_template):
        product_product_obj = self.env['product.product']
        product_pricelist_item_obj = self.env['product.pricelist.item']
        available_odoo_products_dict = {}

        for product_variant_dict in product_template_vals.get('variations'):

            default_code = product_variant_dict.get('sku')
            price = product_variant_dict.get('regular_price') or product_variant_dict.get('sale_price') or 0.0
            woo_weight = float(product_variant_dict.get("weight") or "0.0")
            variation_attributes = product_variant_dict.get('attributes')

            if len(odoo_product_template.attribute_line_ids.ids) != len(variation_attributes):
                continue

            template_attribute_value_domain = self.find_template_attribute_values(
                product_template_vals.get("attributes"), variation_attributes, odoo_product_template)

            if template_attribute_value_domain:
                odoo_product_id = product_product_obj.search(template_attribute_value_domain)

                if odoo_product_id:
                    weight = self.convert_weight_by_uom(woo_weight, multi_ecommerce_connector_id, import_process=True)
                    odoo_product_id.write({'default_code': default_code, "weight": weight})
                    available_odoo_products_dict.update({product_variant_dict["id"]: odoo_product_id})
                    product_pricelist_item_id = product_pricelist_item_obj.search(
                        [('pricelist_id', '=', multi_ecommerce_connector_id.odoo_pricelist_id.id),
                         ('product_id', '=', odoo_product_id and odoo_product_id.id)], limit=1)

                    if not product_pricelist_item_id:
                        multi_ecommerce_connector_id.odoo_pricelist_id.write({'item_ids': [(0, 0, {
                            'applied_on': '0_product_variant', 'product_id': odoo_product_id.id,
                            'compute_price': 'fixed', 'fixed_price': price})]})
                    else:
                        if odoo_product_template.company_id and product_pricelist_item_id.currency_id.id != odoo_product_template.company_id.currency_id.id:
                            instance_currency = product_pricelist_item_id.currency_id
                            product_company_currency = odoo_product_template.company_id.currency_id
                            price = instance_currency.compute(float(price), product_company_currency)
                        product_pricelist_item_id.write({'fixed_price': price})
        if not available_odoo_products_dict:
            odoo_product_template.sudo().unlink()
        return available_odoo_products_dict

    @api.model
    def find_template_attribute_values(self, product_template_attributes, product_variant_attributes,
                                       odoo_product_template):
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        product_template_attribute_value_obj = self.env['product.template.attribute.value']

        template_attribute_value_lst = []
        for product_variant_attribute_id in product_variant_attributes:
            attribute_name = product_variant_attribute_id.get('name')
            attribute_value = product_variant_attribute_id.get('option')

            for product_template_attribute_id in product_template_attributes:
                if product_template_attribute_id.get('variation') and product_template_attribute_id.get('name'):
                    if product_template_attribute_id.get('name').replace(" ", "-").lower() == attribute_name:
                        attribute_name = product_template_attribute_id.get('name')
                        break
            product_attribute_ids = product_attribute_obj.search_or_create_product_attribute(attribute_name,
                                                                                             attribute_type="radio",
                                                                                             create_variant="always",
                                                                                             is_create_new_attribute=True)
            for product_attribute_id in product_attribute_ids:
                product_attribute_value_id = product_attribute_value_obj.search_or_create_product_attribute_value(
                    attribute_value, product_attribute_id, is_create_new_attribute_value=True)

                if product_attribute_value_id:
                    template_attribute_value_id = product_template_attribute_value_obj.search([(
                        'product_attribute_value_id',
                        '=',
                        product_attribute_value_id and product_attribute_value_id.id),
                        ('attribute_id', '=',
                         product_attribute_id and product_attribute_id.id),
                        ('product_tmpl_id', '=',
                         odoo_product_template and odoo_product_template.id)],
                        limit=1)
                    if template_attribute_value_id:
                        domain = ('product_template_attribute_value_ids', '=', template_attribute_value_id.id)
                        template_attribute_value_lst.append(domain)
                    else:
                        return []
        return template_attribute_value_lst

    def mapped_and_create_product_category(self, multi_ecommerce_connector_id, process_history_id,
                                           woocommerce_product_category_data, import_product_with_image=True):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']

        product_category_lst = []
        for woocommerce_product_category_dict in woocommerce_product_category_data:
            woocommerce_product_category_id = setu_woocommerce_product_category_obj.search(
                [('woocommerce_category_id', '=', woocommerce_product_category_dict.get('id')),
                 ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)

            if not woocommerce_product_category_id:
                woocommerce_product_category_id = setu_woocommerce_product_category_obj.search(
                    [('slug', '=', woocommerce_product_category_dict.get('slug')),
                     ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)

            if woocommerce_product_category_id:
                woocommerce_product_category_id.write(
                    {'woocommerce_category_id': woocommerce_product_category_dict.get('id'),
                     'name': woocommerce_product_category_dict.get('name'),
                     'display': woocommerce_product_category_dict.get('display'),
                     'slug': woocommerce_product_category_dict.get('slug'),
                     'is_product_category_exported_in_woocommerce': True})

                setu_woocommerce_product_category_obj.process_for_import_product_category_woocommerce_to_erp(
                    multi_ecommerce_connector_id, process_history_id,
                    woocommerce_product_category_id=woocommerce_product_category_id,
                    import_product_with_image=import_product_with_image)
                product_category_lst.append(woocommerce_product_category_id.id)
            else:
                woocommerce_product_category_id = setu_woocommerce_product_category_obj.create(
                    {'woocommerce_category_id': woocommerce_product_category_dict.get('id'),
                     'name': woocommerce_product_category_dict.get('name'),
                     'display': woocommerce_product_category_dict.get('display'),
                     'slug': woocommerce_product_category_dict.get('slug'),
                     'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                     'is_product_category_exported_in_woocommerce': True})

                setu_woocommerce_product_category_obj.process_for_import_product_category_woocommerce_to_erp(
                    multi_ecommerce_connector_id, process_history_id,
                    woocommerce_product_category_id=woocommerce_product_category_id,
                    import_product_with_image=import_product_with_image)
                woocommerce_product_category_id and product_category_lst.append(woocommerce_product_category_id.id)

        return product_category_lst

    def mapped_and_create_product_tags(self, multi_ecommerce_connector_id, woocommerce_product_tags_data):
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']

        tag_lst = []
        for woocommerce_product_tags_dict in woocommerce_product_tags_data:
            woocommerce_product_tags_id = setu_woocommerce_product_tags_obj.search(
                [('woocommerce_tag_id', '=', woocommerce_product_tags_dict.get('id')),
                 ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
            if not woocommerce_product_tags_id:
                woocommerce_product_tags_id = setu_woocommerce_product_tags_obj.search(
                    [('slug', '=', woocommerce_product_tags_dict.get('slug')),
                     ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1)
            if woocommerce_product_tags_id:
                woocommerce_product_tags_id.write({'name': woocommerce_product_tags_dict.get('name'),
                                                   'slug': woocommerce_product_tags_dict.get('slug'),
                                                   'is_product_tags_exported_in_woocommerce': True})
                tag_lst.append(woocommerce_product_tags_id.id)
            else:
                woocommerce_product_tags_id = setu_woocommerce_product_tags_obj.create(
                    {'woocommerce_tag_id': woocommerce_product_tags_dict.get('id'),
                     'name': woocommerce_product_tags_dict.get('name'),
                     'slug': woocommerce_product_tags_dict.get('slug'),
                     'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                     'is_product_tags_exported_in_woocommerce': True})

                woocommerce_product_tags_id and tag_lst.append(woocommerce_product_tags_id.id)
        return tag_lst

    def woocommerce_check_validate_product(self, product_response, odoo_product_id, woocommerce_product_template):
        woocommerce_product_lst = []
        variations = product_response.get('variations')
        template_title = product_response.get('name')
        total_variant = len(variations)

        validate_product = True
        message = ""

        if not odoo_product_id and not odoo_product_id:
            if total_variant != 0:
                attributes = 1
                for attribute in product_response.get('attributes'):
                    if attribute.get('variation'):
                        attributes *= len(attribute.get('options'))

            product_attributes = {}
            for variation in variations:
                sku = variation.get("sku")
                attributes = variation.get('attributes')
                attributes and product_attributes.update({sku: attributes})
                sku and woocommerce_product_lst.append(sku)

            if not product_attributes and product_response.get('type') == 'variable':
                message = "Attributes are not set in any variation of Product: %s and ID: %s." % (
                    template_title, product_response.get("id"))
                validate_product = False
                return validate_product, message

            if woocommerce_product_lst:
                woocommerce_product_lst = list(filter(lambda x: len(x) > 0, woocommerce_product_lst))
            total_woocommerce_product_lst = len(set(woocommerce_product_lst))
            if not len(woocommerce_product_lst) == total_woocommerce_product_lst:
                duplicate_product_found = list(
                    set([woo_sku for woo_sku in woocommerce_product_lst if woocommerce_product_lst.count(woo_sku) > 1]))
                message = "Duplicate SKU(%s) found in Product: %s and ID: %s." % (
                    duplicate_product_found, template_title, product_response.get("id"))
                validate_product = False
                return validate_product, message

        woocommerce_product_lst = []
        odoo_product_lst = []
        if odoo_product_id:
            odoo_product_tmpl_id = odoo_product_id.product_tmpl_id
            if not (total_variant == 0 and odoo_product_tmpl_id.product_variant_count == 1):
                if total_variant == odoo_product_tmpl_id.product_variant_count:
                    for woo_sku, odoo_sku in zip(product_response.get('variations'),
                                                 odoo_product_tmpl_id.product_variant_ids):
                        woocommerce_product_lst.append(woo_sku.get('sku'))
                        odoo_sku.default_code and odoo_product_lst.append(odoo_sku.default_code)

                    woocommerce_product_lst = list(filter(lambda x: len(x) > 0, woocommerce_product_lst))

                    total_woocommerce_sku = len(set(woocommerce_product_lst))
                    if not len(woocommerce_product_lst) == total_woocommerce_sku:
                        duplicate_skus = list(set([woo_sku for woo_sku in woocommerce_product_lst if
                                                   woocommerce_product_lst.count(woo_sku) > 1]))
                        message = "Duplicate SKU(%s) found in Product: %s and ID: %s." % (
                            duplicate_skus, template_title, product_response.get("id"))
                        validate_product = False
                        return validate_product, message

        if woocommerce_product_template:
            woo_skus = []
            for woo_sku in product_response.get('variations'):
                woo_skus.append(woo_sku.get('sku'))

            total_woo_sku = len(set(woo_skus))
            if not len(woo_skus) == total_woo_sku:
                duplicate_skus = list(set([woo_sku for woo_sku in woo_skus if woo_skus.count(woo_sku) > 1]))
                message = "Duplicate SKU(%s) found in Product: %s and ID: %s." % (
                    duplicate_skus, template_title, product_response.get("id"))
                validate_product = False
                return validate_product, message

        return validate_product, message

    @api.model
    def prepare_woocommerce_product_template_vals(self, woo_commerce_product_tmpl_vals, odoo_template_id,
                                                  is_process_from_order, multi_ecommerce_connector_id,
                                                  process_history_id):
        setu_woocommerce_product_category_obj = self.env["setu.woocommerce.product.category"]
        setu_woocommerce_product_tags_obj = self.env["setu.woocommerce.product.tags"]

        if is_process_from_order:
            woocommerce_product_category_ids = self.mapped_and_create_product_category(multi_ecommerce_connector_id,
                                                                                       process_history_id,
                                                                                       woo_commerce_product_tmpl_vals[
                                                                                           "setu_woocommerce_product_category_ids"],
                                                                                       multi_ecommerce_connector_id.is_sync_woocommerce_product_images)
            woocommerce_product_tag_ids = self.mapped_and_create_product_tags(multi_ecommerce_connector_id,
                                                                              woo_commerce_product_tmpl_vals[
                                                                                  "setu_woocommerce_product_tag_ids"])
        # else:
        #     woocommerce_product_category_ids = []
        #     woocommerce_product_tag_ids = []
        #     for woo_category in woo_commerce_product_tmpl_vals["setu_woocommerce_product_category_ids"]:
        #         woocommerce_product_category_id = setu_woocommerce_product_category_obj.search(
        #             [("woocommerce_category_id", "=", woo_category.get("id")),
        #              ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1).id
        #         woocommerce_product_category_ids.append(woocommerce_product_category_id)
        #     for woo_tag in woo_commerce_product_tmpl_vals["setu_woocommerce_product_tag_ids"]:
        #         woocommerce_product_tag_id = setu_woocommerce_product_tags_obj.search(
        #             [("woocommerce_tag_id", "=", woo_tag.get("id")),
        #              ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)], limit=1).id
        #         woocommerce_product_tag_ids.append(woocommerce_product_tag_id)

            woo_commerce_product_tmpl_vals.update({"odoo_product_tmpl_id": odoo_template_id and odoo_template_id.id,
                                               "is_product_template_exported_in_woocommerce": True,
                                               "setu_woocommerce_product_category_ids": [
                                                   (6, 0, woocommerce_product_category_ids)],
                                               "setu_woocommerce_product_tag_ids": [
                                                   (6, 0, woocommerce_product_tag_ids)]})

        return woo_commerce_product_tmpl_vals

    @api.model
    def woocommerce_product_image_update(self, template_images, variant_image, woocommerce_product_template_id,
                                         woocommerce_product_variant_id, multi_ecommerce_connector_id,
                                         need_to_update_image, prepare_product_dict=False):
        setu_generic_product_image_obj = self.env["setu.generic.product.image"]
        setu_woocommerce_product_image_obj = woocommerce_product_image_ids = remove_obj = self.env[
            "setu.woocommerce.product.image"]

        if not need_to_update_image:
            generic_odoo_image_dict = {}

            if not multi_ecommerce_connector_id.is_woocommerce_image_url:
                for odoo_image in woocommerce_product_template_id.odoo_product_tmpl_id.setu_generic_product_image_ids:
                    if not odoo_image.image:
                        continue
                    key = hashlib.md5(odoo_image.image).hexdigest()
                    if not key:
                        continue
                    generic_odoo_image_dict.update({key: odoo_image.id})
                for template_image in template_images:
                    image_id = template_image["id"]
                    url = template_image.get('src')
                    woocommerce_product_image_id = setu_woocommerce_product_image_obj.search([(
                        "setu_woocommerce_product_template_id",
                        "=",
                        woocommerce_product_template_id and woocommerce_product_template_id.id),
                        (
                            "setu_woocommerce_product_variant_id",
                            "=", False), (
                            "setu_woocommerce_product_image_id",
                            "=", image_id)])
                    if not woocommerce_product_image_id:
                        try:
                            response = requests.get(url, stream=True, verify=False, timeout=10)
                            if response.status_code == 200:
                                image = base64.b64encode(response.content)
                                key = hashlib.md5(image).hexdigest()
                                if key in generic_odoo_image_dict.keys():
                                    woocommerce_product_image_id = setu_woocommerce_product_image_obj.create(
                                        {"setu_woocommerce_product_template_id": woocommerce_product_template_id.id,
                                         "setu_woocommerce_product_image_id": image_id,
                                         "setu_generic_product_image_id": generic_odoo_image_dict[key]})
                                else:
                                    if not woocommerce_product_template_id.odoo_product_tmpl_id.image_1920:
                                        woocommerce_product_template_id.odoo_product_tmpl_id.image_1920 = image
                                        generic_product_image_id = woocommerce_product_template_id.odoo_product_tmpl_id.setu_generic_product_image_ids.filtered(
                                            lambda
                                                x: x.image == woocommerce_product_template_id.odoo_product_tmpl_id.image_1920)
                                    else:
                                        generic_product_image_id = setu_generic_product_image_obj.create(
                                            {"name": woocommerce_product_template_id.name,
                                             "template_id": woocommerce_product_template_id.odoo_product_tmpl_id.id,
                                             "image": image, "url": url})
                                    woocommerce_product_image_id = setu_woocommerce_product_image_obj.search([(
                                        "setu_woocommerce_product_template_id",
                                        "=",
                                        woocommerce_product_template_id.id),
                                        (
                                            "setu_generic_product_image_id",
                                            "=",
                                            generic_product_image_id.id)])
                                    if woocommerce_product_image_id:
                                        woocommerce_product_image_id.setu_woocommerce_product_image_id = image_id
                        except Exception:
                            pass
                    woocommerce_product_image_ids += woocommerce_product_image_id
                all_woocommerce_product_images = setu_woocommerce_product_image_obj.search(
                    [("setu_woocommerce_product_template_id", "=", woocommerce_product_template_id.id),
                     ("setu_woocommerce_product_variant_id", "=", False)])
                remove_obj += (all_woocommerce_product_images - woocommerce_product_image_ids)
        if variant_image:
            generic_odoo_image_dict = {}
            if not multi_ecommerce_connector_id.is_woocommerce_image_url:
                for odoo_image in woocommerce_product_variant_id.odoo_product_id.setu_generic_product_image_ids:
                    if not odoo_image.image:
                        continue
                    key = hashlib.md5(odoo_image.image).hexdigest()
                    if not key:
                        continue
                    generic_odoo_image_dict.update({key: odoo_image.id})

                image_id = variant_image["id"]
                url = variant_image.get('src')
                woocommerce_product_image_id = setu_woocommerce_product_image_obj.search(
                    [("setu_woocommerce_product_variant_id", "=", woocommerce_product_variant_id.id),
                     ("setu_woocommerce_product_image_id", "=", image_id)])
                if not woocommerce_product_image_id:
                    try:
                        response = requests.get(url, stream=True, verify=False, timeout=10)
                        if response.status_code == 200:
                            image = base64.b64encode(response.content)
                            key = hashlib.md5(image).hexdigest()
                            if key in generic_odoo_image_dict.keys():
                                woocommerce_product_image_id = setu_woocommerce_product_image_obj.create(
                                    {"setu_woocommerce_product_template_id": woocommerce_product_template_id.id,
                                     "setu_woocommerce_product_variant_id": woocommerce_product_variant_id.id,
                                     "setu_woocommerce_product_image_id": image_id,
                                     "setu_generic_product_image_id": generic_odoo_image_dict[key]})
                            else:
                                if not woocommerce_product_variant_id.odoo_product_id.image_1920 or prepare_product_dict.get(
                                        'is_image') == True:
                                    woocommerce_product_variant_id.odoo_product_id.image_1920 = image
                                    generic_product_image_id = woocommerce_product_variant_id.odoo_product_id.setu_generic_product_image_ids.filtered(
                                        lambda x: x.image == woocommerce_product_variant_id.odoo_product_id.image_1920)
                                else:
                                    generic_product_image_id = setu_generic_product_image_obj.create(
                                        {"name": woocommerce_product_template_id.name,
                                         "template_id": woocommerce_product_template_id.odoo_product_tmpl_id.id,
                                         "product_id": woocommerce_product_variant_id.odoo_product_id.id,
                                         "image": image, "url": url})
                                woocommerce_product_image_id = setu_woocommerce_product_image_obj.search(
                                    [("setu_woocommerce_product_template_id", "=", woocommerce_product_template_id.id),
                                     ("setu_woocommerce_product_variant_id", "=", woocommerce_product_variant_id.id),
                                     ("setu_generic_product_image_id", "=", generic_product_image_id.id)])
                                if woocommerce_product_image_id:
                                    woocommerce_product_image_id.setu_woocommerce_product_image_id = image_id
                    except Exception:
                        pass
            all_woocommerce_product_images = setu_woocommerce_product_image_obj.search(
                [("setu_woocommerce_product_template_id", "=", woocommerce_product_template_id.id),
                 ("setu_woocommerce_product_variant_id", "=", woocommerce_product_variant_id.id)])
            remove_obj += (all_woocommerce_product_images - woocommerce_product_image_id)
        remove_obj.sudo().unlink()
        return True

    @api.model
    def update_product_in_woocommerce(self, multi_ecommerce_connector_id, template_ids, is_update_basic_detail,
                                      is_update_price, is_update_image, is_update_publish, process_history_id):

        setu_process_history_line_obj = self.env["setu.process.history.line"]

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        batches = []

        if len(template_ids) > 100:
            batches += self.browse(self.process_to_prepare_batch_data(template_ids.ids))
        else:
            batches.append(template_ids)
        for batch_product_template_ids in batches:
            product_batch_update_dict = {'update': []}
            product_batch_update_lst = []

            for woocommerce_product_template_id in batch_product_template_ids:
                product_upload_payload = {'id': woocommerce_product_template_id.woocommerce_product_tmpl_id,
                                          'variations': [], "type": woocommerce_product_template_id.product_tmpl_type}
                if not is_update_publish:
                    product_upload_payload.update({
                        'status': 'publish' if woocommerce_product_template_id.is_product_template_published_website else 'draft'})
                elif is_update_publish == 'publish':
                    product_upload_payload.update({'status': 'publish'})
                else:
                    product_upload_payload.update({'status': 'draft'})

                product_upload_payload = self.create_simple_product_payload_data(woo_api_connect,
                                                                                 multi_ecommerce_connector_id,
                                                                                 woocommerce_product_template_id,
                                                                                 product_upload_payload,
                                                                                 is_update_basic_detail,
                                                                                 is_update_image, process_history_id)
                product_upload_payload = self.prepare_product_variant_dict(woo_api_connect,
                                                                           multi_ecommerce_connector_id,
                                                                           woocommerce_product_template_id,
                                                                           product_upload_payload,
                                                                           is_update_basic_detail, is_update_price,
                                                                           is_update_image, process_history_id)
                product_batch_update_lst.append(product_upload_payload)

            if product_batch_update_lst:
                product_batch_update_dict.update({'update': product_batch_update_lst})
                woo_update_product_api_response = woo_api_connect.post('products/batch', product_batch_update_dict)

                if not isinstance(woo_update_product_api_response, requests.models.Response):
                    message = "Invalid Response Format, %s" % woo_update_product_api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue

                if woo_update_product_api_response.status_code not in [200, 201]:
                    message = "Invalid Request Format, %s" % woo_update_product_api_response.content
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue
                else:
                    if is_update_publish == 'publish':
                        batch_product_template_ids.write({'is_product_template_published_website': True})
                    elif is_update_publish == 'unpublish':
                        batch_product_template_ids.write({'is_product_template_published_website': False})
                try:
                    woo_update_product_api_json_converted = woo_update_product_api_response.json()
                except Exception as e:
                    message = "Requests to resources that don't exist or are missing export Product Stock to WooCommerce for %s %s" % (
                        multi_ecommerce_connector_id.name, e)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                    continue

                if woo_update_product_api_json_converted.get('data', {}) and woo_update_product_api_json_converted.get(
                        'data', {}).get('status') != 200:
                    message = "Invalid Request Format, %s" % (woo_update_product_api_response.content)
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)

                    continue
                for woo_tmpl_id in woo_update_product_api_json_converted.get("update"):
                    if woo_tmpl_id.get("error"):
                        message = "Invalid Request Format, %s" % (woo_tmpl_id.get("error").get('message'))
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)
        return True

    def prepare_product_variant_dict(self, woo_api_connect, multi_ecommerce_connector_id,
                                     woocommerce_product_template_id, product_upload_payload, update_basic_detail,
                                     update_price, update_image, process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_woocommerce_product_attribute_terms_obj = self.env['setu.woocommerce.product.attribute.terms']

        model_id = setu_process_history_line_obj.get_model_id(self._name)
        variants_to_create = []
        for woocommerce_product_variant_id in woocommerce_product_template_id.setu_woocommerce_product_variant_ids:
            var_url = ''
            price = 0.0
            if woocommerce_product_variant_id.woocommerce_product_variant_id:
                info = {'id': woocommerce_product_variant_id.woocommerce_product_variant_id}
                if update_basic_detail:
                    weight = self.convert_weight_by_uom(woocommerce_product_variant_id.odoo_product_id.weight,
                                                        multi_ecommerce_connector_id)
                    info.update({'sku': woocommerce_product_variant_id.default_code, 'weight': str(weight),
                                 "manage_stock": woocommerce_product_variant_id.is_woocommerce_manage_stock})

                if update_image:
                    info.update(self.fetch_and_create_product_variant_image(multi_ecommerce_connector_id,
                                                                            woocommerce_product_variant_id))
            else:
                attributes = self.find_odoo_product_attribute(woocommerce_product_template_id.odoo_product_tmpl_id,
                                                              multi_ecommerce_connector_id, process_history_id)[0]
                info = self.prepare_product_variant_data(woocommerce_product_variant_id, multi_ecommerce_connector_id,
                                                         False)
            if update_price:
                price = woocommerce_product_template_id.fetch_odoo_product_price(
                    woocommerce_product_variant_id.multi_ecommerce_connector_id,
                    woocommerce_product_variant_id)
                info.update({'regular_price': str(price), 'sale_price': str(price)})

            if woocommerce_product_template_id.woocommerce_product_tmpl_id != woocommerce_product_variant_id.woocommerce_product_variant_id:
                if woocommerce_product_variant_id.woocommerce_product_variant_id:
                    product_upload_payload.get('variations').append(info)
                else:
                    variants_to_create.append(info)
            elif woocommerce_product_template_id.woocommerce_product_tmpl_id == woocommerce_product_variant_id.woocommerce_product_variant_id:
                del product_upload_payload['variations']

                if update_basic_detail:
                    product_upload_payload.update({'sku': woocommerce_product_variant_id.default_code,
                                                   "manage_stock": woocommerce_product_variant_id.is_woocommerce_manage_stock})
                    if var_url:
                        if multi_ecommerce_connector_id.is_woocommerce_image_url:
                            if product_upload_payload.get('images'):
                                product_upload_payload.get('images').insert(0, {'src': var_url, 'position': 0})
                            else:
                                product_upload_payload.update({'images': [{'src': var_url, 'position': 0}]})
                        else:
                            if product_upload_payload.get('images'):
                                product_upload_payload.get('images').insert(0, {'id': var_url, 'position': 0})
                            else:
                                product_upload_payload.update({'images': [{'id': var_url, 'position': 0}]})
                if update_price:
                    product_upload_payload.update({'regular_price': str(price), 'sale_price': str(price)})
        if product_upload_payload.get('variations'):
            variant_batches = self.process_to_prepare_batch_data(product_upload_payload.get('variations'))
            for woo_variants in variant_batches:
                api_response = woo_api_connect.post('products/%s/variations/batch' % (product_upload_payload.get('id')),
                                                    {'update': woo_variants})
                if api_response.status_code in [200, 201]:
                    del product_upload_payload['variations']
                if api_response.status_code not in [200, 201]:
                    message = "Invalid request format %s" % api_response
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
        if variants_to_create:
            if product_upload_payload.get("variations"):
                del product_upload_payload['variations']
            product_upload_payload.update({"attributes": attributes})
            api_response = woo_api_connect.put("products/%s" % (product_upload_payload.get("id")),
                                               product_upload_payload)
            api_response = woo_api_connect.post('products/%s/variations/batch' % (product_upload_payload.get('id')),
                                                {'create': variants_to_create})

            try:
                api_response_json = api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing importing Coupons to WooCommerce for %s %s" % (
                    multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return product_upload_payload

            for product in api_response_json.get("create"):
                if product.get("error"):
                    message = "Update Product \n%s" % (product.get("error").get('message'))
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)
                else:
                    variant_id = product.get("id")
                    sku = product.get("sku")
                    variant = woocommerce_product_template_id.setu_woocommerce_product_variant_ids.filtered(
                        lambda x: x.default_code == sku)
                    if variant:
                        variant.write({"woocommerce_product_variant_id": variant_id,
                                       "is_product_variant_exported_in_woocommerce": True})
            setu_woocommerce_product_attribute_terms_obj.create_and_sync_product_attribute_terms(
                multi_ecommerce_connector_id, process_history_id)
        return product_upload_payload

    def create_simple_product_payload_data(self, woo_api_connect, multi_ecommerce_connector_id,
                                           woocommerce_product_template_id, product_upload_payload, update_basic_detail,
                                           update_image, process_history_id):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']

        product_image_lst = []
        woocommerce_product_tags_lst = []
        woocommerce_product_category_lst = []

        if update_image:
            product_image_lst += self.find_woocommerce_product_images(multi_ecommerce_connector_id,
                                                                      woocommerce_product_template_id,
                                                                      woocommerce_product_template_id.odoo_product_tmpl_id)
            product_upload_payload.update({"images": product_image_lst})

        if update_basic_detail:
            weight = self.convert_weight_by_uom(woocommerce_product_template_id.odoo_product_tmpl_id.weight,
                                                multi_ecommerce_connector_id)
            description = ''
            short_description = ''
            if woocommerce_product_template_id.product_tmpl_description:
                woo_template_id = woocommerce_product_template_id.with_context(
                    lang=multi_ecommerce_connector_id.odoo_lang_id.code)
                description = woo_template_id.woo_description

            if woocommerce_product_template_id.product_short_tmpl_description:
                woo_template_id = woocommerce_product_template_id.with_context(
                    lang=multi_ecommerce_connector_id.odoo_lang_id.code)
                short_description = woo_template_id.product_short_tmpl_description

            product_upload_payload.update({'name': woocommerce_product_template_id.name,
                                           'enable_html_description': True,
                                           'enable_html_short_description': True, 'description': description,
                                           'short_description': short_description,
                                           'weight': str(weight),
                                           'taxable': woocommerce_product_template_id.is_product_template_taxable and 'true' or 'false'})

            woocommerce_product_category_lst += setu_woocommerce_product_category_obj.process_via_product_category_export_and_update(
                woocommerce_product_template_id, multi_ecommerce_connector_id, process_history_id)

            if woocommerce_product_category_lst:
                woocommerce_product_category_lst = list(set(woocommerce_product_category_lst))
                woocommerce_product_category_lst = [{'id': category_id} for category_id in
                                                    woocommerce_product_category_lst]
                product_upload_payload.update({'categories': woocommerce_product_category_lst})

            woocommerce_product_tags_lst += setu_woocommerce_product_tags_obj.process_via_product_tag_export_and_update(
                woocommerce_product_template_id, multi_ecommerce_connector_id, process_history_id)
            if woocommerce_product_tags_lst:
                woocommerce_product_tags_lst = list(set(woocommerce_product_tags_lst))
                woocommerce_product_tags_lst = [{'id': tag_id} for tag_id in woocommerce_product_tags_lst]
                product_upload_payload.update({'tags': woocommerce_product_tags_lst})

        return product_upload_payload

    def prepare_export_product_variant_payload(self, multi_ecommerce_connector_id, woocommerce_product_template_id,
                                               update_basic_detail, update_price, update_image, publish,
                                               process_history_id):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        setu_woocommerce_product_tags_obj = self.env['setu.woocommerce.product.tags']

        if update_basic_detail:
            woocommerce_product_tags_lst = []
            woocommerce_product_category_lst = []
            description = ''
            short_description = ''
            if woocommerce_product_template_id.product_tmpl_description:
                woo_template_id = woocommerce_product_template_id.with_context(
                    lang=multi_ecommerce_connector_id.odoo_lang_id.code)
                description = woo_template_id.woo_description

            if woocommerce_product_template_id.product_short_tmpl_description:
                woo_template_id = woocommerce_product_template_id.with_context(
                    lang=multi_ecommerce_connector_id.odoo_lang_id.code)
                short_description = woo_template_id.product_short_tmpl_description

            weight = self.convert_weight_by_uom(woocommerce_product_template_id.odoo_product_tmpl_id.weight,
                                                multi_ecommerce_connector_id)

            data = {'enable_html_description': True,
                    'enable_html_short_description': True,
                    'type': 'simple',
                    'name': woocommerce_product_template_id.name,
                    'description': description,
                    'weight': str(weight),
                    'short_description': short_description,
                    'taxable': woocommerce_product_template_id.is_product_template_taxable and 'true' or 'false',
                    'shipping_required': 'true'}

            woocommerce_product_category_lst += setu_woocommerce_product_category_obj.process_via_product_category_export_and_update(
                woocommerce_product_template_id, multi_ecommerce_connector_id, process_history_id)

            if woocommerce_product_category_lst:
                woocommerce_product_category_lst = list(set(woocommerce_product_category_lst))
                woocommerce_product_category_lst = [{'id': category_id} for category_id in
                                                    woocommerce_product_category_lst]
                data.update({'categories': woocommerce_product_category_lst})

            woocommerce_product_tags_lst += setu_woocommerce_product_tags_obj.process_via_product_tag_export_and_update(
                woocommerce_product_template_id, multi_ecommerce_connector_id, process_history_id)

            if woocommerce_product_tags_lst:
                woocommerce_product_tags_lst = list(set(woocommerce_product_tags_lst))
                woocommerce_product_tags_lst = [{'id': tag_id} for tag_id in woocommerce_product_tags_lst]
                data.update({'tags': woocommerce_product_tags_lst})

            attributes, is_variable = self.find_odoo_product_attribute(
                woocommerce_product_template_id.odoo_product_tmpl_id, multi_ecommerce_connector_id, process_history_id)

            if is_variable:
                data.update({'type': 'variable'})

            odoo_product_tmpl_id = woocommerce_product_template_id.odoo_product_tmpl_id
            if odoo_product_tmpl_id.attribute_line_ids:
                variations = []
                for woocommerce_product_variant_id in woocommerce_product_template_id.setu_woocommerce_product_variant_ids:
                    variation_data = {}
                    product_variant = self.prepare_product_variant_data(woocommerce_product_variant_id,
                                                                        multi_ecommerce_connector_id, update_image)
                    variation_data.update(product_variant)
                    if update_price:
                        if data.get('type') == 'simple':
                            data.update(self.fetch_odoo_product_price(multi_ecommerce_connector_id,
                                                                      woocommerce_product_variant_id))
                        else:
                            variation_data.update(self.fetch_odoo_product_price(multi_ecommerce_connector_id,
                                                                                woocommerce_product_variant_id))
                    variations.append(variation_data)
                default_att = variations and variations[0].get('attributes') or []
                data.update({'attributes': attributes, 'default_attributes': default_att, 'variations': variations})
                if data.get('type') == 'simple':
                    data.update({'sku': str(woocommerce_product_variant_id.default_code),
                                 "manage_stock": woocommerce_product_variant_id.is_woocommerce_manage_stock})
            else:
                woocommerce_product_variant_id = woocommerce_product_template_id.setu_woocommerce_product_variant_ids
                data.update(
                    self.prepare_product_variant_data(woocommerce_product_variant_id, multi_ecommerce_connector_id,
                                                      update_image))
                if update_price:
                    price = self.fetch_odoo_product_price(multi_ecommerce_connector_id, woocommerce_product_variant_id)
                    data.update({'regular_price': str(price), 'sale_price': str(price)})

        if publish == 'publish':
            data.update({'status': 'publish'})
        else:
            data.update({'status': 'draft'})

        if update_image:
            tmpl_images = []
            odoo_product_tmpl_id = woocommerce_product_template_id.odoo_product_tmpl_id
            tmpl_images += self.find_woocommerce_product_images(multi_ecommerce_connector_id,
                                                                woocommerce_product_template_id, odoo_product_tmpl_id)
            tmpl_images and data.update({"images": tmpl_images})
        return data

    @api.model
    def find_woocommerce_product_images(self, multi_ecommerce_connector_id, woocommerce_product_template_id,
                                        odoo_template_id):

        tmpl_images = []
        position = 0
        gallery_img_keys = {}
        gallery_images = woocommerce_product_template_id.setu_woocommerce_product_image_ids.filtered(
            lambda x: not x.setu_woocommerce_product_variant_id)
        for br_gallery_image in gallery_images:
            image_id = br_gallery_image.setu_woocommerce_product_image_id
            img_url = ''
            if br_gallery_image.image and not image_id:
                key = hashlib.md5(br_gallery_image.image).hexdigest()
                if not key:
                    continue
                if key in gallery_img_keys:
                    continue
                else:
                    gallery_img_keys.update({key: br_gallery_image.id})
                res = ImageUploader.upload_image(multi_ecommerce_connector_id, br_gallery_image.image,
                                                 "%s_%s_%s" % (
                                                     odoo_template_id.name, odoo_template_id.categ_id.name,
                                                     odoo_template_id.id))
                image_id = res and res.get('id', False) or ''
            if image_id:
                tmpl_images.append({'id': image_id, 'position': position})
                position += 1
                br_gallery_image.setu_woocommerce_product_image_id = image_id
        return tmpl_images

    @api.model
    def find_odoo_product_attribute(self, odoo_template_id, multi_ecommerce_connector_id, process_history_id):
        setu_woocommerce_product_attributes_obj = self.env['setu.woocommerce.product.attributes']
        position = 0
        is_variable = False
        attributes = []
        for attribute_line in odoo_template_id.attribute_line_ids:
            options = []
            for option in attribute_line.value_ids:
                options.append(option.name)
            variation = False
            if attribute_line.attribute_id.create_variant in ['always', 'dynamic']:
                variation = True
            attribute_data = {'name': attribute_line.attribute_id.name,
                              'slug': attribute_line.attribute_id.name.lower(),
                              'position': position,
                              'visible': True,
                              'variation': variation,
                              'options': options}

            if multi_ecommerce_connector_id.woocommerce_attribute_type == 'select':
                attrib_data = setu_woocommerce_product_attributes_obj.process_via_product_attributes_export_and_update(
                    attribute_line.attribute_id, multi_ecommerce_connector_id, process_history_id)

                if not attrib_data:
                    break
                attribute_data.update({'id': attrib_data.get(attribute_line.attribute_id.id)})
            elif multi_ecommerce_connector_id.woocommerce_attribute_type == 'text':
                attribute_data.update({'name': attribute_line.attribute_id.name})
            position += 1
            if attribute_line.attribute_id.create_variant in ['always', 'dynamic']:
                is_variable = True
            attributes.append(attribute_data)
        return attributes, is_variable

    def convert_weight_by_uom(self, weight, multi_ecommerce_connector_id, import_process=False):
        woo_weight_uom = multi_ecommerce_connector_id.woocommerce_weight_uom_id
        product_weight_uom = self.env.ref("uom.product_uom_lb") if self.env["ir.config_parameter"].sudo().get_param(
            "product.weight_in_lbs") == '1' else self.env.ref("uom.product_uom_kgm")

        if woo_weight_uom != product_weight_uom:
            if import_process:
                weight = woo_weight_uom._compute_quantity(weight, product_weight_uom)
            else:
                weight = product_weight_uom._compute_quantity(weight, woo_weight_uom)
        return weight

    # ===========================================================================
    # Export Product ERP to Woocommerce
    # ===========================================================================

    @api.model
    def export_product_in_woocommerce(self, multi_ecommerce_connector_id, woocommerce_product_template_ids,
                                      is_set_basic_detail, is_set_price, is_set_images, is_publish, process_history_id):
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_attribute_terms_obj = self.env['setu.woocommerce.product.attribute.terms']

        model_id = setu_process_history_line_obj.get_model_id(self._name)

        woo_api_connect = multi_ecommerce_connector_id.connect_with_woocommerce()
        variants = []
        for woocommerce_product_template_id in woocommerce_product_template_ids:
            odoo_product_tmpl_id = woocommerce_product_template_id.odoo_product_tmpl_id
            data = self.prepare_export_product_variant_payload(multi_ecommerce_connector_id,
                                                               woocommerce_product_template_id, is_set_basic_detail,
                                                               is_set_price, is_set_images, is_publish,
                                                               process_history_id)

            variants = data.get('variations') or []
            variants and data.update({'variations': []})
            api_response = woo_api_connect.post('products', data)
            if not isinstance(api_response, requests.models.Response):
                message = "Invalid Response Format, %s" % (api_response)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)

                continue
            if api_response.status_code not in [200, 201]:
                message = "Invalid Request Format, %s" % (api_response.content)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)

                continue
            try:
                api_response_json_data = api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing import product attribute to WooCommerce for %s %s" % (
                    multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            if api_response_json_data.get('data', {}) and api_response_json_data.get('data', {}).get('status') not in [
                200, 201]:
                message = api_response_json_data.get('message')
                if api_response_json_data.get('code') == 'woocommerce_rest_product_sku_already_exists':
                    message = "%s, ==> %s" % (message, data.get('name'))
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                continue
            if not isinstance(api_response_json_data, dict):
                message = "Invalid Response Format, %s" % api_response_json_data
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)

                continue
            response_variations = []
            woocommerce_product_tmpl_id = api_response_json_data.get('id')

            if variants:
                response_variations = []
                variant_batches = []
                start, end = 0, 100
                if len(variants) > 100:
                    while True:
                        w_products_ids = variants[start:end]
                        if not w_products_ids:
                            break
                        temp = end + 100
                        start, end = end, temp
                        if w_products_ids:
                            variant_batches.append(w_products_ids)
                else:
                    variant_batches.append(variants)
                for woo_variants in variant_batches:
                    for variant in woo_variants:
                        if variant.get('image'):
                            variant.update({'image': variant.get('image')})
                    api_response = woo_api_connect.post("products/%s/variations/batch" % woocommerce_product_tmpl_id,
                                                        {'create': woo_variants})

                    if api_response.status_code not in [200, 201]:
                        message = "Invalid Request Format, %s" % api_response.content
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)

                        continue
                    try:
                        response_variations += api_response.json().get('create')
                    except Exception as e:
                        message = "Requests to resources that don't exist or are missing import product attribute to WooCommerce for %s %s" % multi_ecommerce_connector_id.name, e
                        setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                              process_history_id)
                        continue

            for response_variation in response_variations:
                if response_variation.get('error'):
                    message = "Invalid Request Format, %s" % response_variation.get('error')
                    setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                          process_history_id)

                    continue
                response_variant_data = {}
                variant_sku = response_variation.get('sku')
                variant_id = response_variation.get('id')
                variant_created_at = response_variation.get('date_created').replace('T', ' ')
                variant_updated_at = response_variation.get('date_modified').replace('T', ' ')
                woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.search(
                    [('default_code', '=', variant_sku),
                     ('setu_woocommerce_product_template_id', '=', woocommerce_product_template_id.id),
                     ('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id)])
                response_variant_data.update(
                    {'woocommerce_product_variant_id': variant_id, 'product_variant_created_at': variant_created_at,
                     'product_variant_modified_at': variant_updated_at,
                     'is_product_variant_exported_in_woocommerce': True})
                woocommerce_product_variant_id and woocommerce_product_variant_id.write(response_variant_data)
            created_at = api_response_json_data.get('date_created').replace('T', ' ')
            updated_at = api_response_json_data.get('date_modified').replace('T', ' ')

            if odoo_product_tmpl_id.product_variant_count == 1 and not odoo_product_tmpl_id.attribute_line_ids:
                woocommerce_product_variant_id = woocommerce_product_template_id.setu_woocommerce_product_variant_ids
                woocommerce_product_variant_id.write({'woocommerce_product_variant_id': woocommerce_product_tmpl_id,
                                                      'product_variant_created_at': created_at or False,
                                                      'product_variant_modified_at': updated_at or False,
                                                      'is_product_variant_exported_in_woocommerce': True})

            total_variants_in_woo = api_response_json_data.get('variations') and len(
                api_response_json_data.get('variations')) or 1
            tmpl_data = {'woocommerce_product_tmpl_id': woocommerce_product_tmpl_id,
                         'product_tmpl_created_at': created_at or False,
                         'product_tmpl_modified_at': updated_at or False,
                         'is_product_template_exported_in_woocommerce': True,
                         'total_variants_in_woocommerce': total_variants_in_woo}
            tmpl_data.update(
                {'is_product_template_published_website': True}) if is_publish == 'publish' else tmpl_data.update(
                {'is_product_template_published_website': False})
            woocommerce_product_template_id.write(tmpl_data)
            setu_woocommerce_product_attribute_terms_obj.create_and_sync_product_attribute_terms(
                multi_ecommerce_connector_id, process_history_id)
            self._cr.commit()
        return True

    # ===============================================================================
    # Methods which Define Un Publish WooCommerce Product
    # ===============================================================================

    def woocommerce_product_unpublish(self):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                         self.multi_ecommerce_connector_id,
                                                                                         model_id)

        woo_api_connect = self.multi_ecommerce_connector_id.connect_with_woocommerce()

        if self.woocommerce_product_tmpl_id:
            woocommerce_product_tmpl_dict = {'status': 'draft'}
            woo_product_unpublish_api_response = woo_api_connect.put('products/%s' % (self.woocommerce_product_tmpl_id),
                                                                     woocommerce_product_tmpl_dict)
            if not isinstance(woo_product_unpublish_api_response, requests.models.Response):
                message = "Invalid Response Format, %s" % (woo_product_unpublish_api_response)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True
            if woo_product_unpublish_api_response.status_code not in [200, 201]:
                message = "Invalid Request Format, %s" % (woo_product_unpublish_api_response.content)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True
            try:
                woo_product_unpublish_api_response_data = woo_product_unpublish_api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing unpublish product to WooCommerce for %s %s" % (
                    self.multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False
            if woo_product_unpublish_api_response_data.get('data', {}) and woo_product_unpublish_api_response_data.get(
                    'data', {}).get('status') not in [200, 201]:
                message = woo_product_unpublish_api_response_data.get('message')
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
            else:
                self.write({'is_product_template_published_website': False})

        return True

    # ===============================================================================
    # Methods which Define Publish WooCommerce Product
    # ===============================================================================

    def woocommerce_product_publish(self):
        setu_process_history_obj = self.env["setu.process.history"]
        setu_process_history_line_obj = self.env["setu.process.history.line"]
        model_id = setu_process_history_line_obj.get_model_id(self._name)
        process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                         self.multi_ecommerce_connector_id,
                                                                                         model_id)
        woo_api_connect = self.multi_ecommerce_connector_id.connect_with_woocommerce()

        if self.woocommerce_product_tmpl_id:
            woocommerce_product_tmpl_dict = {'status': 'publish'}
            woo_product_publish_api_response = woo_api_connect.put('products/%s' % (self.woocommerce_product_tmpl_id),
                                                                   woocommerce_product_tmpl_dict)
            if not isinstance(woo_product_publish_api_response, requests.models.Response):
                message = "Invalid Response Format, %s" % (woo_product_publish_api_response)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True

            if woo_product_publish_api_response.status_code not in [200, 201]:
                message = "Invalid Request Format, %s" % (woo_product_publish_api_response.content)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return True
            try:
                woo_product_publish_api_response_data = woo_product_publish_api_response.json()
            except Exception as e:
                message = "Requests to resources that don't exist or are missing unpublish product to WooCommerce for %s %s" % (
                    self.multi_ecommerce_connector_id.name, e)
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
                return False

            if woo_product_publish_api_response_data.get('data', {}) and woo_product_publish_api_response_data.get(
                    'data', {}).get('status') not in [200, 201]:
                message = woo_product_publish_api_response_data.get('message')
                setu_process_history_line_obj.woocommerce_common_process_history_line(message, model_id,
                                                                                      process_history_id)
            else:
                self.write({'is_product_template_published_website': True})
        return True
