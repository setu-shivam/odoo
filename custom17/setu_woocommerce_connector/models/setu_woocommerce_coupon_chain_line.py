from odoo import fields, models, api


class SetuWoocommerceCouponChainLine(models.Model):
    _name = 'setu.woocommerce.coupon.chain.line'
    _description = 'WooCommerce Coupon Chain Line'

    name = fields.Char(help="Coupon Chain Line", translate=True)
    woocommerce_coupon_id = fields.Char(string="WooCommerce Coupon ID", copy=False)
    woocommerce_coupon_code = fields.Char(string='WooCommerce Coupon Code', translate=True)
    state = fields.Selection([("draft", "Draft"), ("fail", "Fail"), ("done", "Done"), ("cancel", "Cancelled")],
                             default="draft")

    coupon_chain_line_data = fields.Text(string="Coupon Chain Line Data", translate=True)

    last_coupon_chain_line_process_date = fields.Datetime(string="Last Chain Line Process Date")

    woocommerce_coupons_id = fields.Many2one("setu.woocommerce.coupons", string="Woocommerce Coupons Coupon",
                                             copy=False)
    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector')
    setu_woocommerce_coupon_chain_id = fields.Many2one("setu.woocommerce.coupon.chain", string="CouponChain ID",
                                                       ondelete="cascade")

    def process_woocommerce_coupon_chain_line(self):

        setu_process_history_obj = self.env['setu.process.history']
        self_woocommerce_coupons_obj = self.env['setu.woocommerce.coupons']

        self.env.cr.execute(
            """update setu_woocommerce_coupon_chain set is_chain_in_process = False  
            where is_chain_in_process = True""")
        self._cr.commit()

        coupon_chain_id = self.setu_woocommerce_coupon_chain_id
        if coupon_chain_id.process_history_id:
            process_history_id = coupon_chain_id.process_history_id
        else:
            model_id = setu_process_history_obj.process_history_line_ids.get_model_id("setu.woocommerce.coupons")
            multi_ecommerce_connector_id = coupon_chain_id.multi_ecommerce_connector_id
            process_history_id = setu_process_history_obj.create_woocommerce_process_history("import",
                                                                                             multi_ecommerce_connector_id,
                                                                                             model_id)
        self_woocommerce_coupons_obj.process_coupon_via_webhook_created(self, process_history_id)
        if process_history_id and not process_history_id.process_history_line_ids:
            process_history_id.unlink()

    def auto_process_woocommerce_coupon_chain(self):
        query = """SELECT setu_woocommerce_coupon_chain_id FROM setu_woocommerce_coupon_chain_line WHERE state = 'draft'
         ORDER BY "create_date" ASC limit 1;"""
        self._cr.execute(query)
        coupon_chain_ids = self._cr.fetchone()
        coupon_chain_id = self.env["setu.woocommerce.coupon.chain"].browse(coupon_chain_ids)
        setu_woocommerce_coupon_chain_line_ids = coupon_chain_id and coupon_chain_id.setu_woocommerce_coupon_chain_line_ids.filtered(
            lambda x: x.state == "draft")
        setu_woocommerce_coupon_chain_line_ids and setu_woocommerce_coupon_chain_line_ids.process_woocommerce_coupon_chain_line()
        return True
