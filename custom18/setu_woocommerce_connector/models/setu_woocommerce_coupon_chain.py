from odoo import fields, models, api


class SetuWooCommerceCouponChain(models.Model):
    _name = 'setu.woocommerce.coupon.chain'
    _description = 'WooCommerce Coupon Chain'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    is_chain_in_process = fields.Boolean(string="Is Chain Processing", default=False)
    is_action_require = fields.Boolean(default=False)

    current_status = fields.Char(default="Running...", translate=True)
    name = fields.Char(readonly=True, translate=True)

    record_created_from = fields.Selection([("import_process", "Via Import Process"), ("webhook", "Via Webhook")])
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("completed", "Completed"), ("fail", "Fail")],
        compute="_get_compute_coupon_state", default="draft", store=True, tracking=True)

    no_records_processed = fields.Integer(string="No Records Processed")
    total_coupon_records = fields.Integer(string="Total Record", compute="_get_total_count_coupon_records")
    total_draft_coupon_records = fields.Integer(string="Total Draft Records", compute="_get_total_count_coupon_records")
    total_done_coupon_records = fields.Integer(string="Total Done Records", compute="_get_total_count_coupon_records")
    total_fail_coupon_records = fields.Integer(string="Total Fail Records", compute="_get_total_count_coupon_records")
    total_cancel_coupon_records = fields.Integer(string="Total Cancel Records",
                                                 compute="_get_total_count_coupon_records")

    multi_ecommerce_connector_id = fields.Many2one('setu.multi.ecommerce.connector',
                                                   string='Multi e-Commerce Connector', copy=False)
    ecommerce_connector = fields.Selection(string="e-Commerce Connector",
                                           related="multi_ecommerce_connector_id.ecommerce_connector", store=True)
    process_history_id = fields.Many2one("setu.process.history", string="Process History")
    process_history_line_ids = fields.One2many(related="process_history_id.process_history_line_ids")
    setu_woocommerce_coupon_chain_line_ids = fields.One2many("setu.woocommerce.coupon.chain.line",
                                                             "setu_woocommerce_coupon_chain_id", string="Coupon Lines")

    @api.depends('setu_woocommerce_coupon_chain_line_ids.state')
    def _get_total_count_coupon_records(self):
        for coupon_chain_id in self:
            coupon_chain_line_ids = coupon_chain_id.setu_woocommerce_coupon_chain_line_ids
            coupon_chain_id.total_coupon_records = len(coupon_chain_line_ids)
            coupon_chain_id.total_draft_coupon_records = len(
                coupon_chain_line_ids.filtered(lambda chain_id: chain_id.state == "draft"))
            coupon_chain_id.total_done_coupon_records = len(
                coupon_chain_line_ids.filtered(lambda chain_id: chain_id.state == "done"))
            coupon_chain_id.total_fail_coupon_records = len(
                coupon_chain_line_ids.filtered(lambda chain_id: chain_id.state == "fail"))
            coupon_chain_id.total_cancel_coupon_records = len(
                coupon_chain_line_ids.filtered(lambda chain_id: chain_id.state == "cancel"))

    @api.depends('setu_woocommerce_coupon_chain_line_ids.state')
    def _get_compute_coupon_state(self):
        for coupon_chain_id in self:
            if coupon_chain_id.total_coupon_records == coupon_chain_id.total_done_coupon_records + coupon_chain_id.total_cancel_coupon_records:
                coupon_chain_id.state = "completed"
            elif coupon_chain_id.total_draft_coupon_records == coupon_chain_id.total_coupon_records:
                coupon_chain_id.state = "draft"
            elif coupon_chain_id.total_coupon_records == coupon_chain_id.total_fail_coupon_records:
                coupon_chain_id.state = "fail"
            else:
                coupon_chain_id.state = "in_progress"

    @api.model
    def create(self, vals):
        seq = self.env["ir.sequence"].next_by_code("setu.woocommerce.coupon.chain") or "/"
        vals.update({"name": seq or ""})
        return super(SetuWooCommerceCouponChain, self).create(vals)

    def create_woocommerce_coupon_chain_via_webhook(self, request_json, multi_ecommerce_connector_id):
        created_coupon_chain_id = self.sudo().create_woocommerce_coupon_chain([request_json],
                                                                              multi_ecommerce_connector_id)
        created_coupon_chain_id.setu_woocommerce_coupon_chain_line_ids.process_woocommerce_coupon_chain_line()

    def create_woocommerce_coupon_chain(self, request_json, multi_ecommerce_connector_id):
        while request_json:
            coupon_datas = request_json[:200]
            if coupon_datas:
                coupon_chain_ids = self.create({"multi_ecommerce_connector_id": multi_ecommerce_connector_id.id})
                coupon_chain_ids.create_woocommerce_coupon_chain_line(coupon_datas, multi_ecommerce_connector_id)
                del request_json[:200]
        return coupon_chain_ids

    def create_woocommerce_coupon_chain_line(self, coupon_datas, multi_ecommerce_connector_id):
        vals_list = []
        for coupon_data in coupon_datas:
            vals_list.append({"setu_woocommerce_coupon_chain_id": self.id,
                              "multi_ecommerce_connector_id": multi_ecommerce_connector_id.id or False,
                              "woocommerce_coupon_id": coupon_data["id"],
                              "coupon_chain_line_data": coupon_data,
                              "woocommerce_coupon_code": coupon_data["code"]})
        if vals_list:
            return self.env["setu.woocommerce.coupon.chain.line"].create(vals_list)
        return False
