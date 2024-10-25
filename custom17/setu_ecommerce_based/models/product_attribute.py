# -*- coding: utf-8 -*-
from odoo import models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def get_create_product_attribute(self, attr_name_lst, variant_dict, product_template_id):
        product_attribute_lst = []
        for attribute_dict in attr_name_lst:
            product_attribute_id = self.search_or_create_product_attribute(attribute_dict.get("name"),
                                                                           is_create_new_attribute=True)[0]
            product_attribute_lst.append(product_attribute_id and product_attribute_id.id)
        template_attributes_lst = self.prepare_template_attribute_value_domain(product_attribute_lst, variant_dict,
                                                                               product_template_id)
        if len(product_attribute_lst) != len(template_attributes_lst):
            return []
        return template_attributes_lst

    def prepare_and_create_product_attribute(self, list_dict):
        product_attribute_value_obj = self.env["product.attribute.value"]
        attribute_line_lst = []
        for attr_dict in list_dict.get("options"):
            attr_name = attr_dict.get("name")
            attr_values = attr_dict.get("values")
            attribute = self.search_or_create_product_attribute(attr_name, is_create_new_attribute=True)[0]
            attr_val_lst = []
            for attr_value in attr_values:
                attribute_value = product_attribute_value_obj.search_or_create_product_attribute_value(attr_value,
                                                                                                       attribute,
                                                                                                       is_create_new_attribute_value=True)
                if attribute_value:
                    attribute_value = attribute_value[0]
                    attr_val_lst.append(attribute_value.id)
            if attr_val_lst:
                attribute_line_ids_data = [0, False,
                                           {"attribute_id": attribute.id, "value_ids": [[6, False, attr_val_lst]]}]
                attribute_line_lst.append(attribute_line_ids_data)
        return attribute_line_lst

    def prepare_template_attribute_value_domain(self, product_attribute_list, variant_dict, product_template_id):
        template_attribute_value_domain = []
        product_attribute_value_obj = self.env["product.attribute.value"]
        product_template_attribute_value_obj = self.env["product.template.attribute.value"]
        counter = 0
        for product_attribute_id in product_attribute_list:
            counter += 1
            attribute_name = "option" + str(counter)
            attribute_val = variant_dict.get(attribute_name)
            product_attribute_id = product_attribute_value_obj.browse(product_attribute_id)
            product_attribute_value_id = product_attribute_value_obj.search_or_create_product_attribute_value(
                attribute_val, product_attribute_id, is_create_new_attribute_value=True)
            if product_attribute_value_id:
                template_attribute_value_id = product_template_attribute_value_obj.search(
                    [("product_attribute_value_id", "=", product_attribute_value_id.id),
                     ("attribute_id", "=", product_attribute_id and product_attribute_id.id),
                     ("product_tmpl_id", "=", product_template_id and product_template_id.id)], limit=1)
                if template_attribute_value_id:
                    domain = ("product_template_attribute_value_ids", "=", template_attribute_value_id.id)
                    template_attribute_value_domain.append(domain)

        return template_attribute_value_domain

    def search_or_create_product_attribute(self, attribute_name, attribute_type='radio', create_variant='always',
                                           is_create_new_attribute=False):
        product_attribute_ids = self.search(
            [('name', '=ilike', attribute_name), ('create_variant', '=', create_variant)], limit=1)
        if not product_attribute_ids and is_create_new_attribute:
            return self.create(
                ({'name': attribute_name, 'create_variant': create_variant, 'display_type': attribute_type}))
        return product_attribute_ids
