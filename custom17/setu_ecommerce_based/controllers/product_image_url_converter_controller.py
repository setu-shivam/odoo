# -*- coding: utf-8 -*-

import base64
from odoo import http, registry, SUPERUSER_ID, api, _
from odoo.http import request


class ImageUrl(http.Controller):

    @http.route('/product/image/<string:db_name>/<string:encodedres>', type='http', auth='public')
    def store_image_data_to_url(self, db_name, encodedres='', **kwargs):
        try:
            if len(encodedres) and db_name:
                db_registry = registry(db_name)
                if db_name and not request.session.db:
                    request.session.db = db_name
                with db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    decode_data = base64.urlsafe_b64decode(encodedres)
                    res_id = str(decode_data, "utf-8")
                    status, headers, content = env['ir.http'].sudo().binary_content(model='setu.generic.product.image',
                                                                                    id=res_id, field='image')
                    content_base64 = base64.b64decode(content) if content else ''
                    headers.append(('Content-Length', len(content_base64)))
                    return request.make_response(content_base64, headers)
        except Exception:
            return request.not_found()
        return request.not_found()
