from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class myform(http.Controller):

    @http.route("/form",type='http', auth='public', website=True,csrf=False)
    def myform(self, **kw):
        # partners = request.env['res.partner'].sudo().search([])
        # values = {}
        # values.update({
        #     'partners': partners
        # })

        res_partner_data={'name':kw.get('name'),'email':kw.get('email'),'phone':kw.get('phone'),'is_company':False,'customer_rank':1}
        try:
            request.env['res.partner'].create(res_partner_data)
        except:
            print(kw.get('name'))
            print(kw.get('email'))
        else:
            _logger.info(">>>>>done")
            print('>>>>>done')
        res = request.render("module1.form", res_partner_data)
        return res

    # @api.model
    # def create(self,vals):


