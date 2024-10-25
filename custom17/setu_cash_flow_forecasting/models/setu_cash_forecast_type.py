import json
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from statistics import mean


class SetuCashForecastType(models.Model):
    _name = 'setu.cash.forecast.type'
    _description = 'Cash Forecast Type'
    _inherit = ['mail.thread']
    _order = 'sequence'

    name = fields.Char('Name')
    code = fields.Char('Code')
    type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash Out'),
                             ('opening', 'Opening Forecast'), ('closing', 'Closing Forecast'),
                             ('net_forecast', 'Net Forecasting'), ('pending', 'Pending')],
                            string="Group")
    forecasting_tag = fields.Many2one('cash.forecast.tag', string='Forecasting Tag')
    cash_forecast_category_id = fields.Many2one('setu.cash.forecast.categories', string="Category name")
    is_group_for_opening = fields.Boolean("Is Group For Opening Balance",
                                          related='cash_forecast_category_id.is_group_for_opening')
    sequence = fields.Integer('Sequence')
    is_recurring = fields.Boolean('Recurring forecast', default=False,
                                  help="Enable this option to Calculate Forecast repeatedly after the months"
                                       "that you select in Forecast Execution Duration")
    forecast_start_period = fields.Many2one('cash.forecast.fiscal.period', string='Forecast Start Period',
                                            help="Forecast will be calculated from the period that is selected here")
    forecast_end_period = fields.Many2one('cash.forecast.fiscal.period', string='Forecast End Period',
                                          help="Forecast will be calculated up to the period that is selected here")
    period_interval = fields.Selection(string='Period Interval', selection=[('days', 'Daily'),
                                                                            ('weeks', 'Weekly'),
                                                                            ('months', 'Monthly')],
                                       related='forecast_start_period.fiscal_id.period_interval')
    recurring_duration_interval = fields.Integer(default='1', string='Forecast Execution Duration(In Months)',
                                                 help="Select duration in Months after which you wish to Execute next Forecast"
                                                      "Forecast will be executed after the number of Months that is selected"
                                                      " here between duration of Forecast Start Period and Forecast End Period"
                                                 )

    parent_forecast_type_id = fields.Many2one('setu.cash.forecast.type', string='Parent forecast type')
    child_forecast_ids = fields.One2many('setu.cash.forecast.type', 'parent_forecast_type_id',
                                         string='Child forecast types')

    account_ids = fields.Many2many('account.account', string="Accounts", copy=False)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Accounts", copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=False, default=lambda self: self.env.company)

    auto_calculate = fields.Boolean("Auto Calculate", default=True,
                                    help="Enable this option if Cash Forecast should be calculated based "
                                         "on Auto Calculation Formula set."
                                         "If this option is disabled then "
                                         "Cash Forecast will be calculated based on Fixed Value that you enter")
    fixed_value = fields.Float("Fixed value")
    dep_forecast_ids = fields.Many2many('setu.cash.forecast.type', 'cash_forecast_type_dependent', 'forecast_type_id',
                                        string='Dependant Forecast Type', copy=False)
    invisible_in_report = fields.Boolean('Invisible in report', default=False)

    # Forecast calculate formula
    calculate_from = fields.Selection([('past_account_entries', 'Past Accounting Entries'),
                                       ('past_period_forecasting_entries', 'Past Period Forecasting Entries'),
                                       ('pending', 'Pending Payable / Receivable'),
                                       ('dependant', 'Base on Dependant Forecast'),
                                       ('unbilled_purchase', 'Unbilled Purchase'),
                                       ('uninvoiced_sales', 'Uninvoiced Sales'),
                                       ('advance_or_down_payments', 'Advance/Down Payments')],
                                      string="Calculate from",
                                      help="-Past Accounting Entries of the Accounts that are selected in Account tab "
                                           "will be considered based on option that you select in Calculation Pattern "
                                           "-Entries of previous forecast calculated will be considered"
                                           "-All of Pending Payable to Vendors or Pending Receivable from Customers "
                                           "from the Accounts that are selected in Accounts tab will be considered"
                                           "-Entries will be considered from Forecast Type that you select in Dependant"
                                           " Forecast Type tab")

    calculation_pattern = fields.Selection([('average', 'Average Value of Last X Days'),
                                            ('average_entries', 'Average Value of Last X Entries'),
                                            ('seasonal', 'Same Period Previous Year')],
                                           string="Calculation pattern",
                                           help="-Cash Forecast will be calculated by taking the Average value of the "
                                                "entries of option selected in Calculate from functionality for "
                                                "Number of days entered"
                                                "-Cash Forecast will be calculated by taking the Average value of the "
                                                "entries of option selected in Calculate from functionality for "
                                                "Number of Entries entered"
                                                "-Entries of same forecast period of previous year will be considered"
                                                "while calculating Cash Forecast")
    multiply_by = fields.Float(string="Multiply by",
                               help="This option allows you to increment the Forecast Value by percentage "
                                    "that you enter here."
                                    "For eg: To increment forecast value by 5% enter 0.05. To double the "
                                    "forecast value enter 2")
    average_value_of_days = fields.Integer(string="Number of days", default=90)
    number_of_period_months = fields.Integer(string='Number Of Periods', default=1)

    real_value_multiply_by = fields.Float(string='Real value multiply by',
                                          help="While calculating Real Value of this type, "
                                               "if valuation of account appears negative and "
                                               "you wish to display it positive then multiply it with -1")
    extra_gain_and_loss = fields.Float("Extra Gain and Loss", help="")

    # past_period_type_id = fields.Many2one('setu.cash.forecast.type')

    # [Dipesh] create field for store kanban_dashboard_graph data
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    @api.model
    def create(self, vals):
        if not self._context.get('demo_data', False) and vals.get('type') in ['income', 'expense', 'opening'] and \
                not vals.get('account_ids') and vals.get('calculate_from') not in ['uninvoiced_sales',
                                                                                   'unbilled_purchase']:
            raise ValidationError(_("Please set proper account in cash forecast type"))
        return super(SetuCashForecastType, self).create(vals)

    def write(self, vals):
        res = super(SetuCashForecastType, self).write(vals)
        for rec in self:
            if not self._context.get('demo_data', False) and \
                    not rec.account_ids and rec.type in ['income', 'expense', 'opening'] and \
                    rec.calculate_from not in ['uninvoiced_sales', 'unbilled_purchase']:
                raise ValidationError(_("Please set proper account in cash forecast type"))
        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            name=_("%s (copy)") % (self.name or ''))
        return super(SetuCashForecastType, self).copy(default)

    @api.constrains('multiply_by', 'average_value_of_days', 'number_of_period_months', 'calculate_from',
                    'calculation_pattern')
    # [Dipesh] getting cash forecast types and generate json data for chart
    def _kanban_dashboard_graph(self):
        for data in self:
            data.kanban_dashboard_graph = json.dumps(data.get_bar_graph_datas())

    # [Dipesh] method for generate json chart data
    def get_bar_graph_datas(self):
        record = self.env['setu.cash.forecast'].search([('forecast_type', '=', self.type), ('name', '=', self.name)])
        result = []
        for data in record:
            result.append(
                {'label': data.forecast_period_id.display_name, 'value': data.forecast_value, 'type': 'future'})
        data = [{'label': '21-27 Aug', 'value': 33337.5, 'type': ''}, ]
        if not result.__len__():
            return [{'values': data, 'title': "dummy"}]
        if all(d['value'] == 0.0 for d in result):
            return [{'values': data, 'title': "zero-dummy"}]
        else:
            return [{'values': result, 'title': "graph_title"}]

    # [Dipesh] Create action for open setu.cash.forecast.type form view when click on kanban view title
    def open_action(self):
        return {
            'name': _('Refund Orders'),
            'view_mode': 'form',
            'res_model': 'setu.cash.forecast.type',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }

    @api.onchange('cash_forecast_category_id')
    def _compute_group(self):
        self.type = self.cash_forecast_category_id.type

    def _check_numeric_field(self):
        if self.multiply_by < 0:
            raise ValidationError(_("Please Enter positive values For 'Multiply by'"))

        if self.calculate_from == 'past_period_forecasting_entries' and self.number_of_period_months <= 0 \
                or self.calculate_from in ['past_account_entries', 'past_sales'] and \
                self.calculation_pattern == 'average' and self.average_value_of_days <= 0:
            raise ValidationError(_("Please Enter greater then 0 values For "
                                    "'{}'".format(
                'Number Of Periods' if self.calculate_from == 'past_period_forecasting_entries'
                else 'Number of days')))
        return True

    @api.constrains('name', 'type', 'company_id')
    def _check_forecast_type(self):
        for record in self:
            if record.type in ['opening', 'closing']:
                duplicate_records = self.search([('id', '!=', record.id),
                                                 ('type', '=', record.type),
                                                 ('company_id', '=', record.company_id.id)])
            else:
                duplicate_records = self.search([('id', '!=', record.id),
                                                 ('name', '=', record.name),
                                                 ('company_id', '=', record.company_id.id)])
            if duplicate_records:
                raise ValidationError(_('Forecast type you want to create is duplicate'))

    @api.constrains('forecast_end_period', 'forecast_start_period')
    def _validate_dates(self):
        if self.forecast_start_period and self.forecast_end_period and \
                self.forecast_start_period.start_date > self.forecast_end_period.start_date:
            raise ValidationError(_('Please select valid period range.'))

    def _check_duplicates(self, forecast_period_id):
        return self.env['setu.cash.forecast'].search([('forecast_type_id', '=', self.id),
                                                      ('forecast_period_id', '=', forecast_period_id.id),
                                                      ('company_id', '=', self.company_id.id),
                                                      ('account_ids', 'in', self.account_ids.ids)])

    def approve_forecast_type(self, forecast_period_id):
        flag = False
        if (self.type in ['closing', 'opening', 'net_forecast'] or
                self.calculate_from in ['pending', 'uninvoiced_sales', 'unbilled_purchase']):
            flag = True
        elif self.is_recurring:
            if self.forecast_start_period and self.forecast_start_period.start_date <= forecast_period_id.start_date:
                recurring_date = self.forecast_start_period.start_date
                period_list = [self.forecast_start_period.id]
                while recurring_date < forecast_period_id.start_date:
                    recurring_date = recurring_date + relativedelta(**{forecast_period_id.period_interval:
                                                                           self.recurring_duration_interval})
                    recurring_period = forecast_period_id.search([('start_date', '<=', recurring_date),
                                                                  ('end_date', '>=', recurring_date),
                                                                  (
                                                                      'company_id', '=',
                                                                      forecast_period_id.company_id.id)])

                    period_list.append(recurring_period.id)
                if forecast_period_id.id in period_list:
                    if self.forecast_end_period:
                        if self.forecast_end_period.start_date >= forecast_period_id.start_date:
                            flag = True
                    else:
                        flag = True
        elif forecast_period_id.id == self.forecast_start_period.id:
            flag = True
        return flag

    def _get_opening_balance(self, forecast_period_id):
        prev_period_id = self.env['cash.forecast.fiscal.period'].search(
            [('end_date', '=', forecast_period_id.start_date - timedelta(days=1)),
             ('company_id', '=', forecast_period_id.company_id.id)])
        if previous_cash_forecast := self.env['setu.cash.forecast'].search(
                [('forecast_type', '=', 'closing'), ('forecast_period_id', '=', prev_period_id.id)], limit=1):
            balance = previous_cash_forecast.forecast_value
        else:
            query = f"""
                select
                    sum(aml.debit)-sum(aml.credit) as balance
                from
                    {"account_move_line aml join account_move am on am.id = aml.move_id"
            if self._context.get('calculated_base_on', False) != 'demo' else 'local_account_book aml'}
                where
                    {"am.state = 'posted' and" if self._context.get('calculated_base_on', False) != 'demo' else ''}
                    aml.date < '{forecast_period_id.start_date}' 
                    and aml.account_id {'in' if len(self.account_ids.ids) > 1 else '='} 
                    {tuple(self.account_ids.ids) if len(self.account_ids.ids) > 1 else self.account_ids.id}
            """
            self._cr.execute(query)

            balance = self._cr.fetchall()[0][0]
        return balance or 0

    def _get_closing_forecast_value(self, forecast_period_id):
        current_period_forecasts = self.env['setu.cash.forecast'].search(
            [('forecast_period_id', '=', forecast_period_id.id)])

        period_opening = sum(current_period_forecasts.filtered(
            lambda frc: frc.forecast_type == 'opening').mapped('forecast_value'))
        period_income = sum(current_period_forecasts.filtered(
            lambda frc: frc.forecast_type == 'income' and frc.forecast_type != 'pending'
        ).mapped('forecast_value'))
        period_expense = sum(current_period_forecasts.filtered(
            lambda frc: frc.forecast_type == 'expense' and frc.forecast_type != 'pending'
        ).mapped('forecast_value'))

        return period_opening + period_income - period_expense

    def get_calculation_days(self, forecast_period_id):
        if self.calculation_pattern == 'average':
            start_date = date.today() - timedelta(days=self.average_value_of_days)
            end_date = date.today()
            days = self.average_value_of_days
        else:
            start_date = datetime.combine(forecast_period_id.start_date - relativedelta(years=1), datetime.min.time())
            end_date = datetime.combine(forecast_period_id.end_date - relativedelta(years=1), datetime.max.time())
            days = (end_date - start_date).days + 1
        return start_date, end_date, days

    def _get_past_account_entries_forecast_value(self, forecast_period_id):
        account_move_line_obj = self.env['account.move.line']
        period_days = (forecast_period_id.end_date - forecast_period_id.start_date
                       ).days + 1 if self.calculation_pattern != 'average_entries' else 1

        domain = [('company_id', '=', self.company_id.id),
                  ('account_id', 'in', self.account_ids.ids)]

        limit = False
        if self.calculation_pattern == 'average_entries':
            limit = days = self.average_value_of_days
        else:
            start_date, end_date, days = self.get_calculation_days(forecast_period_id)
            domain += [('date', '>=', start_date), ('date', '<=', end_date)]

        if self._context.get('calculated_base_on', False) == 'demo':
            move_line = self.env['local.account.book'].search(domain, order='date desc', limit=limit)
        else:
            move_line = account_move_line_obj.search(domain + [('move_id.state', 'not in', ['draft', 'cancel'])],
                                                     order='date desc',
                                                     limit=limit)

        credited_line = move_line.filtered(lambda line: line.account_id.internal_group in ['income'])
        credited_amount = sum(credited_line.mapped('credit')) - sum(credited_line.mapped('debit'))

        debited_line = move_line.filtered(
            lambda line: line.account_id.internal_group in ['expense', 'liability', 'asset'])
        debited_amount = sum(debited_line.mapped('debit')) - sum(debited_line.mapped('credit'))

        return ((credited_amount + debited_amount) / days) * period_days

    def _get_past_analytic_account_entries_forecast_value(self, forecast_period_id):
        analytic_line_obj = self.env['account.analytic.line']
        period_days = (forecast_period_id.end_date - forecast_period_id.start_date
                       ).days + 1 if self.calculation_pattern != 'average_entries' else 1

        domain = [('account_id', '=', self.analytic_account_id.id),
                  ('general_account_id', 'in', self.account_ids.ids),
                  ('company_id', '=', self.company_id.id)]
        limit = False
        if self.calculation_pattern == 'average_entries':
            days = limit = self.average_value_of_days
        else:
            date_from, date_to, days = self.get_calculation_days(forecast_period_id)
            domain += [('date', '>=', date_from),
                       ('date', '<=', date_to)]

        if self._context.get('calculated_base_on', False) == 'demo':
            analytic_line = self.env['local.account.book'].search([
                ('account_id', 'in', self.account_ids.ids),
                ('company_id', '=', self.company_id.id),
                ('analytic_account_id', '=', self.analytic_account_id.id)],
                order='date desc', limit=limit)
            return ((sum(analytic_line.mapped('credit')) - sum(analytic_line.mapped('debit'))) / days) * period_days
        else:
            analytic_line = analytic_line_obj.search(domain, order='date desc', limit=limit)
            return (sum(analytic_line.mapped('amount')) / days) * period_days

    def _get_net_forecast_value(self, forecast_period_id):
        current_period_forecasts = self.env['setu.cash.forecast'].search([
            ('forecast_period_id', '=', forecast_period_id.id),
            ('forecast_type', 'not in', ['opening', 'closing'])])

        period_income = sum(current_period_forecasts.filtered(
            lambda frc: frc.forecast_type == 'income' and frc.forecast_type != 'pending'
        ).mapped('forecast_value'))
        period_expense = sum(current_period_forecasts.filtered(
            lambda frc: frc.forecast_type == 'expense' and frc.forecast_type != 'pending'
        ).mapped('forecast_value'))

        return period_income - period_expense

    def _get_past_period_forecasting_entries_value(self, forecast_period_id):
        no_of_periods = self.number_of_period_months or 1
        past_periods_avg = self.env['setu.cash.forecast'].search([('forecast_period_id', '!=', forecast_period_id.id),
                                                                  ('forecast_type_id', '=', self.id),
                                                                  ('forecast_period_id.start_date', '>=',
                                                                   forecast_period_id.start_date - relativedelta(
                                                                       months=no_of_periods))])
        forecast_value = sum(past_periods_avg.mapped('forecast_value')) / no_of_periods
        return forecast_value or 0

    def _get_pending_forecast_value(self, forecast_period_id):
        prev_period_id = self.env['cash.forecast.fiscal.period'].search([
            ('end_date', '=', forecast_period_id.start_date - timedelta(days=1)),
            ('company_id', '=', forecast_period_id.company_id.id)])

        previous_forecast = self.env['setu.cash.forecast'].search([('forecast_type_id.calculate_from', '=', 'pending'),
                                                                   ('forecast_period_id', '=', prev_period_id.id)],
                                                                  limit=1)
        #
        domain = [('company_id', '=', self.company_id.id),
                  ('account_id', 'in', self.account_ids.ids)]

        if self._context.get('calculated_base_on', False) == 'demo':
            if previous_forecast:
                domain.append(('date', '>=', forecast_period_id.start_date))
            domain.append(('date', '<=', forecast_period_id.end_date))
            pending_amount = self.env['local.account.book'].search(domain)
            return sum(pending_amount.mapped('debit')) - sum(pending_amount.mapped('credit'))
        else:
            if previous_forecast:
                domain.append(('move_id.invoice_date_due', '>=', forecast_period_id.start_date))
            domain.append(('move_id.invoice_date_due', '<=', forecast_period_id.end_date))
            pending_move_line = self.env['account.move.line'].search(domain +
                                                                     [('move_id.payment_state', '!=', 'paid'),
                                                                      ('move_id.state', 'not in', ['draft', 'cancel'])])
            pending_move = pending_move_line.mapped('move_id')
            pending_invoice = pending_move.filtered(lambda x: x.move_type in ['out_invoice', 'in_invoice'])
            pending_refund = pending_move.filtered(lambda x: x.move_type in ['out_refund', 'in_refund'])
            return sum(pending_invoice.mapped('amount_residual_signed')) - sum(
                pending_refund.mapped('amount_residual_signed'))
            # return sum(pending_invoice.mapped('amount_total')) - sum(
            #     pending_refund.mapped('amount_total'))

    def _get_unbilled_purchase_value(self, forecast_period_id):
        currency_rate = self.env['res.currency.rate'].search(
            [('name', '<=', date.today()), ('company_id', '=', self.company_id.id)], limit=1,
            order='id desc').company_rate
        query = """
                select 
                    sum(l.payment_amount) - sum(l.amount) as payment_amount
                from 
                    (select
                        max(t.payment_amount) as payment_amount,
                        max(t.invoiced_amount) as amount
                    from
                        (select 
                            po.id as po_id,	
                            po.date_order,
                            po.amount_total as order_amount,
                            max(case when am.state = 'posted' then
                            case when po.currency_id != {} then
                                Round(am.amount_total /
                                    CASE COALESCE({}, 0::numeric)
                                        WHEN 0 THEN 1.0
                                        ELSE {}
                                    END, 2)
                                    else 
                                        COALESCE(am.amount_total,0) end
                            else
                                0
                            end) as invoiced_amount,
                            delay_type,
                            case when po.payment_term_id is not null then 
                                    case when delay_type = 'days_after' THEN 
                                        date_order + (ptl.nb_days * INTERVAL '1 days')
                                    when ptl.delay_type = 'days_after_end_of_month' THEN 
                                        date_order + (((DATE_PART('days', DATE_TRUNC('month', date_order) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) - EXTRACT(DAY FROM date_order))+ptl.nb_days) * INTERVAL '1 days')
                                    when ptl.delay_type = 'days_after_end_of_next_month' THEN 
                                        -- date_order + (ptl.nb_days * INTERVAL '1 days')
                                        date_order + (((DATE_PART('days', DATE_TRUNC('month', date_order) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) - EXTRACT(DAY FROM date_order))+
                                    DATE_PART('days', DATE_TRUNC('month', date_order + (INTERVAL '1 months')) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) + ptl.nb_days) * INTERVAL '1 days') end
                            else po.date_approve END as payment_date,
                                
                            case when po.payment_term_id is not null and po.currency_id != {} then 
                                    case when ptl.value = 'percent' then 
                                        round((((po.amount_total /
                                        CASE COALESCE({}, 0::numeric)
                                            WHEN 0 THEN 1.0
                                            ELSE {}
                                        END) * ptl.value_amount)/100)::numeric , 2)
                                    else
                                        Round((ptl.value_amount /
                                        CASE COALESCE({}, 0::numeric)
                                            WHEN 0 THEN 1.0
                                            ELSE {}
                                        END)::numeric ,2) end
                            else po.amount_total end as payment_amount
                        from 
                            purchase_order po
                            join purchase_order_line as pl on pl.order_id = po.id
                            left join account_payment_term pt on pt.id = po.payment_term_id
                            left join account_payment_term_line ptl on ptl.payment_id = pt.id 
                            left join account_move_line aml on aml.purchase_line_id = pl.id
                            left join account_move am on am.id = aml.move_id
                            where 
                            po.state = 'purchase' and po.company_id = {}
                            GROUP BY 1,2,3,5,6,7
                            )t
                            group by t.po_id
                        having
                            max(t.payment_date) >= '{}' and
                            max(t.payment_date) <= '{}')l
                """.format(self.company_id.currency_id.id, currency_rate, currency_rate, self.company_id.currency_id.id,
                           currency_rate, currency_rate,
                           currency_rate, currency_rate,
                           self.company_id.id, forecast_period_id.start_date, forecast_period_id.end_date)

        self._cr.execute(query)
        unbilled_purchase_data = self._cr.dictfetchall()
        data = unbilled_purchase_data[0].get('payment_amount')
        return data if data else 0

    def _get_uninvoiced_sales_value(self, forecast_period_id):
        currency_rate = self.env['res.currency.rate'].search(
            [('name', '<=', date.today()), ('company_id', '=', self.company_id.id)], limit=1,
            order='id desc').company_rate
        query = """
                   select 
                        sum(l.payment_amount) - sum(l.amount) as payment_amount
                   from (
                        select
                            max(t.payment_amount) as payment_amount,
                            max(t.invoiced_amount) as amount
                        from 
                            (select 
                                    so.id as so_id,  
                                    so.date_order,
                                    so.amount_total as order_amount,
                                    max(case when am.state = 'posted' then
                                        case when so.currency_id != {} then
                                            Round(am.amount_total /
                                                CASE COALESCE({}, 0::numeric)
                                                    WHEN 0 THEN 1.0
                                                    ELSE {}
                                                END, 2)
                                        else 
                                            COALESCE(am.amount_total,0) end
                                    else
                                        0
                                    end) as invoiced_amount,
                                    delay_type,
                                    case when so.payment_term_id is not null then 
                                        case when delay_type = 'days_after' THEN 
                                            date_order + (ptl.nb_days * INTERVAL '1 days')
                                        when ptl.delay_type = 'days_after_end_of_month' THEN 
                                            date_order + (((DATE_PART('days', DATE_TRUNC('month', date_order) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) - EXTRACT(DAY FROM date_order))+ptl.nb_days) * INTERVAL '1 days')
                                        when ptl.delay_type = 'days_after_end_of_next_month' THEN 
                                            -- date_order + (ptl.nb_days * INTERVAL '1 days')
                                            date_order + (((DATE_PART('days', DATE_TRUNC('month', date_order) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) - EXTRACT(DAY FROM date_order))+
                                        DATE_PART('days', DATE_TRUNC('month', date_order + (INTERVAL '1 months')) + '1 MONTH'::INTERVAL - '1 DAY'::INTERVAL) + ptl.nb_days) * INTERVAL '1 days') end
                                    else so.date_order end as payment_date,
                            
                                    case when so.payment_term_id is not null and so.currency_id != {} then 
                                        case when ptl.value = 'percent' then 
                                            round(((so.amount_total /
                                            CASE COALESCE({}, 0::numeric)
                                                WHEN 0 THEN 1.0
                                                ELSE {}
                                            END) * ptl.value_amount)/100,2)
                                        else
                                            Round(ptl.value_amount /
                                            CASE COALESCE({}, 0::numeric)
                                                WHEN 0 THEN 1.0
                                                ELSE {}
                                            END, 2) end
                                    else so.amount_total
                                    end as payment_amount
                                from 
                                    sale_order so
                                    join sale_order_line as sl on sl.order_id = so.id
                                    left join account_payment_term pt on pt.id = so.payment_term_id
                                    left join account_payment_term_line ptl on ptl.payment_id = pt.id 
                                    left join sale_order_line_invoice_rel as slr on slr.order_line_id = sl.id
                                    left join account_move_line aml on aml.id = slr.invoice_line_id
                                    left join account_move am on am.id = aml.move_id
                                where 
                                    so.state = 'sale' and so.company_id = {}
                                GROUP BY 1,2,3,5,6,7
                            )t
                            group by t.so_id
                        having
                            max(t.payment_date) >= '{}' and
                            max(t.payment_date) <= '{}')l
                """.format(self.company_id.currency_id.id, currency_rate, currency_rate, self.company_id.currency_id.id,
                           currency_rate, currency_rate,
                           currency_rate, currency_rate,
                           self.company_id.id, forecast_period_id.start_date, forecast_period_id.end_date)

        self._cr.execute(query)
        uninvoiced_sale_data = self._cr.dictfetchall()
        data = uninvoiced_sale_data[0].get('payment_amount')
        return data if data else 0

    def _get_down_or_advance_payment_values(self, forecast_period_id):
        move_line_ids = self.env['account.move.line'].search(
            [('date', '>=', forecast_period_id.start_date), ('date', '<=', forecast_period_id.end_date),
             ('account_id', 'in', self.account_ids.ids)])
        forecast_value = 0.0
        if self.type == 'income':
            forecast_value = sum(move_line_ids.mapped('credit')) - sum(move_line_ids.mapped('debit'))
        elif self.type == 'expense':
            forecast_value = sum(move_line_ids.mapped('debit')) - sum(move_line_ids.mapped('credit'))
        return forecast_value

    def _get_dependant_forecast_value(self, forecast_period_id):
        dep_forecast_ids = self.env['setu.cash.forecast'].search([('forecast_type_id', 'in', self.dep_forecast_ids.ids),
                                                                  ('forecast_period_id', '=', forecast_period_id.id)])
        dep_forecast_income = sum(dep_forecast_ids.filtered(lambda frc: frc.forecast_type == 'income'
                                                            ).mapped('forecast_value'))
        dep_forecast_expense = sum(dep_forecast_ids.filtered(lambda frc: frc.forecast_type == 'expense'
                                                             ).mapped('forecast_value'))

        return abs(dep_forecast_income - dep_forecast_expense)

    def _get_forecast_value(self, forecast_period_id):
        forecast_value = 0
        calculation_method = self.calculate_from

        if self.cash_forecast_category_id.is_group_for_opening:
            forecast_value = self._get_opening_balance(forecast_period_id)

        elif self.type == 'closing':
            forecast_value = self._get_closing_forecast_value(forecast_period_id)

        elif self.type == 'net_forecast':
            forecast_value = self._get_net_forecast_value(forecast_period_id)

        elif calculation_method == 'pending':
            forecast_value = self._get_pending_forecast_value(forecast_period_id)

        elif not self.auto_calculate:
            forecast_value = self.fixed_value or 0.0

        elif calculation_method == 'past_account_entries':
            if self.analytic_account_id:
                forecast_value = self._get_past_analytic_account_entries_forecast_value(forecast_period_id)
            else:
                forecast_value = self._get_past_account_entries_forecast_value(forecast_period_id)

        elif calculation_method == 'past_period_forecasting_entries':
            forecast_value = self._get_past_period_forecasting_entries_value(forecast_period_id)

        elif calculation_method == 'unbilled_purchase':
            forecast_value = self._get_unbilled_purchase_value(forecast_period_id)

        elif calculation_method == 'uninvoiced_sales':
            forecast_value = self._get_uninvoiced_sales_value(forecast_period_id)

        elif calculation_method == 'advance_or_down_payments':
            forecast_value = self._get_down_or_advance_payment_values(forecast_period_id)

        elif calculation_method == 'dependant':
            forecast_value = self._get_dependant_forecast_value(forecast_period_id)

        if self.type not in ['opening', 'net_forecast', 'closing']:
            if self.multiply_by:
                forecast_value *= self.multiply_by or 1
            if self.extra_gain_and_loss:
                forecast_value += self.extra_gain_and_loss
        return round(forecast_value)

    def document_layout_save(self):
        return self.env['onboarding.onboarding.step'].action_validate_step(
            'setu_cash_flow_forecasting.onboarding_onboarding_step_forecast_type')
