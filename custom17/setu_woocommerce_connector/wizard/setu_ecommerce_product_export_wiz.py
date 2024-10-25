# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError
from _collections import OrderedDict
from datetime import datetime, timedelta


class SetuEcommerceProductExportWiz(models.TransientModel):
    _inherit = 'setu.ecommerce.product.export.wiz'

    def woocommerce_connector_prepare_product_export_to_ecommerce(self):
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_process_history_line_obj = self.env['setu.process.history.line']
        setu_process_history_obj = self.env["setu.process.history"]
        product_obj = self.env['product.product']

        model_id = setu_process_history_line_obj.get_model_id(setu_woocommerce_product_template_obj._name)

        active_template_ids = self.env["product.template"].browse(self._context.get("active_ids", []))
        odoo_product_template_ids = active_template_ids.filtered(lambda template: template.type == "product") #mightchange
        if not odoo_product_template_ids:
            raise ValidationError(_("It seems like selected products are not Storable Products."))

        self.prepare_for_export_product_in_woocommerce(odoo_product_template_ids)
        if self.export_action == 'create_and_sync':
            pending_exported_woocommerce_template_ids = setu_woocommerce_product_template_obj.search(
                [('odoo_product_tmpl_id', 'in', odoo_product_template_ids.ids),
                 ('is_product_template_exported_in_woocommerce', '=', False),
                 ('multi_ecommerce_connector_id', '=', self.multi_ecommerce_connector_id.id)])

            if pending_exported_woocommerce_template_ids:
                if pending_exported_woocommerce_template_ids and len(
                        pending_exported_woocommerce_template_ids) > 80:
                    raise ValidationError(_("For better performance please select only 80 records to export."))
                process_history_id = setu_process_history_obj.create_woocommerce_process_history("export",
                                                                                                 self.multi_ecommerce_connector_id,
                                                                                                 model_id)

                setu_woocommerce_product_template_obj.export_product_in_woocommerce(
                    multi_ecommerce_connector_id=self.multi_ecommerce_connector_id,
                    woocommerce_product_template_ids=pending_exported_woocommerce_template_ids,
                    is_set_basic_detail=self.basic_details,
                    is_set_price=self.price_export,
                    is_set_images=self.set_image,
                    is_publish='publish',
                    process_history_id=process_history_id)
        elif self.export_action == 'sync_only':
            pending_updated_woocommerce_template_ids = setu_woocommerce_product_template_obj.search(
                [('odoo_product_tmpl_id', 'in', odoo_product_template_ids.ids),
                 ('is_product_template_exported_in_woocommerce', '=', True),
                 ('multi_ecommerce_connector_id', '=', self.multi_ecommerce_connector_id.id)])
            if pending_updated_woocommerce_template_ids:
                if pending_updated_woocommerce_template_ids and len(pending_updated_woocommerce_template_ids) > 80:
                    raise ValidationError(_("For better performance please select only 80 records to export."))

                process_history_id = setu_process_history_obj.create_woocommerce_process_history("update",
                                                                                                 self.multi_ecommerce_connector_id,
                                                                                                 model_id)
                setu_woocommerce_product_template_obj.update_product_in_woocommerce(
                    multi_ecommerce_connector_id=self.multi_ecommerce_connector_id,
                    template_ids=pending_updated_woocommerce_template_ids,
                    is_update_basic_detail=self.basic_details,
                    is_update_price=self.price_export,
                    is_update_image=self.set_image,
                    is_update_publish="publish",
                    process_history_id=process_history_id)

        if self.inventory_export:
            export_stock_from_date = datetime.now() - timedelta(3)
            product_ids = product_obj.product_stock_movement(export_stock_from_date,
                                                             self.multi_ecommerce_connector_id.odoo_company_id)
            woocommerce_product_template_ids = setu_woocommerce_product_variant_obj.search(
                [('odoo_product_id', 'in', product_ids),
                 ('is_woocommerce_manage_stock', '=', True)]).setu_woocommerce_product_template_id.filtered(lambda
                                                                                                                x: x.multi_ecommerce_connector_id == self.multi_ecommerce_connector_id and x.is_product_template_exported_in_woocommerce == True)
            if woocommerce_product_template_ids:
                setu_woocommerce_product_variant_obj.with_context(
                    update_stock_inventory=product_ids).export_product_stock_to_woocommerce(
                    self.multi_ecommerce_connector_id, woocommerce_product_template_ids)
        return True

    def prepare_for_export_product_in_woocommerce(self, odoo_product_template_ids):
        woocommerce_template_id = False
        setu_woocommerce_product_template_obj = self.env['setu.woocommerce.product.template']
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_image_obj = self.env["setu.woocommerce.product.image"]
        woocommerce_category_dict = {}

        multi_ecommerce_connector_id = self.multi_ecommerce_connector_id

        for product_variant_id in odoo_product_template_ids.product_variant_ids:
            if not product_variant_id.default_code:
                continue
            product_template_id = product_variant_id.product_tmpl_id
            if product_template_id.attribute_line_ids and len(product_template_id.attribute_line_ids.filtered(
                    lambda x: x.attribute_id.create_variant == "always")) > 0:
                product_type = 'variable'
            else:
                product_type = 'simple'
            existing_woocommerce_template_id = setu_woocommerce_product_template_obj.search(
                [("multi_ecommerce_connector_id", "=", multi_ecommerce_connector_id.id),
                 ("odoo_product_tmpl_id", "=", product_template_id.id)])
            woo_product_template_vals = ({'odoo_product_tmpl_id': product_template_id.id,
                                          'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                                          'name': product_template_id.name,
                                          "active": True,
                                          'product_tmpl_type': product_type})
            if multi_ecommerce_connector_id.is_use_default_product_description:
                woo_product_template_vals.update({"product_tmpl_description": product_template_id.description_sale,
                                                  "product_short_tmpl_description": product_template_id.description})
            if product_template_id.categ_id:
                category_id = product_template_id.categ_id
                woocommerce_category_dict = self.create_product_category_for_woocommerce(category_id,
                                                                                         multi_ecommerce_connector_id,
                                                                                         woocommerce_category_dict)
                woo_category_id = self.update_product_category(product_template_id.categ_id,
                                                               multi_ecommerce_connector_id)
                woo_product_template_vals.update(
                    {'setu_woocommerce_product_category_ids': [(6, 0, woo_category_id.ids)]})
            if not existing_woocommerce_template_id:
                existing_woocommerce_template_id = setu_woocommerce_product_template_obj.create(
                    woo_product_template_vals)
                woocommerce_template_id = existing_woocommerce_template_id.id
            else:
                if woocommerce_template_id != existing_woocommerce_template_id.id:
                    existing_woocommerce_template_id.write(woo_product_template_vals)
                    woocommerce_template_id = existing_woocommerce_template_id.id

            woocommerce_product_image_lst = []
            product_template_id = existing_woocommerce_template_id.odoo_product_tmpl_id
            if product_template_id.setu_generic_product_image_ids:
                for generic_product_image_id in product_template_id.setu_generic_product_image_ids.filtered(
                        lambda x: not x.product_id):
                    woo_product_image = setu_woocommerce_product_image_obj.search_read(
                        [("setu_woocommerce_product_template_id", "=", woocommerce_template_id),
                         ("setu_generic_product_image_id", "=", generic_product_image_id.id)], ["id"])
                    if not woo_product_image:
                        woocommerce_product_image_lst.append(
                            {"setu_generic_product_image_id": generic_product_image_id.id,
                             "setu_woocommerce_product_template_id": woocommerce_template_id})
                if woocommerce_product_image_lst:
                    setu_woocommerce_product_image_obj.create(woocommerce_product_image_lst)
            woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.search(
                [('multi_ecommerce_connector_id', '=', multi_ecommerce_connector_id.id),
                 ('odoo_product_id', '=', product_variant_id.id),
                 ('setu_woocommerce_product_template_id', '=', existing_woocommerce_template_id.id)])
            woocommerce_product_variant_vals = (
                {'multi_ecommerce_connector_id': multi_ecommerce_connector_id.id,
                 'odoo_product_id': product_variant_id.id,
                 'setu_woocommerce_product_template_id': existing_woocommerce_template_id and existing_woocommerce_template_id.id,
                 'default_code': product_variant_id.default_code,
                 'name': product_variant_id.name})
            if not woocommerce_product_variant_id:
                woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.create(
                    woocommerce_product_variant_vals)
            else:
                woocommerce_product_variant_id.write(woocommerce_product_variant_vals)
            odoo_product_id = woocommerce_product_variant_id.odoo_product_id
            odoo_image = odoo_product_id.setu_generic_product_image_ids
            if odoo_image:
                woocommerce_product_image_id = setu_woocommerce_product_image_obj.search_read(
                    [("setu_woocommerce_product_template_id", "=", woocommerce_template_id),
                     ("setu_woocommerce_product_variant_id", "=", woocommerce_product_variant_id.id),
                     ("setu_generic_product_image_id", "=", odoo_image[0].id)], ["id"])
                if not woocommerce_product_image_id:
                    setu_woocommerce_product_image_obj.create(
                        {"setu_generic_product_image_id": odoo_image[0].id,
                         "setu_woocommerce_product_variant_id": woocommerce_product_variant_id.id,
                         "setu_woocommerce_product_template_id": woocommerce_template_id})
        return True

    def create_product_category_for_woocommerce(self, category_id, multi_ecommerce_connector_id,
                                                woocommerce_category_dict, list_of_category=[]):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        product_category_obj = self.env['product.category']

        if category_id:
            list_of_category.append(category_id.id)
            parent_category_id = category_id.parent_id
            self.create_product_category_for_woocommerce(parent_category_id, multi_ecommerce_connector_id,
                                                         woocommerce_category_dict, list_of_category=list_of_category)
        else:
            for category_id in list(OrderedDict.fromkeys(reversed(list_of_category))):
                if woocommerce_category_dict.get((category_id, multi_ecommerce_connector_id.id)):
                    continue
                list_category_id = product_category_obj.browse(category_id)
                parent_category_id = list_category_id.parent_id
                woocommerce_product_parent_category_id = parent_category_id and setu_woocommerce_product_category_obj.search(
                    [('name', '=', parent_category_id.name), ('multi_ecommerce_connector_id', '=',
                                                              multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                    limit=1) or False

                if woocommerce_product_parent_category_id:
                    woocommerce_product_category_id = setu_woocommerce_product_category_obj.search(
                        [('name', '=', list_category_id.name),
                         ('parent_id', '=', woocommerce_product_parent_category_id.id), (
                             'multi_ecommerce_connector_id', '=',
                             multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)], limit=1)
                    woocommerce_category_dict.update(
                        {(category_id, multi_ecommerce_connector_id.id): woocommerce_product_category_id.id})
                else:
                    woocommerce_product_category_id = setu_woocommerce_product_category_obj.search(
                        [('name', '=', list_category_id.name), ('multi_ecommerce_connector_id', '=',
                                                                multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                        limit=1)
                    woocommerce_category_dict.update(
                        {(category_id, multi_ecommerce_connector_id.id): woocommerce_product_category_id.id})
                if not woocommerce_product_category_id:
                    if not parent_category_id:
                        parent_category_id = setu_woocommerce_product_category_obj.create(
                            {'name': list_category_id.name,
                             'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
                        woocommerce_category_dict.update(
                            {(category_id, multi_ecommerce_connector_id.id): parent_category_id.id})
                    else:
                        parent_id = setu_woocommerce_product_category_obj.search(
                            [('name', '=', parent_category_id.name), ('multi_ecommerce_connector_id', '=',
                                                                      multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
                            limit=1)
                        woocommerce_product_category_id = setu_woocommerce_product_category_obj.create(
                            {'name': list_category_id.name,
                             'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id,
                             'parent_id': parent_id.id})
                        woocommerce_category_dict.update(
                            {(category_id, multi_ecommerce_connector_id.id): woocommerce_product_category_id.id})
                elif not woocommerce_product_category_id.parent_id and parent_category_id:
                    parent_category_id = setu_woocommerce_product_category_obj.search(
                        [('name', '=', parent_category_id.name), ('parent_id', '=', parent_category_id.id), (
                            'multi_ecommerce_connector_id', '=',
                            multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)])
                    if not parent_category_id:
                        woo_cat_id = setu_woocommerce_product_category_obj.create({'name': list_category_id.name,
                                                                                   'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
                        woocommerce_category_dict.update(
                            {(category_id, multi_ecommerce_connector_id.id): woo_cat_id.id})
                    if not parent_category_id.parent_id.id == woocommerce_product_category_id.id and woocommerce_product_category_id.multi_ecommerce_connector_id.id == multi_ecommerce_connector_id.id:
                        woocommerce_product_category_id.write({'parent_id': parent_category_id.id})
                        woocommerce_category_dict.update(
                            {(category_id, multi_ecommerce_connector_id.id): parent_category_id.id})
        return woocommerce_category_dict

    def update_product_category(self, woocommerce_product_category_id, multi_ecommerce_connector_id):
        setu_woocommerce_product_category_obj = self.env['setu.woocommerce.product.category']
        product_category_id = setu_woocommerce_product_category_obj.search(
            [('name', '=', woocommerce_product_category_id.name), ('multi_ecommerce_connector_id', '=',
                                                                   multi_ecommerce_connector_id and multi_ecommerce_connector_id.id)],
            limit=1)
        if product_category_id and product_category_id.name != woocommerce_product_category_id.name:
            product_category_id.write({'name': woocommerce_product_category_id.name})
        else:
            product_category_id = setu_woocommerce_product_category_obj.create(
                {'name': woocommerce_product_category_id.name,
                 'multi_ecommerce_connector_id': multi_ecommerce_connector_id and multi_ecommerce_connector_id.id})
        return product_category_id
