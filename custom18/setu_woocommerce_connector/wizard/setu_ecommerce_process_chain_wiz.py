from odoo import fields, models, api, _


class SetuEcommerceProcessChainWiz(models.TransientModel):
    _inherit = 'setu.ecommerce.process.chain.wiz'

    def manual_main_chain_process(self):
        res = super(SetuEcommerceProcessChainWiz, self).manual_main_chain_process()
        get_current_chain_process = self._context.get('current_chain_process')
        if get_current_chain_process == 'manual_coupon_chain_process':
            self.sudo().manual_coupon_chain_process()
        return res

    def manual_coupon_chain_process(self):
        setu_woocommerce_coupon_chain_line_obj = self.env["setu.woocommerce.coupon.chain.line"]
        active_coupon_chain_ids = self._context.get('active_ids')
        for coupon_chain_id in active_coupon_chain_ids:
            woocommerce_coupon_chain_line_ids = setu_woocommerce_coupon_chain_line_obj.search(
                [("setu_woocommerce_coupon_chain_id", "=", coupon_chain_id), ("state", "in", ('draft', 'fail'))])
            woocommerce_coupon_chain_line_ids.process_woocommerce_coupon_chain_line()
        return True

    def cancel_main_chain_process(self):
        res = super(SetuEcommerceProcessChainWiz, self).cancel_main_chain_process()
        get_current_chain_process = self._context.get('current_chain_process')
        if get_current_chain_process == "cancel_coupon_chain_process":
            self.cancel_coupon_chain_process()
        return res

    def cancel_coupon_chain_process(self):
        setu_ecommerce_coupon_chain_obj = self.env["setu.woocommerce.coupon.chain"]
        active_coupon_chain_ids = self._context.get('active_ids')
        coupon_chain_ids = setu_ecommerce_coupon_chain_obj.browse(active_coupon_chain_ids)
        for coupon_chain_id in coupon_chain_ids:
            coupon_chain_line_ids = coupon_chain_id.setu_woocommerce_coupon_chain_line_ids.filtered(
                lambda line: line.state in ['draft', 'fail'])
            coupon_chain_line_ids.write({'state': 'cancel'})
            coupon_chain_id.message_post(body=_("Manually set to cancel chain lines %s - ") % (
                coupon_chain_line_ids.mapped('setu_woocommerce_coupon_chain_id')))
        return True
