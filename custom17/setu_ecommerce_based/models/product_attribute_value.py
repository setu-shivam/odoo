# -*- coding: utf-8 -*-
from odoo import models


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def prepare_template_attribute_values(self, variation_attributes, product_template):
        template_attribute_value_lst = []
        product_attribute_value_id = False
        product_attribute_obj = self.env["product.attribute"]
        product_template_attribute_value_obj = self.env["product.template.attribute.value"]
        for variation_attribute in variation_attributes:
            attribute_val = variation_attribute.get("option")
            attribute_name = variation_attribute.get("name")
            product_attribute = product_attribute_obj.search([("name", "=ilike", attribute_name)], limit=1)
            if product_attribute:
                product_attribute_value_id = self.search_or_create_product_attribute_value(attribute_val,
                                                                                           product_attribute)
            if product_attribute_value_id:
                product_attribute_value_id = product_attribute_value_id[0]
                template_attribute_value_id = product_template_attribute_value_obj.search(
                    [("product_attribute_value_id", "=", product_attribute_value_id.id),
                     ("attribute_id", "=", product_attribute.id), ("product_tmpl_id", "=", product_template.id)],
                    limit=1)
                template_attribute_value_id and template_attribute_value_lst.append(template_attribute_value_id.id)
        return template_attribute_value_lst

    def search_or_create_product_attribute_value(self, name, attribute_id, is_create_new_attribute_value=False):
        attribute_value_ids = self.search(
            [('name', '=', name), ('attribute_id', '=', attribute_id and attribute_id.id)], limit=1)
        if not attribute_value_ids:
            attribute_value_ids = self.search(
                [('name', '=ilike', name), ('attribute_id', '=', attribute_id and attribute_id.id)], limit=1)
        if not attribute_value_ids and is_create_new_attribute_value:
            return self.create(({'name': name, 'attribute_id': attribute_id and attribute_id.id}))
        return attribute_value_ids
