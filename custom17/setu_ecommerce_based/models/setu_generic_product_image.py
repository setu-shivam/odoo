# -*- coding: utf-8 -*-
import base64

import requests
from odoo import models, fields, api, _


class SetuGenericProductImage(models.Model):
    _name = 'setu.generic.product.image'
    _description = 'Generic Product Image'
    _order = 'sequence, id'

    name = fields.Char(string="Image Name", translate=True)
    image = fields.Image(string="Image")
    url = fields.Char(string="Image URL", translate=True)
    sequence = fields.Integer(string="Sequence", index=True, default=10)
    product_id = fields.Many2one('product.product', string="Product ID", ondelete='cascade')
    template_id = fields.Many2one('product.template', string='Product Template ID', ondelete='cascade')

    @api.model
    def default_get(self, fields):
        fields += ["template_id", "product_id"]
        return super(SetuGenericProductImage, self).default_get(fields)

    @api.onchange('url')
    def _onchange_url(self):
        if not self.url:
            self.image = False
            return {}
        image_types = ["image/jpeg", "image/png", "image/tiff", "image/vnd.microsoft.icon",
                       "image/x-icon"  "image/vnd.djvu", "image/svg+xml", "image/gif"],
        try:
            response = requests.get(self.url, stream=True, verify=False, timeout=10)
            if (response.status_code == 200 and response.headers["Content-Type"] in image_types):
                image = base64.b64encode(response.content)
                self.image = image
        except:
            self.image = False
            title = _(f"Warning for : {self.template_id.name}")
            warning = {
                'title': title,
                'message': "There seems to problem while fetching Image from URL",
            }
            return {'warning': warning}
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        res_ids = super(SetuGenericProductImage, self).create(vals_list)
        for res, vals in zip(res_ids, vals_list):
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/product/image/{}/{}'.format(self.env.cr.dbname,
                                                           base64.urlsafe_b64encode(str(res.id).encode("utf-8")).decode(
                                                               "utf-8"))
            res.write({'url': url})
        return res_ids

    def write(self, values):
        if 'url' not in values:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/product/image/{}/{}'.format(self.env.cr.dbname, base64.urlsafe_b64encode(
                str(self.id).encode("utf-8")).decode("utf-8"))
            values.update({'url': url})
        return super(SetuGenericProductImage, self).write(values)
