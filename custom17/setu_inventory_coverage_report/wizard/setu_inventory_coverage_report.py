# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_inventory_coverage_report.library import xlsxwriter
from . import setu_excel_formatter
import base64
from io import BytesIO


class SetuInventoryCoverageReport(models.TransientModel):
    _name = 'setu.inventory.coverage.report'
    _description = """Setu Inventory Coverage Report """

    stock_file_data = fields.Binary(string="Stock Movement File")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    company_ids = fields.Many2many(comodel_name="res.company", string="Companies")
    product_category_ids = fields.Many2many(comodel_name="product.category", string="Product Categories")
    product_ids = fields.Many2many(comodel_name="product.product", string="Products")
    category_product_ids = fields.Many2many(comodel_name="product.product", string="Categories Products",
                                            compute="_categories_wise_product")
    warehouse_ids = fields.Many2many(comodel_name="stock.warehouse", string="Warehouses")
    company_warehouse_ids = fields.Many2many(comodel_name="stock.warehouse", string="Company Warehouses",
                                             compute="_company_wise_warehouse")
    report_by = fields.Selection([('company', 'Company'), ('warehouse', 'Warehouse')], default='warehouse')
    internal_transfers_as_sales = fields.Boolean(string="Consider Internal Warehouse Transfer As Sales")
    vendor_strategy = fields.Selection([('quickest', 'Quickest'),
                                        ('cheapest', 'Cheapest')], string="Vendor Strategy")
    coverage_ratio_strategy = fields.Selection([('static_days', 'Static Coverage Days'),
                                                ('lead_time', 'Vendor Lead Days')], string="Coverage Ratio Strategy")
    coverage_days = fields.Integer(string="Coverage (In Days)")

    @api.constrains('coverage_days')
    def _check_coverage_days(self):
        if self.coverage_ratio_strategy == 'static_days' and self.coverage_days <= 0:
            raise ValidationError(_("Coverage Days Should be greater than 0."))

    @api.onchange('coverage_ratio_strategy')
    def _onchange_coverage_strategy(self):
        if self.coverage_ratio_strategy != 'static_days':
            self.coverage_days = 0

    @api.depends("product_category_ids")
    def _categories_wise_product(self):
        product_product_obj = self.env['product.product']
        for rec in self:
            if rec.product_category_ids:
                rec.category_product_ids = product_product_obj.search(
                    [('categ_id', 'child_of', rec.product_category_ids.ids)])
            else:
                products = self.env['product.product'].search([])
                rec.category_product_ids = products if products else False

    @api.depends("company_ids")
    def _company_wise_warehouse(self):
        stock_warehouse_obj = self.env['stock.warehouse']
        for rec in self:
            if rec.company_ids:
                rec.company_warehouse_ids = stock_warehouse_obj.search(
                    [('company_id', 'child_of', rec.company_ids.ids)])
            else:
                warehouses = self.env['stock.warehouse'].search([])
                rec.company_warehouse_ids = warehouses if warehouses else False

    @api.onchange('report_by')
    def onchange_report_by(self):
        if self.report_by == 'company':
            self.internal_transfers_as_sales = False

    def get_file_name(self):
        if self._context.get('is_abc', False):
            filename = "inventory_coverage_abc_report.xlsx"
        else:
            filename = "inventory_coverage_report.xlsx"
        return filename

    def create_excel_workbook(self, file_pointer):
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    def create_excel_worksheet(self, workbook, sheet_name):
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(22)
        # worksheet.set_border()
        return worksheet

    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 3, 23)
        worksheet.set_column(4, 16, 15)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        if self._context.get('is_abc', False):
            worksheet.merge_range(0, 0, 1, 16, "Inventory Coverage ABC Report", wb_format)
        else:
            worksheet.merge_range(0, 0, 1, 16, "Inventory Coverage Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        worksheet.write(2, 0, "Sales Start Date", wb_format_left)
        worksheet.write(3, 0, "Sales End Date", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align': 'center', 'bold': True,
                                                      'font_color': 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def get_inventory_coverage_report_data(self, for_reporting=False):
        """
        :return:
        """
        start_date = self.start_date
        end_date = self.end_date
        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids', False) or self.env.user.company_ids.ids) or {}

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}
        include_internal_transfer = 'Y' if self.internal_transfers_as_sales else False
        if self._context.get('is_abc', False):
            query = """Select * from get_icar_inventory_coverage_abc_analysis_data('%s','%s','%s','%s','%s','%s','%s','%d','%s','%s',
                        '%s','%s','%s')""" % (
                company_ids, products, category_ids, warehouses, start_date, end_date, self.report_by, self.id,
                include_internal_transfer, self.abc_analysis_type, self.vendor_strategy, self.coverage_ratio_strategy,
                self.coverage_days)
            self._cr.execute(query)
        else:
            query = """Select * from icr_get_inventory_coverage_data('%s','%s','%s','%s','%s','%s','%s','%d','%s','%s',
            '%s','%s')""" % (
                company_ids, products, category_ids, warehouses, start_date, end_date, self.report_by, self.id,
                include_internal_transfer, self.vendor_strategy, self.coverage_ratio_strategy, self.coverage_days)
            self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        if for_reporting:
            if self._context.get('is_abc', False):
                if self.abc_analysis_type == 'all':
                    abc_str = """'A','B','C'"""
                elif self.abc_analysis_type == 'high_sales':
                    abc_str = """'A'"""
                elif self.abc_analysis_type == 'medium_sales':
                    abc_str = """'B'"""
                else:
                    abc_str = """'C'"""
                self._cr.execute(
                    f"""select * from setu_inventory_coverage_analysis_bi_report where wizard_id={self.id} and analysis_category in ({abc_str})""")
            else:
                self._cr.execute(
                    f"""select * from setu_inventory_coverage_analysis_bi_report where wizard_id={self.id}""")
            stock_data = self._cr.dictfetchall()
            return stock_data
        return stock_data

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        company_wise_data = {}
        report_by = self.report_by
        for data in stock_data:
            if report_by == 'warehouse':
                key = (data.get('warehouse_id'), data.get('warehouse_name'))
            else:
                key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key, False):
                company_wise_data[key] = {data.get('product_id'): data}
            else:
                company_wise_data.get(key).update({data.get('product_id'): data})
        return company_wise_data

    def download_report(self):
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_inventory_coverage_report_data(for_reporting=True)
        company_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not company_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in company_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 3
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for age_data_key, age_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, age_data_value, row=row_no)

        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'stock_file_data': file_data})
        file_pointer.close()

        if self._context.get('is_abc', False):
            name = 'Inventory Coverage ABC Report'
        else:
            name = 'Inventory Coverage Report'

        return {
            'name': name,
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=setu.inventory.coverage.report&field=stock_file_data&id=%s&filename=%s' % (self.id, file_name),
            'target': 'new',
        }

    def download_report_in_listview(self):
        coverage_data = self.get_inventory_coverage_report_data()
        graph_view_id = self.env.ref(
            'setu_inventory_coverage_report.setu_inventory_coverage_analysis_bi_report_graph').id
        tree_view_id = self.env.ref(
            'setu_inventory_coverage_report.setu_inventory_coverage_analysis_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report', False)
        context = self._context.copy() or {}
        context.update({'icr_report_by': self.report_by})
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((tree_view_id, 'tree'))
            viewmode = "graph,tree"
        else:
            report_display_views.append((tree_view_id, 'tree'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode = "tree,graph"
        domain = [('wizard_id', '=', self.id)]
        if self._context.get('is_abc', False):
            if self.abc_analysis_type == 'all':
                domain.append(('analysis_category', 'in', ['A','B','C']))
            elif self.abc_analysis_type == 'high_sales':
                domain.append(('analysis_category', 'in', ['A']))
            elif self.abc_analysis_type == 'medium_sales':
                domain.append(('analysis_category', 'in', ['B']))
            else:
                domain.append(('analysis_category', 'in', ['C']))
        return {
            'name': _('Inventory Coverage Report'),
            'domain': domain,
            'res_model': 'setu.inventory.coverage.analysis.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'context': context,
            'views': report_display_views,
        }

    # def create_data(self, data):
    #     del data['company_name']
    #     del data['product_name']
    #     del data['category_name']
    #     return self.env['setu.inventory.coverage.analysis.bi.report'].create(data)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook, worksheet)
        self.set_column_width(workbook, worksheet)
        worksheet.set_row(row, 28)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        worksheet.set_row(row, 30)
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        odd_normal_right_format.set_text_wrap()
        even_normal_right_format.set_text_wrap()
        normal_left_format.set_text_wrap()

        worksheet.write(row, 0, 'Company', normal_left_format)
        column_no = 1
        if self.report_by == 'warehouse':
            worksheet.write(row, column_no, 'Warehouse', normal_left_format)
            column_no += 1
        worksheet.write(row, column_no, 'Product', normal_left_format)
        worksheet.write(row, column_no + 1, 'Category', normal_left_format)
        worksheet.write(row, column_no + 2, 'Vendor', odd_normal_right_format)
        worksheet.write(row, column_no + 3, 'Current Stock', even_normal_right_format)
        worksheet.write(row, column_no + 4, 'Sold', odd_normal_right_format)
        worksheet.write(row, column_no + 5, 'Average Daily Sales', even_normal_right_format)
        worksheet.write(row, column_no + 6, 'Coverage Days', odd_normal_right_format)
        worksheet.write(row, column_no + 7, 'Out Days', even_normal_right_format)
        worksheet.write(row, column_no + 8, 'Lead Days', odd_normal_right_format)
        worksheet.write(row, column_no + 9, 'Cost', even_normal_right_format)
        worksheet.write(row, column_no + 10, 'Currency', odd_normal_right_format)
        worksheet.write(row, column_no + 11, 'MOQ', even_normal_right_format)
        worksheet.write(row, column_no + 12, 'Company Currency Price', odd_normal_right_format)
        worksheet.write(row, column_no + 13, 'Company Currency', even_normal_right_format)
        worksheet.write(row, column_no + 14, 'Coverage Ratio', odd_normal_right_format)
        return worksheet, row, column_no

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('company_name', ''), normal_left_format)
        column_no = 1
        if self.report_by == 'warehouse':
            worksheet.write(row, column_no, data.get('warehouse_name', ''), normal_left_format)
            column_no += 1
        worksheet.write(row, column_no, data.get('product_name', ''), normal_left_format)
        worksheet.write(row, column_no + 1, data.get('category_name', ''), normal_left_format)
        worksheet.write(row, column_no + 2, self.env['res.partner'].browse(data.get('partner_id', '')).name if data.get(
            'partner_id') else '',
                        odd_normal_right_format)
        worksheet.write(row, column_no + 3, data.get('current_stock', ''), even_normal_right_format)
        worksheet.write(row, column_no + 4, data.get('sold_qty'), odd_normal_right_format)
        worksheet.write(row, column_no + 5, data.get('average_daily_sales', ''), even_normal_right_format)
        worksheet.write(row, column_no + 6, data.get('coverage_days', ''), odd_normal_right_format)
        worksheet.write(row, column_no + 7, data.get('out_stock_days', ''), even_normal_right_format)
        worksheet.write(row, column_no + 8, data.get('delay') if data.get('delay') else 0, odd_normal_right_format)
        worksheet.write(row, column_no + 9, data.get('price', '') if data.get('price') else 0.0,
                        even_normal_right_format)
        currency_name = self.env['res.currency'].browse(data.get('currency_id', '')).name
        worksheet.write(row, column_no + 10, currency_name if data.get('currency_id') else '',
                        odd_normal_right_format)
        worksheet.write(row, column_no + 11, data.get('min_qty', '') if data.get('min_qty') else 0,
                        even_normal_right_format)
        worksheet.write(row, column_no + 12,
                        data.get('price_in_currency', '') if data.get('price_in_currency') else 0.0,
                        odd_normal_right_format)
        company = self.env['res.company'].browse(data.get('company_id'))
        worksheet.write(row, column_no + 13, self.env['res.currency'].browse(company.currency_id.id).name,
                        even_normal_right_format)
        worksheet.write(row, column_no + 14, round(data.get('coverage_ratio', ''), 2), odd_normal_right_format)
        return worksheet, row, column_no


class SetuABCXYZAnalysisBIReport(models.TransientModel):
    _name = 'setu.inventory.coverage.analysis.bi.report'
    _description = "It helps to manage abc-xyz analysis data in listview and graphview"

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    product_category_id = fields.Many2one(comodel_name="product.category", string="Category")
    company_id = fields.Many2one(comodel_name="res.company", string="Company")
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Warehouse")
    average_daily_sales = fields.Float(string="ADS")
    current_stock = fields.Float(string="On hand")
    coverage_days = fields.Integer(string="Coverage Days")
    company_name = fields.Char(string="Company")
    product_name = fields.Char(string="Product")
    category_name = fields.Char(string="Category")
    warehouse_name = fields.Char(string="Warehouse")
    wizard_id = fields.Many2one(comodel_name="setu.inventory.coverage.report", string="Wizard")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Template")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Vendor")
    currency_id = fields.Many2one(comodel_name="res.currency", string="Currency")
    price = fields.Float(string="Cost")
    delay = fields.Integer(string="Lead Days")
    min_qty = fields.Float(string="MOQ")
    price_in_currency = fields.Float(string="Company Currency Price")
    company_currency_id = fields.Many2one(comodel_name="res.currency", related="company_id.currency_id",
                                          string="Company Currency")
    coverage_ratio = fields.Float(string="Coverage Ratio")
    out_stock_days = fields.Integer(string="Out Days")
    sold_qty = fields.Float(string="Sold")
