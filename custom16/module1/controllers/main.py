from odoo import http
from odoo.http import request

class mypage(http.Controller):

    @http.route("/mypage",auth="public")
    def mypage(self,id=False,**kw):
        print(id)
        partner_ids=request.env['res.partner'].sudo().search([])
        return request.render("module1.page",{'partner_ids':partner_ids})
