# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
import io
import datetime
import base64
import unicodedata
from werkzeug.utils import redirect
from datetime import datetime, timedelta
from odoo.exceptions import AccessError, MissingError
from odoo import exceptions, SUPERUSER_ID
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager

from odoo.http import request, route
from odoo.tools import consteq


class RmaBackend(CustomerPortal):

    @http.route('/setu_rma/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to, company_id, date_range):
        date_from = datetime.strptime(date_from + ' 00:00:00', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(pytz.utc)
        date_to = datetime.strptime(date_to + ' 23:59:59', DEFAULT_SERVER_DATETIME_FORMAT).astimezone(pytz.utc)

        dashboard_data = []
        request.env.cr.execute(
            """
                        select count(sro.id), sro.name
                            from setu_return_order_line srl
                                join setu_return_reason sro on sro.id = srl.return_reason_id
                            where srl.create_date between '%s' and '%s'
                        group by sro.name
                    """ % (date_from, date_to)
        )
        return_reason = request.env.cr.dictfetchall()
        if return_reason:
            dashboard_data.append({
                'chart_type': 'pie',
                'chart_name': 'return_reason',
                'chart_title': 'Return Reason',
                'chart_values': [{'values': return_reason}]
            })
        request.env.cr.execute(
            """
                        select count(sro.id), sro.name
                            from setu_return_order_line srl
                                join setu_return_order_reason sro on sro.id = srl.return_order_reason_id
                            where srl.create_date between '%s' and '%s'
                        group by sro.name
                    """ % (date_from, date_to)
        )
        return_choice = request.env.cr.dictfetchall()
        if return_choice:
            dashboard_data.append({
                'chart_type': 'pie',
                'chart_name': 'return_choice',
                'chart_title': 'Customer Return Choice',
                'chart_values': [{'values': return_choice}]
            })

        if date_range == 'week':
            request.env.cr.execute(
                """
                                    select
                                        date::date as name,
                                        sum(qty_done) as count
                                    from stock_move_line sm
                                        join stock_location sl on sl.id = sm.location_dest_id
                                    where sm.create_date between %s and %s and sl.usage='customer' and state='done'  
                                    and sm.company_id in %s
                                    group by date::date order by date::date
                    
                                """, [date_from, date_to, tuple(company_id)]
            )
            shipped_qty = request.env.cr.dictfetchall()
            request.env.cr.execute(
                """
                                                      select
                                                  date::date as name,
                                                  sum(qty_done) as count
                                              from stock_move_line sm
                                                  join stock_location sl on sl.id = sm.location_id
                                              where sm.create_date between %s and %s and sl.usage='customer' and state='done'
                                              and sm.company_id in %s
                                              group by date::date order by date::date
                                                  """, [date_from, date_to, tuple(company_id)]
            )
            returned_qty = request.env.cr.dictfetchall()
        elif date_range == 'month':
            request.env.cr.execute(
                """select main_data.name,sum(main_data.count) as count from
                                                      (
                                    select
                                        extract(MONTH from date::date) as mo_num,
                                        to_char(date::date,'W') as w_num,
                                        concat(TO_CHAR(date::date,'Month'),'- ','W',to_char(date::date,'W')) as name,
                                        sum(qty_done) as count
                                    from stock_move_line sm
                                        join stock_location sl on sl.id = sm.location_dest_id
                                    where sm.create_date between %s and %s and sl.usage='customer' and state='done'  
                                    and sm.company_id in %s
                                    group by date::date order by date::date)as main_data 
                    group by main_data.name,main_data.mo_num,main_data.w_num
                    order by main_data.mo_num,main_data.w_num
                                """, [date_from, date_to, tuple(company_id)]
            )
            shipped_qty = request.env.cr.dictfetchall()
            request.env.cr.execute(
                """select main_data.name,sum(main_data.count) as count from
                                                      (
                                                      select
                                                  extract(MONTH from date::date) as mo_num,
                                        to_char(date::date,'W') as w_num,
                                        concat(TO_CHAR(date::date,'Month'),'- ','W',to_char(date::date,'W')) as name,
                                        sum(qty_done) as count
                                              from stock_move_line sm
                                                  join stock_location sl on sl.id = sm.location_id
                                              where sm.create_date between %s and %s and sl.usage='customer' and state='done'
                                              and sm.company_id in %s
                                              group by date::date order by date::date)as main_data 
                    group by main_data.name,main_data.mo_num,main_data.w_num
                    order by main_data.mo_num,main_data.w_num
                                                  """, [date_from, date_to, tuple(company_id)]
            )
            returned_qty = request.env.cr.dictfetchall()
        else:
            request.env.cr.execute(
                """select main_data.name,sum(main_data.count) as count from
                                                      (
                                    select
                                        extract(MONTH from date::date) as mo_num,  
                                        extract(YEAR from date::date) as yr_num,                
                                        concat(TO_CHAR(date::date,'Month'),'- ',(extract(YEAR from date::date))) as name,
                                        sum(qty_done) as count
                                    from stock_move_line sm
                                        join stock_location sl on sl.id = sm.location_dest_id
                                    where sm.create_date between %s and %s and sl.usage='customer' and state='done'  
                                    and sm.company_id in %s
                                    group by date::date order by date::date)as main_data 
                    group by main_data.name,main_data.yr_num,main_data.mo_num
                    order by main_data.yr_num,main_data.mo_num
                                """, [date_from, date_to, tuple(company_id)]
            )
            shipped_qty = request.env.cr.dictfetchall()
            request.env.cr.execute(
                """select main_data.name,sum(main_data.count) as count from
                                                      (select
                                                      extract(MONTH from date::date) as mo_num,
                                                      extract(YEAR from date::date) as yr_num,
                                                  concat(TO_CHAR(date::date,'Month'),'- ',(extract(YEAR from date::date))) as name,
                                                  sum(qty_done) as count
                                              from stock_move_line sm
                                                  join stock_location sl on sl.id = sm.location_id
                                              where sm.create_date between %s and %s and sl.usage='customer' and state='done'
                                              and sm.company_id in %s
                                              group by date::date order by date::date)as main_data 
                    group by main_data.name,main_data.yr_num,main_data.mo_num
                    order by main_data.yr_num,main_data.mo_num
                                                  """, [date_from, date_to, tuple(company_id)]
            )
            returned_qty = request.env.cr.dictfetchall()

        if shipped_qty or returned_qty:
            # if shipped_qty:
            #     shipped_qty_dup = shipped_qty[0].copy()
            #     shipped_qty_dup.update({'count': 0, 'name': shipped_qty_dup.get('name')})
            #     shipped_qty.append(shipped_qty_dup)
            # if returned_qty:
            #     returned_qty_dup = returned_qty[0].copy()
            #     returned_qty_dup.update({'count': 0, 'name': returned_qty_dup.get('name')})
            #     returned_qty.append(returned_qty_dup)
            # shipped_qty = self.name_maker(shipped_qty, date_range)
            # returned_qty = self.name_maker(returned_qty, date_range)
            dashboard_data.append({
                'chart_type': 'bar',
                'chart_name': 'shipped_vs_return',
                'chart_title': 'Shipped Vs Returned',
                'chart_values': [{'key': 'Shipped', 'values': shipped_qty}, {'key': 'Returned', 'values': returned_qty}]
            })
        return dashboard_data

    def _prepare_home_portal_values(self, counters):
        values = super(RmaBackend, self)._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        ReturnOrder = request.env['setu.return.order'].sudo()
        if 'order_counts' in counters:
            values['order_counts'] = ReturnOrder.sudo().search_count([
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ])
        return values

        # Return Order :
        # list of many return order visible and click on return order number for open a return order form
        # call for return order template
    @http.route(['/my/returns', '/my/returns/page/<int:page>'], type='http', website=True)
    def portal_my_return(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ReturnOrder = request.env['setu.return.order'].sudo()
        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id])
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'return': 'date desc'},
            'name': {'label': _('Reference'), 'return': 'name'},
            'stage': {'label': _('Stage'), 'return': 'state'},
        }
        # default sortby return
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['return']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        order_counts = ReturnOrder.sudo().search_count(domain)

        pager = portal_pager(
            url="/my/returns",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_counts,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        returns = ReturnOrder.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_returns_history'] = returns.ids[:100]

        values.update({
            'date': date_begin,
            'returns': returns.sudo(),
            'page_name': 'return',
            'pager': pager,
            'default_url': '/my/returns',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("setu_rma.portal_my_return", values)

    # Return Order :
    # click on any return order for open pdf type report
    # call for return order template
    @http.route(["/my/returns/<int:id>"], type='http', website=True)
    def return_order(self, id, access_token=None, **kw):
        # try:
        #     order_sudo = RmaBackend._document_check_access(self, 'setu.return.order', id, access_token=None)
        # except (AccessError, MissingError):
        #     return request.redirect('/my')
        order_sudo = request.env['setu.return.order'].sudo().search([('id','=',id)])

        values = {
            'return_order': order_sudo,
            'token': access_token,
            'report_type': "html"
        }
        return request.render('setu_rma.returns_order_portal_template', values)

    # Return Order :
    # click on any return order for open pdf type form report
    # call for return order template
    @http.route(['/my/return/form/', '/my/return/form/<int:id>'], type='http', website=True)
    def return_order_form(self, id, access_token=None, **kw):
        try:
            delivery_order = RmaBackend._document_check_access(self, 'stock.picking', id, access_token=None)
            # rma_order = request.env['setu.return.order'].sudo().search([('stock_picking_id', '=', delivery_order.id)])
        except (AccessError, MissingError):
            return request.redirect('/my')
        # delivery_order = request.env['stock.picking'].sudo().search([('id','=',id)])
        values = {
            'delivery_order': delivery_order,
            # 'rma_order': rma_order,
            'sale_id': delivery_order.sale_id,
            'token': access_token,
            'report_type': "html",
        }
        return request.render('setu_rma.returns_order_portal_form_template', values)

    # Return Order :
    # click on any return order for create a rerturn order and open pdf type form report
    # call for return order template
    @http.route(['/return/form/submit/<int:id>'], type='http', website=True)
    def return_order_form_submit(self, id=False,access_token=None,  **kw):
        delivery_order = request.env['stock.picking'].sudo().search([('id', '=', id)])
        rma_order = request.env['setu.return.order'].sudo()
        rma_line = request.env['setu.return.order.line'].sudo()
        order = rma_order.sudo().create({
            'stock_picking_id': delivery_order.id,
            'partner_id': delivery_order.partner_id.id
        })

        order.onchange_picking_id()
        order.onchange_sale_id()
        product_list = [i for i in kw if 'product-name' in i]
        product_list_ids = [int(i.split('-name-')[1]) for i in product_list]
        remove_lines = rma_line.sudo().search([('return_order_id', '=', order.id), ('product_id', 'not in', product_list_ids)])

        for product_list_id in product_list_ids:
            line = rma_line.sudo().search(
                [('return_order_id', '=', order.id), ('product_id', '=', product_list_id)])
            if kw.get('request-qty-%s' % product_list_id, False) == '' or kw.get('request-qty-%s' % product_list_id, False) == '0':
                line.unlink()
            else:
                line.sudo().write({
                    'return_order_reason_id': int(kw.get('return-action-%s' % product_list_id, False)),
                    'return_reason_id': int(kw.get('return-reason-%s' % product_list_id, False)),
                    'quantity': kw.get('request-qty-%s' % product_list_id, False),
                })
        return request.redirect('/my/returns/%s?status=true' % order.id)
