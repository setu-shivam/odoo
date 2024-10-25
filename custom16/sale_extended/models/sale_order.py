from odoo import fields, models, api
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rewards_use = fields.Boolean(string='Add Reward points')
    reward_point_use = fields.Float(string='Points', tracking=True)


    # @api.model
    # def write(self,vals):
    #     # vals.update({"price_unit": vals.get('price_unit')+vals.get('extra_price')})
    #     vals.update({'amount_untaxed':vals.get('amount_untaxed')+vals.partner_id.extra_price})
    #     # self.price_unit+=self.extra_price
    #     return super(SaleOrder,self).write(vals)

    # @api.onchange('rewards_use')
    # def _onchange_rewards_use(self):
    #     x = self.env['sale.order.line'].search([('product_id', '=', 40), ('order_id', '=', self.id)])
    #     for rec in self:
    #         if rec.rewards_use:
    #             # self.env['sale.order.line'].create({'product_id': 40, 'order_id':rec.id, 'price_unit':rec.reward_point_use})
    #                 self.env['sale.order.line'].create({'product_id': 40,'order_id':rec.id})
    #         if rec.reward_point_use == 0 and x:
    #             self.env['sale.order.line'].search([('product_id', '=', 40), ('order_id', '=', rec.id)]).unlink()
    #         # elif rec.reward_use == False :
    #         #     self.env['sale.order.line'].unlink({'product_id': 40, 'order_id': rec.id})
    #         else:
    #             rec.rewards_use=False

# deduction method
#     def action_confirm(self):
#         self.partner_id.setu_credit_limit -= self.amount_total
#         if self.partner_id.setu_credit_limit < 0:
#             raise ValidationError("Not Enought credit")
#         return super(SaleOrder, self).action_confirm()


# sum and compare
#     def action_confirm(self):
#         for rec in self:
#             search_total = self.search([('partner_id', '=', rec.partner_id.id)])
#             sum=0
#             for amt in search_total:
#                 sum+=amt.amount_total
#             if sum>rec.partner_id.setu_credit_limit:
#                 raise ValidationError("Not Enought credit")
#         return super(SaleOrder,self).action_confirm()

    # def action_confirm(self):
    #     for rec in self:
    #         search_total = self.search([('partner_id', '=', rec.partner_id.id)])
    #         sum=0
    #         for amt in search_total:
    #             sum+=amt.amount_total
    #         if sum>rec.partner_id.setu_credit_limit:
    #             raise ValidationError("Not Enought credit")
    #     return super(SaleOrder,self).action_confirm()

# ----------------------------------------------------------------------#rewards

    @api.onchange('rewards_use')
    def _onchange_rewards_use(self):
        for rec in self:
            if rec.rewards_use == False:
                rec.reward_point_use = 0

    @api.onchange('reward_point_use')
    def _onchange_rewards(self):
        for rec in self:
            if rec.reward_point_use:
                if rec.reward_point_use > rec.partner_id.reward_points:
                    raise ValidationError('Not Enough Rewards')
            else:
                rec.reward_point_use = False

    def action_confirm(self):
        search_sale_order_line = self.env['sale.order.line'].search([('name', 'ilike', 'reward%'), ('order_id', '=', self.id)])
        for rec in self:
            if rec.reward_point_use:
                if rec.reward_point_use > rec.partner_id.reward_points:
                    raise ValidationError('Not Enough Rewards')

                if search_sale_order_line:
                    search_sale_order_line.unlink()
                search_reward_name=self.env['product.template'].search([('name', 'ilike', 'reward%')]).id
                search_reward_id=self.env['product.product'].search([('product_tmpl_id', '=', search_reward_name)]).id
                self.env['sale.order.line'].create({'product_id': search_reward_id, 'order_id': rec.id, 'price_unit': -(rec.reward_point_use)})
            else:
                search_sale_order_line.unlink()

            rec.partner_id.reward_points-=rec.reward_point_use
            if rec.amount_total >= 1000:
                rec.partner_id.reward_points += rec.amount_total * 2 / 100
            else:
                rec.partner_id.reward_points += rec.amount_total * 1 / 100
        return super(SaleOrder, self).action_confirm()
    def action_cancel(self):
        for rec in self:
            cancel_warning = self._show_cancel_wizard()
            if cancel_warning:
                if rec.partner_id.reward_points != 0:
                    if rec.amount_total > 1000:
                        rec.partner_id.reward_points -= rec.amount_total * 2 / 100
                    if rec.amount_total < 1000:
                        rec.partner_id.reward_points -= rec.amount_total * 1 / 100
                rec.reward_point_use=0
        return super(SaleOrder, self).action_cancel()

# ----------------------------------------------------------------------


# def action_confirm(self):
#     res = super().action_confirm()
#     partner_id = self.partner_id
#     sale_order_id = self.browse(54)
#     filter_line = sale_order_id.order_line.filtered(lambda order_line: order_line.product_template_id.id == 23)
#     subtotal = sum(filter_line.mapped('price_subtotal'))
#     return res

