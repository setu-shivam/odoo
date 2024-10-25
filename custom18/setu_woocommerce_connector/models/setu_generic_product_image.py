from odoo import fields, models, api


class SetuGenericProductImage(models.Model):
    _inherit = 'setu.generic.product.image'

    @api.model
    def create(self, vals):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_image_obj = self.env["setu.woocommerce.product.image"]
        setu_woocommerce_product_template_obj = self.env["setu.woocommerce.product.template"]

        res = super(SetuGenericProductImage, self).create(vals)

        if self.env.user.has_group('setu_woocommerce_connector.group_setu_woocommerce_connector_user'):
            woocommerce_product_image_vals = {"setu_generic_product_image_id": res.id}
            if vals.get("product_id", False):
                woocommerce_variant_ids = setu_woocommerce_product_variant_obj.search_read(
                    [('odoo_product_id', '=', vals.get("product_id"))], ["id", "setu_woocommerce_product_template_id"])
                for woocommerce_variant_id in woocommerce_variant_ids:
                    woocommerce_product_image_vals.update(
                        {"setu_woocommerce_product_variant_id": woocommerce_variant_id["id"],
                         "setu_woocommerce_product_template_id":
                             woocommerce_variant_id["setu_woocommerce_product_template_id"][0],
                         "sequence": 0})
                    setu_woocommerce_product_image_obj.create(woocommerce_product_image_vals)

            elif vals.get("template_id", False):
                if self._context.get("main_image"):
                    woocommerce_product_image_vals.update({"sequence": 0})
                woocommerce_product_template_ids = setu_woocommerce_product_template_obj.search_read(
                    [("odoo_product_tmpl_id", "=", vals.get("template_id"))], ["id"])
                for woocommerce_product_template_id in woocommerce_product_template_ids:
                    woocommerce_product_image_vals.update(
                        {'setu_woocommerce_product_template_id': woocommerce_product_template_id["id"]})
                    setu_woocommerce_product_image_obj.create(woocommerce_product_image_vals)
        return res

    def write(self, vals):
        setu_woocommerce_product_variant_obj = self.env['setu.woocommerce.product.variant']
        setu_woocommerce_product_image_obj = self.env["setu.woocommerce.product.image"]
        res = super(SetuGenericProductImage, self).write(vals)

        if self.env.user.has_group('setu_woocommerce_connector.group_setu_woocommerce_connector_user'):
            for record_id in self:
                setu_woocommerce_product_image_obj += setu_woocommerce_product_image_obj.search(
                    [("setu_generic_product_image_id", "=", record_id.id)])
            if setu_woocommerce_product_image_obj:
                if not vals.get("product_id", ""):
                    setu_woocommerce_product_image_obj.write({'setu_woocommerce_product_variant_id': False})
                elif vals.get("product_id", ""):
                    for setu_woocommerce_product_image_id in setu_woocommerce_product_image_obj:
                        setu_woocommerce_product_variant_id = setu_woocommerce_product_variant_obj.search_read(
                            [("odoo_product_id", "=", vals.get("product_id")), (
                                "setu_woocommerce_product_template_id", "=",
                                setu_woocommerce_product_image_id.setu_woocommerce_product_template_id.id)], ["id"])
                        if setu_woocommerce_product_variant_id:
                            setu_woocommerce_product_image_id.write(
                                {"setu_woocommerce_product_variant_id": setu_woocommerce_product_variant_id["id"]})
        return res
