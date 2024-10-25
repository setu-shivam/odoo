from odoo.tests import Form
from odoo import fields, models, api, _
import random
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
from freezegun import freeze_time
import logging

_logger = logging.getLogger("generating_data")


class SetuDataGenerator(models.TransientModel):
    _name = "setu.data.generator"
    _description = ""

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")
    max_order_per_day = fields.Integer("Maximum orders per day", default=10, )
    max_products_per_order = fields.Integer("Maximum products per order", default=3)
    max_qty_per_product_in_order = fields.Integer("Maximum qty per product in order", default=3)
    delivery_day_diff = fields.Integer("Delivery/Receive Day Difference from order date(0 to diff days)", default=1)
    journal_entry_ids = fields.One2many("setu.accounting.entry.data.generator", "wizard_id",
                                        string="Journal Entry Data")
    generate = fields.Selection([('po_so', 'Purchase/Sale order'),
                                 ('entries', 'Journal Entries')], string='Generate', default='po_so')

    # @api.onchange('product_category_ids')
    # def onchange_product_category_id(self):
    #     if self.product_category_ids:
    #         return {'domain': {'product_ids': [('categ_id','child_of', self.product_category_ids.ids)]}}
    #
    # @api.onchange('company_ids')
    # def onchange_company_id(self):
    #     if self.company_ids:
    #         return {'domain': {'warehouse_ids': [('company_id', 'child_of', self.company_ids.ids)] }}

    def get_filters(self):
        products = []
        warehouses = []
        if self.product_category_ids:
            domain = [('categ_id', 'child_of', self.product_category_ids.ids), ('detailed_type', '=', 'product')]
            products += self.env['product.product'].search(domain).ids
        if self.product_ids:
            products = self.product_ids.ids

        if not products:
            products = self.env['product.product'].search([('detailed_type', '=', 'product')]).ids

        if self.company_ids:
            domain = [('company_id', 'child_of', self.company_ids.ids)]
            warehouses += self.env['stock.warehouse'].search(domain).ids
        if self.warehouse_ids:
            warehouses = self.warehouse_ids.ids

        if not warehouses:
            warehouses = self.env['stock.warehouse'].search([]).ids

        return warehouses, products

    def create_sale_order(self, partners, end_date, order_creation_loop):
        whs, products = self.get_filters()
        orders = []
        order_list = []
        order_count = 1
        creation_date = end_date - relativedelta(days=order_creation_loop - 1)
        while order_count <= self.max_order_per_day:
            warehouse_id = whs[(random.randint(1, len(whs))) - 1]
            partner_id = partners[(random.randint(1, len(partners))) - 1]
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            pl = self.env['product.pricelist'].sudo().search([('company_id', '=', wh.company_id.id)])
            so_line_vals = self.prepare_sale_order_line_vals(products, wh, creation_date)
            pricelist_id = pl[(random.randint(1, len(pl))) - 1]
            if so_line_vals:
                so_vals = {'name': _('New'),
                           'date_order': creation_date,
                           'effective_date': creation_date,
                           'commitment_date': creation_date,
                           'expected_date': creation_date,
                           'company_id': wh.company_id.id,
                           'warehouse_id': warehouse_id,
                           'partner_id': partner_id,
                           'user_id': self.env.user.id,
                           'order_line': so_line_vals,
                           'state': 'draft',
                           'create_date': creation_date,
                           'pricelist_id': pricelist_id.id
                           }
                order = self.env['sale.order'].create(so_vals)
                order.write({'create_date': creation_date})
                # order._onchange_company_id()
                # order.onchange_partner_id()
                # order.onchange_partner_shipping_id()
                # order.onchange_user_id()
                orders.append(order.id)
                order_list.append(order.id)

                order.order_line.write({'scheduled_date': creation_date, })
                # order.action_update_prices()
                for line in order.order_line:
                    price_unit = line.with_company(line.company_id)._get_display_price()
                    if price_unit:
                        min_price_unit = price_unit - (price_unit * 5 / 100)
                        max_price_unit = price_unit + (price_unit * 5 / 100)
                        if price_unit <= 0 or min_price_unit <= 0:
                            min_price_unit = price_unit if price_unit > 0 else 10
                        if max_price_unit <= 0:
                            max_price_unit = price_unit if price_unit > 0 else 10
                    else:
                        min_price_unit = 10
                        max_price_unit = 20
                    price_unit = random.randint(int(min_price_unit), int(max_price_unit))
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price_unit,
                        product_currency=line.currency_id
                    )
            order_count += 1
        return orders

    def prepare_sale_order_line_vals(self, products, wh, scheduled_date):
        product_per_order = self.max_products_per_order
        qty_per_product = self.max_qty_per_product_in_order
        products = self.env['product.product'].sudo().with_context(warehouse=wh.id).browse(products)
        net_products = []
        for p in products:
            draft_so_qty = sum(self.env['sale.order.line'].sudo().search([('order_id.state', 'in', ['draft', 'sent']),
                                                                          ('product_id', '=', p.id),
                                                                          ('order_id.warehouse_id', '=', wh.id)]
                                                                         ).mapped('product_uom_qty'))
            draft_so_qty = max(draft_so_qty, 0)
            avail = p.qty_available - (p.outgoing_qty + draft_so_qty)
            if avail > qty_per_product:
                net_products.append(p.id)
        so_line_vals = []
        if products := net_products:
            prod_count = 1
            already_taken = []
            while prod_count <= product_per_order:
                product_id = products[(random.randint(1, len(products))) - 1]
                if product_id in already_taken:
                    prod_count += 1
                    continue
                already_taken.append(product_id)
                so_line_vals.append((0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': random.randint(1, qty_per_product),
                    'scheduled_date': scheduled_date,
                }))
                prod_count += 1
        return so_line_vals

    def generate_so(self):
        start_date = self.start_date
        end_date = self.end_date
        order_per_day = self.max_order_per_day
        i = days = (end_date - start_date).days + 1
        company_partners = self.env['res.company'].sudo().search([]).mapped("partner_id")
        user_partners = self.env['res.users'].sudo().search([]).mapped("partner_id")
        # print(f"Company partners => {company_partners}")
        exclude_partners = user_partners + company_partners
        partners = self.env['res.partner'].sudo().search([('id', 'not in', exclude_partners.ids)]).ids
        sale_orders = []
        while i >= 1:
            sale_orders.extend(self.create_sale_order(partners, end_date, i))
            sale_orders = list(
                set(sale_orders))  # list(set(sale_orders) + set(self.create_sale_order(partners, end_date, i)))
            i = i - 1
        if sale_orders:
            return {
                'name': _('Quotations'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'target': 'current',
                'domain': [('id', 'in', sale_orders)]
            }
        # else:
        #     raise ValidationError(_("No Quotations Are Created."))

        # for sale in sale_orders:
        #     so_context = {'default_type': 'out_invoice',
        #                   'force_company' : sale.company_id.id,
        #                   'default_company_id' : sale.company_id.id,
        #                   'force_date': False, 'history_order':True,}
        #     sale.filtered(lambda order: order.state in ('draft', 'sent')).with_context(so_context).action_confirm()
        #     self.complete_sale_flow(sale)
        # return True

    def confirm_sale_order_first_company(self):
        sale_orders = self.env['sale.order'].search([('company_id', '=', 1), ('state', 'in', ('draft', 'sent'))],
                                                    limit=200, order='id asc')
        job_queue_data_generation = self._context.get('job_queue_data_generation', False)
        if not job_queue_data_generation:
            sale_orders = sale_orders.filtered(lambda x: x.create_date.date() == datetime.now().date())
        if job_queue_data_generation:
            delivery_gap = self._context.get('sale_delivery_day_diff')
        else:
            delivery_gap = self.env['ir.config_parameter'].sudo(). \
                get_param('setu_data_generator.sale_delivery_gap')
            delivery_gap = int(delivery_gap)
        if not delivery_gap:
            delivery_gap = 0
        for sale in sale_orders:
            so_context = {'default_type': 'out_invoice',
                          'with_company': sale.company_id.id,
                          'default_company_id': sale.company_id.id,
                          'force_date': False, 'history_order': True, }
            if self._context.get('job_queue_data_generation', False) and 'sale_delivery_day_diff' in self._context:
                so_context.update({'sale_delivery_day_diff': self._context.get('sale_delivery_day_diff'),
                                   'job_queue_data_generation': self._context.get('job_queue_data_generation', False)})
            # print(sale.partner_id.name)
            sale.with_user(self.env.user).filtered(lambda order: order.state in ('draft', 'sent')).with_context(
                so_context).action_confirm()
            self.with_context(delivery_gap=delivery_gap).complete_sale_flow(sale)

    def confirm_sale_order_second_company(self):
        sale_orders = self.env['sale.order'].search([('company_id', '=', 2), ('state', 'in', ('draft', 'sent'))],
                                                    limit=200, order='id asc')
        job_queue_data_generation = self._context.get('job_queue_data_generation', False)
        if job_queue_data_generation:
            sale_orders = sale_orders.filtered(lambda x: x.create_date.date() == datetime.now().date())
        if job_queue_data_generation:
            delivery_gap = self._context.get('sale_delivery_day_diff')
        else:
            delivery_gap = self.env['ir.config_parameter'].sudo(). \
                get_param('setu_data_generator.sale_delivery_gap')
            delivery_gap = int(delivery_gap)
        if not delivery_gap:
            delivery_gap = 0
        for sale in sale_orders:
            so_context = {'default_type': 'out_invoice',
                          'with_company': sale.company_id.id,
                          'default_company_id': sale.company_id.id,
                          'history_order': True, }
            if self._context.get('job_queue_data_generation', False) and 'sale_delivery_day_diff' in self._context:
                so_context.update({'sale_delivery_day_diff': self._context.get('sale_delivery_day_diff'),
                                   'job_queue_data_generation': self._context.get('job_queue_data_generation', False)})
            # print(sale.partner_id.name)
            sale.filtered(lambda order: order.state in ('draft', 'sent')).with_context(so_context).action_confirm()
            self.with_context(delivery_gap=delivery_gap).complete_sale_flow(sale)

    def complete_sale_flow(self, sales_order):
        delivery_gap = self.env['ir.config_parameter'].sudo(). \
            get_param('setu_data_generator.sale_delivery_gap')
        delivery_gap = int(delivery_gap)
        day = random.randint(0, delivery_gap + 1)
        original_context = self._context.copy() or {}
        # imediate_obj = self.env['stock.immediate.transfer']
        for order in sales_order:
            delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
            so_context = {'with_company': order.company_id.id,
                          'default_company_id': order.company_id.id,
                          'history_order': True,
                          'history_order_date': delivery_date,

                          # 'default_type': 'out_invoice',
                          }
            # with freeze_time(delivery_date):
            for picking in order.picking_ids:
                picking.with_context(so_context).action_assign()
                picking.with_context(so_context).action_confirm()
                for mv in picking.move_ids_without_package:
                    mv.quantity = mv.product_uom_qty
                delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
                so_context.update({'history_order_date': delivery_date,
                                   'force_period_date': delivery_date})
                # with freeze_time(delivery_date):
                picking.with_context(so_context).button_validate()
                delivery_gap = self.delivery_day_diff
                if self._context.get('delivery_gap', False):
                    delivery_gap = self._context.get('delivery_gap')
                day = random.randint(0, delivery_gap + 1)
                # delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
                picking.write({'date_done': delivery_date})
                moves = picking.move_ids_without_package
                for p in moves:
                    if p.date_deadline:
                        p.write({'date': delivery_date})
                        for l in p.move_line_ids:
                            l.write({'date': delivery_date})
            self.with_context(original_context).create_post_invoices(sales=order)
            # order.picking_ids.write({'date_done' : order.date_order})
            # order.with_context(so_context)._create_invoices()
            # for invoice in order.invoice_ids:
            #     order.invoice_ids.write({'invoice_date' : str(order.date_order)})
            #     invoice.action_post()

        return True

    def create_purchase_order(self, partners, end_date, order_creation_loop):
        whs, products = self.get_filters()
        orders = []
        order_list = []
        order_count = 1
        creation_date = end_date - relativedelta(days=order_creation_loop - 1)
        while order_count <= self.max_order_per_day:
            warehouse_id = whs[(random.randint(1, len(whs)) - 1)]
            partner_id = partners[(random.randint(1, len(partners)) - 1)]
            partner = self.env['res.partner'].browse(partner_id)
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            fpos = self.env['account.fiscal.position'].with_context(with_company=wh.company_id.id)._get_fiscal_position(
                partner)
            pl = self.env['product.pricelist'].sudo().search([('company_id', '=', wh.company_id.id)])
            price_list_id = pl[(random.randint(1, len(pl))) - 1]
            if po_line_vals := self._prepare_purchase_order_line_vals(wh, fpos, products, creation_date, partner,
                                                                      wh.company_id, price_list_id):

                so_vals = {'name': _('New'),
                           'company_id': wh.company_id.id,
                           'user_id': self.env.user.id,
                           'state': 'draft',
                           'partner_id': partner_id,
                           'picking_type_id': wh.in_type_id.id,
                           # 'l10n_in_journal_id': wh.l10n_in_purchase_journal_id.id,
                           'default_location_dest_id_usage': 'internal',
                           'payment_term_id': partner.with_context(
                               with_company=wh.company_id.id).property_supplier_payment_term_id.id,
                           'date_order': creation_date,
                           'date_approve': creation_date,
                           'fiscal_position_id': fpos,
                           'order_line': po_line_vals,
                           'date_planned': creation_date,
                           'create_date': creation_date,
                           'currency_id': price_list_id.currency_id.id
                           }
                order = self.env['purchase.order'].create(so_vals)
                order.write({'date_approve': order.date_planned, 'effective_date': order.date_planned,
                             'create_date': creation_date})
                order._compute_currency_rate()
                # for line in order.order_line:
                #     line.onchange_product_id()
                #     line.product_uom_qty = line.product_qty = random.randint(1, self.max_qty_per_product_in_order + 1)
                    # product = line.product_id
                    # _logger.info("======Going to purchase=%s====Available Product=%s===Order Qty=%s======" % (
                    #     product.name, product.qty_available, line.product_uom_qty))
                    # a=0
                orders.append(order.id)
                order_list.append(order.id)
            # self._cr.execute("update purchase_order set create_date='%s'::date where id=%d"%(creation_date.strftime('%Y-%m-%d'), order.id))
            order_count += 1
        return orders

    def _prepare_purchase_order_line_vals(self, wh, fpos, products, scheduled_date, partner, company, price_list_id):
        product_per_order = self.max_products_per_order
        qty_per_product = self.max_qty_per_product_in_order
        po_line_vals = []
        purchase_if_minimum_stock = self.env['ir.config_parameter'].sudo(). \
            get_param('setu_data_generator.purchase_if_minimum_stock')
        products = self.env['product.product'].sudo().browse(products)
        draft_po_line = self.env['purchase.order.line'].sudo().search(
            [('order_id.state', 'in', ['draft', 'sent']), ('product_id', 'in', products.ids),
             ('order_id.picking_type_id.warehouse_id', '=', wh.id)])
        if products := products.with_context(warehouse=wh.id).filtered(lambda x: ((x.qty_available + sum(
                draft_po_line.filtered(lambda y: y.product_id.id == x.id).mapped(
                        'product_uom_qty'))) - x.outgoing_qty <= int(purchase_if_minimum_stock))).ids:
            # if products:
            alread_taken = []
            prod_count = 1
            while prod_count <= product_per_order:
                product_id = products[(random.randint(1, len(products))) - 1]
                product = self.env['product.product'].browse(product_id)
                if product_id in alread_taken:
                    prod_count += 1
                    continue
                alread_taken.append(product_id)

                product_lang = product.with_prefetch().with_context(
                    lang=partner.lang,
                    partner_id=partner.id,
                )
                name = product_lang.display_name
                if product_lang.description_purchase:
                    name += '\n' + product_lang.description_purchase

                taxes = product.supplier_taxes_id
                taxes_id = fpos.map_tax(taxes, product_id, partner) if fpos else taxes
                if taxes_id:
                    taxes_id = taxes_id.filtered(lambda x: x.company_id.id == company.id)
                product_qty = random.randint(1, qty_per_product)
                seller = product.seller_ids.filtered(lambda s: s.partner_id.id == partner.id and s.currency_id.id == price_list_id.currency_id.id)
                # seller = product._select_seller(
                #     partner_id=partner,
                #     quantity=product_qty,
                #     date=scheduled_date,
                #     uom_id=product.uom_po_id)
                price_unit = 0.0
                if seller:
                    price_unit = seller.price if seller.price >= 1 else product.standard_price
                else:
                    price_unit = product.standard_price
                ## Here currency coversion may required in case order currency and seller currency is not same
                ## For now we don't need it, so I just skip it
                if price_unit:
                    min_price_unit = price_unit - (price_unit * 5 / 100)
                    max_price_unit = price_unit + (price_unit * 5 / 100)
                    if price_unit <= 0 or min_price_unit <= 0:
                        min_price_unit = price_unit if price_unit > 0 else 10
                    if max_price_unit <= 0:
                        max_price_unit = price_unit if price_unit > 0 else 10
                else:
                    min_price_unit = 10
                    max_price_unit = 20
                price_unit = random.randint(int(min_price_unit), int(max_price_unit))
                po_line_vals.append((0, 0, {
                    'name': name,
                    'product_id': product_id,
                    'product_qty': product_qty,
                    'date_planned': scheduled_date,
                    'price_unit': price_unit,
                    'product_uom': product.uom_po_id.id,
                    'taxes_id': [(6, 0, taxes_id.ids)],
                }))
                prod_count += 1
        return po_line_vals

    def generate_po(self):
        start_date = self.start_date
        end_date = self.end_date
        order_per_day = self.max_order_per_day
        i = days = (end_date - start_date).days + 1
        company_partners = self.env['res.company'].sudo().search([]).mapped("partner_id")
        user_partners = self.env['res.users'].sudo().search([]).mapped("partner_id")
        exclude_partners = user_partners + company_partners
        partners = self.env['res.partner'].sudo().search([('id', 'not in', exclude_partners.ids)]).ids

        purchase_orders = []
        while i >= 1:
            purchase_orders.extend(self.create_purchase_order(partners, end_date, i))
            purchase_orders = list(set(purchase_orders))
            i = i - 1
        if purchase_orders:
            purchase_orders = self.env['purchase.order'].sudo().browse(purchase_orders)
            for purchase in purchase_orders:
                po_context = {'with_company': purchase.company_id.id,
                              'default_company_id': purchase.company_id.id,
                              'force_date': False, 'history_order': True}
                if self._context.get('job_queue_datageneration', False) and 'sale_delivery_day_diff' in self._context:
                    po_context.update({'sale_delivery__day_diff': self._context.get('sale_delivery_day_diff'),
                                       'job_queue_data_generation': self._context.get('job_queue_data_generation',
                                                                                      False)})
                purchase.filtered(lambda order: order.state in ('draft', 'sent')).with_context(
                    po_context).button_confirm()
                self.with_context(po_context).complete_purchase_flow(purchase)
                purchase.write({'date_approve': purchase.date_planned})

        if purchase_orders:
            return {
                'name': _('Purchase Orders'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'target': 'current',
                'domain': [('id', 'in', purchase_orders.ids)]
            }
        # else:
        #     raise ValidationError(_("No Purchase Orders Are Created."))

    def complete_purchase_flow(self, purchase_order):
        # imediate_obj = self.env['stock.immediate.transfer']
        original_context = self._context.copy() or {}
        for order in purchase_order:
            day = random.randint(0, self.delivery_day_diff)
            delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
            po_context = {'with_company': order.company_id.id,
                          'default_company_id': order.company_id.id,
                          # 'default_journal_id' : order.picking_type_id.warehouse_id.l10n_in_purchase_journal_id.id,
                          'history_order' : True,
                          'default_type':'in_invoice',
                          'default_currency_id': order.currency_id.id,
                          'history_order_date': delivery_date
                          }
            with freeze_time(delivery_date):
                for picking in order.picking_ids:
                    picking.with_context(po_context).action_assign()
                    picking.with_context(po_context).action_confirm()
                    for mv in picking.move_ids_without_package:
                        mv.quantity = mv.product_uom_qty
                    picking.with_context(po_context).button_validate()

                    # delivery_date = (order.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
                    picking.write({'date_done': delivery_date})
                    moves = picking.move_ids_without_package
                    for p in moves:
                        if p.date_deadline:
                            p.write({'date': delivery_date})
                            for l in p.move_line_ids:
                                l.write({'date': delivery_date})
            self.with_context(original_context).create_post_blls(purchases=order)
            # vals = {  'company_id': order.company_id.id,
            #           'journal_id' : order.picking_type_id.warehouse_id.l10n_in_purchase_journal_id.id,
            #           'type':'in_invoice',
            #           'currency_id': order.currency_id.id,
            #           'partner_id' : order.partner_id.id,
            #           'invoice_date' : order.date_order,
            #           'date': str(order.date_order),
            #           'state' : 'draft',
            #         }
            # move = self.env['account.move'].with_context(po_context).create(vals)
            #
            # # move_form = Form(self.env['account.move'].with_context(po_context))
            # # move_form.partner_id = order.partner_id
            # # move_form.purchase_id = order
            # # move_form.journal_id = order.picking_type_id.warehouse_id.l10n_in_purchase_journal_id
            # # move_form.save()
            # for invoice in order.invoice_ids:
            #     order.invoice_ids.write({'invoice_date' : str(order.date_order),
            #                              # 'journal_id' : order.picking_type_id.warehouse_id.l10n_in_purchase_journal_id.id,
            #                              'date' : str(order.date_order)})
            #     invoice.action_post()

        return True

    def generate_inventory(self):
        return True

    def create_post_invoices(self, sales=False):
        if not sales:
            sales = self.sudo().env['sale.order'].search(
                [('state', 'in', ('sale', 'done')), ('invoice_status', '=', 'to invoice')])

        job_queue_data_generation = self._context.get('job_queue_data_generation', False)
        if job_queue_data_generation:
            invoice_post_days = self._context.get('sale_delivery_day_diff')
        else:
            invoice_post_days = self.env['ir.config_parameter'].sudo(). \
                get_param('setu_data_generator.invoice_post_days')
            invoice_post_days = int(invoice_post_days)
        if not invoice_post_days:
            invoice_post_days = 0

        for sale in sales:
            try:
                if sale.picking_ids and not sale.picking_ids.filtered(lambda p: p.state not in ('cancel', 'done')):
                    sale._create_invoices()
                    for invoice in sale.invoice_ids:
                        date_order = sale.date_order.date().strftime('%Y-%m-%d')

                        due_date = (sale.date_order + timedelta(days=invoice_post_days)).date().strftime('%Y-%m-%d')
                        invoice.write({'date': date_order, 'invoice_date': date_order, 'invoice_date_due': due_date})
                        invoice.action_post()
                        day = random.randint(1, invoice_post_days + 1)
                        payment_date = (sale.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
                        self.env['account.payment.register'].with_context(active_model='account.move',
                                                                          active_ids=invoice.ids).create(
                            {'payment_date': payment_date})._create_payments()
                        # invoice.auto_invoice_payment_date = date.today() + relativedelta(days=random.randint(0, 60))
            except Exception as e:
                pass

    def create_post_blls(self, purchases=False):
        if not purchases:
            purchases = self.sudo().env['purchase.order'].search(
                [('state', 'in', ('purchase', 'done')), ('invoice_status', '=', 'to invoice')])

        job_queue_data_generation = self._context.get('job_queue_data_generation', False)
        if job_queue_data_generation:
            bill_post_days = self._context.get('sale_delivery_day_diff')
        else:
            bill_post_days = self.env['ir.config_parameter'].sudo(). \
                get_param('setu_data_generator.bill_post_days')
            bill_post_days = int(bill_post_days)
        if not bill_post_days:
            bill_post_days = 0

        for purchase in purchases:
            try:
                date = purchase.date_order.strftime('%Y-%m-%d')
                if purchase.picking_ids and not purchase.picking_ids.filtered(
                        lambda p: p.state not in ('cancel', 'done')):
                    purchase.action_create_invoice()
                    for invoice in purchase.invoice_ids:
                        invoice.invoice_date = date
                        invoice.date = date
                        due_date = (purchase.date_order + timedelta(days=bill_post_days)).date().strftime('%Y-%m-%d')
                        invoice.invoice_date_due = due_date
                        day = random.randint(1, bill_post_days + 1)
                        payment_date = (purchase.date_order + timedelta(days=day)).date().strftime('%Y-%m-%d')
                        # invoice.invoice_date = date.today()
                        # invoice.auto_invoice_payment_date = date.today() + relativedelta(days=random.randint(3, 15))
                        invoice.action_post()
                        self.env['account.payment.register'].with_context(
                            active_model='account.move', active_ids=invoice.ids).create({
                            'payment_date': payment_date})._create_payments()

            except Exception as e:
                pass

    # def scheduler_generator_data(self):
    #     today = datetime.now().date().strftime('%Y-%m-%d')
    #     self.generator_data(today, today)

    def generator_data(self, start_date, end_date, company=[]):
        _logger.info(f"processing data for {start_date}&{end_date}")
        com_list = []
        if company:
            com_list = [('id', 'in', company)]
        company = self.env['res.company'].search(com_list)
        context = self._context.copy() or {}
        date_difference = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
        # this process is only for 7 days, 15 days and 30 days data process
        # purchase_end_date = datetime.strptime(end_date,'%Y-%m-%d').replace(day=5).strftime('%Y-%m-%d'),
        # sale_start_date = start_date
        if date_difference > 15:
            delivery_day_diff = 5
            # sale_delivery_day_diff =
            purchase_end_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=8)
            so_max_order_per_day = 5
            so_max_products_per_order = 4
            so_max_qty_per_product_in_order = 4
            # sale_start_date = purchase_end_date + timedelta(days=1)
        elif date_difference > 7:
            delivery_day_diff = 4
            purchase_end_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=2)
            so_max_order_per_day = 10
            so_max_products_per_order = 5
            so_max_qty_per_product_in_order = 8
            # sale_start_date = purchase_end_date + timedelta(days=1)
        else:
            delivery_day_diff = 3
            so_max_order_per_day = 8
            so_max_products_per_order = 5
            so_max_qty_per_product_in_order = 8
            purchase_end_date = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=1)
            # sale_start_date = purchase_end_date + timedelta(days=1)

        purchase_end_date = purchase_end_date.strftime('%Y-%m-%d')
        context.update({'job_queue_data_generation': True, 'sale_delivery_day_diff': delivery_day_diff})
        for com in company:
            warehouses = self.env['stock.warehouse'].search([('company_id', '=', com.id)])
            for warehouse in warehouses:
                vals = {
                    'company_ids': [(6, 0, com.ids)],
                    'warehouse_ids': [(6, 0, warehouse.ids)],
                    'max_order_per_day': 5,
                    'max_products_per_order': 10,
                    'max_qty_per_product_in_order': 40,
                    'delivery_day_diff': delivery_day_diff,
                    'start_date': start_date,
                    'end_date': purchase_end_date,
                }

                wiz = self.env['setu.data.generator'].create(vals)
                _logger.info(f"processing PO data for {wiz.warehouse_ids.name} {com.name}")
                wiz.with_context(context).generate_po()

                wiz.write({'max_order_per_day': so_max_order_per_day,
                           'max_products_per_order': so_max_products_per_order,
                           'max_qty_per_product_in_order': so_max_qty_per_product_in_order,
                           'start_date': start_date,
                           'end_date': end_date
                           })
                _logger.info(f"processing SO data for {wiz.warehouse_ids[0].name} {com.name}")
                wiz.with_context(context).generate_so()

                if com.id == 1:
                    wiz.with_context(context).confirm_sale_order_first_company()
                else:
                    wiz.with_context(context).confirm_sale_order_second_company()
        _logger.info(f"compeleted data for {start_date}&{end_date}")
        return True

    def generate_acc_entries(self):
        if not self.journal_entry_ids:
            raise ValidationError(_("Please Add Accounting journal Configurations."))
        move_ids = []
        for entry in self.journal_entry_ids:
            date_start = self.start_date
            while date_start < self.end_date:
                if entry.interval_type == 'months':
                    date_end = date_start + relativedelta(months=1, days=-1)
                elif entry.interval_type == 'years':
                    date_end = date_start + relativedelta(years=1, days=-1)
                else:
                    date_end = date_start + relativedelta(days=1)

                if date_end > self.end_date:
                    date_end = self.end_date

                time_between_dates = date_end - date_start
                days_between_dates = time_between_dates.days
                random_number_of_days = random.randrange(days_between_dates)
                random_date = date_start + timedelta(days=random_number_of_days)
                random_amount = random.randrange(entry.amount_from, entry.amount_to + 1)

                vals = {
                    'journal_id': entry.journal_id.id,
                    'company_id': entry.account_id.company_id.id,
                    'date': random_date,
                    'line_ids': [
                        [
                            0, 0,
                            {
                                'account_id': entry.account_id.id if entry.account_id.account_type == 'expense'
                                else entry.reconcile_account_id.id,
                                'date_maturity': False,
                                'amount_currency': random_amount if entry.account_id.account_type == 'expense'
                                else random_amount * -1,
                                'currency_id': entry.company_id.currency_id.id,
                                'debit': random_amount if entry.account_id.account_type == 'expense' else 0,
                                'credit': random_amount if entry.account_id.account_type == 'income' else 0,
                                'quantity': 1,
                                'product_uom_id': False,
                                'sequence': 10,
                                'tax_base_amount': 0,
                            }
                        ],
                        [
                            0, 0,
                            {
                                'account_id': entry.account_id.id if entry.account_id.account_type == 'income'
                                else entry.reconcile_account_id.id,
                                'date_maturity': False,
                                'amount_currency': random_amount if entry.account_id.account_type == 'income'
                                else random_amount * -1,
                                'currency_id': entry.company_id.currency_id.id,
                                'debit': random_amount if entry.account_id.account_type == 'income' else 0,
                                'credit': random_amount if entry.account_id.account_type == 'expense' else 0,
                                'quantity': 1,
                                'product_uom_id': False,
                                'sequence': 10,
                            }
                        ]
                    ],
                }
                move_id = self.env['account.move'].create(vals)
                move_id.action_post()
                move_ids.append(move_id.id)

                if entry.interval_type == 'months':
                    date_start = date_start + relativedelta(months=entry.interval)
                elif entry.interval_type == 'years':
                    date_start = date_start + relativedelta(years=entry.interval)
                else:
                    date_start = date_start + relativedelta(days=entry.interval)

        if move_ids:
            return {
                'name': _('Journal Entries'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'context': {'search_default_group_by_journal': 1},
                'res_model': 'account.move',
                'target': 'current',
                'domain': [('id', 'in', move_ids)]
            }


class SetuAccountingEntryDataGenerator(models.TransientModel):
    _name = "setu.accounting.entry.data.generator"

    def _get_acc_domain(self):
        accounts = self.env['account.account'].sudo().search([('account_type', 'in', ['expense', 'income'])])
        return [('id', 'in', accounts.ids)]

    wizard_id = fields.Many2one("setu.data.generator")
    account_id = fields.Many2one("account.account", string="Account", domain=_get_acc_domain)
    reconcile_account_ids = fields.Many2many("account.account", string="Reconcile Account",
                                             compute='_get_domain')
    reconcile_account_id = fields.Many2one("account.account", string="Reconcile Account")
    company_id = fields.Many2one('res.company', string='Company', related='account_id.company_id')
    journal_ids = fields.Many2many("account.journal", compute="_get_domain")
    journal_id = fields.Many2one("account.journal", string="Journal")
    amount_from = fields.Float("Amount From")
    amount_to = fields.Float("Amount To")
    interval = fields.Integer("Interval", default=1)
    interval_type = fields.Selection([("days", "Day"),
                                      ("months", "Month"),
                                      ("years", "Year")],
                                     default='months',
                                     string="Type")

    @api.onchange('account_id')
    def onchange_account_id(self):
        # for rec in self:
        if self.account_id:
            if journal := self.env['account.journal'].sudo().search(
                    [('type', '=', 'general'), ('code', '=', 'MISC'), ('company_id', '=', self.company_id.id)],
                    limit=1):
                self.journal_id = journal.id
            if account := self.env['account.account'].sudo().search(
                    [('name', '=', 'Bank'), ('company_id', '=', self.company_id.id)], limit=1):
                self.reconcile_account_id = account.id

    @api.depends("account_id")
    def _get_domain(self):
        for rec in self:
            if rec.account_id:
                company = rec.account_id.company_id
                journals = self.env['account.journal'].sudo().search([('company_id', '=', company.id)])
                rec.journal_ids = [(6, 0, journals.ids)]
            else:
                rec.journal_ids = [(6, 0, [])]

            if accounts := self.env['account.account'].sudo().search([('account_type', '=', 'asset_cash'),
                                                                      ('company_id', '=', rec.company_id.id)]):
                rec.reconcile_account_ids = [(6, 0, accounts.ids)]
            else:
                rec.reconcile_account_ids = [(6, 0, [])]
