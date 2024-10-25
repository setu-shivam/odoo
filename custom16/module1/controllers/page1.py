from odoo import http
from odoo.http import request

class Page1(http.Controller):

    @http.route("/page1", type='http', auth='public', website=True, csrf=False)
    def page1(self, **kw):
        return request.render("module1.page1", {})