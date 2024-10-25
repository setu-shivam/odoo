from odoo import fields, models, api, _

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_stock_to_sale_ratio_report.library import xlsxwriter
from . import setu_excel_formatter
import base64
from io import BytesIO


class SetuStockToSaleReport(models.TransientModel):
    _name = 'setu.stock.to.sale.report'
    _description = """

    """

    get_report_from_beginning = fields.Boolean("Report up to a certain date?")
    ratio_file_data = fields.Binary('Stock To Sale Ratio File')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    upto_date = fields.Date("Stock up to a certain date")
    company_ids = fields.Many2many("res.company", string="Company")#, required="True")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", 'stock_to_sale_report_product_rel',
                                   'stock_to_sale_report_id', 'product_id', string="Products")
    products_ids = fields.Many2many("product.product", 'stock_to_sale_report_product_rel',
                                    'stock_to_sale_ratio_report_id',
                                    'products_id',
                                    string="Products",
                                    compute="_compute_products_ids")
    low = fields.Float('Low Ratio')
    good = fields.Float('Good Ratio')
    high = fields.Float('High Ratio')

    def get_report_date_range(self):
        if self.get_report_from_beginning:
            start_date = '1900-01-01'
            end_date = self.upto_date.strftime("%Y-%m-%d")
            return start_date, end_date
        else:
            start_date = self.start_date and self.start_date.strftime("%Y-%m-%d") or '1900-01-01'
            end_date = self.end_date and self.end_date.strftime("%Y-%m-%d")
            return start_date, end_date

    @api.depends('product_category_ids')
    def _compute_products_ids(self):
        for record in self:
            if record.product_category_ids:
                products = self.env['product.product'].search(
                    [('categ_id', 'child_of', record.product_category_ids.ids)])
                record.products_ids = products if products else False
            else:
                products = self.env['product.product'].search([])
                record.products_ids = products if products else False

    def get_product_stock_to_sale_ratio_data(self):
        start_date, end_date = self.get_report_date_range()

        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            # company_ids = set(self.env.context.get('allowed_company_ids', False) or self.env.user.company_ids.ids) or {}
            # if no company selected active company data
            company_ids = set(self.env.user.company_ids.ids) or {}
            #  if no company selected all company data
        query = """
            Select * from get_product_stock_to_sale_ratio('%s','%s','%s','%s','%s')
        """ % (company_ids, products, category_ids, start_date, end_date)
        # print(query)
        self._cr.execute(query)
        ratio_data = self._cr.dictfetchall()
        for di in ratio_data:
            list = ['opening', 'closing', 'avg_cost', 'avg_stock_value','sales','sales_return', 'net_sales']
            for col in list:
                if not di.get(col):
                    di.update({col: 0})
            net_sales = di.get('net_sales')
            avg_stock_value = di.get('avg_stock_value')
            if not net_sales:
                ratio = 0
            else:
                ratio = avg_stock_value / net_sales
            if ratio <= float(self.env['ir.config_parameter'].get_param('setu.stock.to.sale.report.lost_sales')):
                ratio_status = 'Lost Sales'
            elif ratio >= float(self.env['ir.config_parameter'].get_param('setu.stock.to.sale.report.capital_lock')):
                ratio_status = 'Capital Lock'
            else:
                ratio_status = 'Good Performance'
            di.update({'ratio': "{:.3f}".format(ratio),
                       'ratio_status': ratio_status})
        return ratio_data

    def download_report(self):
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        ratio_data = self.get_product_stock_to_sale_ratio_data()
        # print(ratio_data)
        company_wise_data = self.prepare_data_to_write(ratio_data=ratio_data)
        if not company_wise_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)

        for ratio_data_key, ratio_data_value in company_wise_data.items():
            sheet_name = ratio_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 4
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for data_key, data_value in ratio_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, data_value, row=row_no)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'ratio_file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Stock To Sale Ratio Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/setu_air_download_document?model=setu.stock.to.sale.report&field=ratio_file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'new',
        }

    def download_report_in_listview(self):
        ratio_data = self.get_product_stock_to_sale_ratio_data()
        # print(ratio_data)
        for data_value in ratio_data:
            data_value['wizard_id'] = self.id
            self.create_data(data_value)
        graph_view_id = self.env.ref('setu_stock_to_sale_ratio_report.setu_stock_to_sale_bi_report_graph').id
        tree_view_id = self.env.ref('setu_stock_to_sale_ratio_report.setu_stock_to_sale_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report', False)
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
        return {
            'name': _('Stock To Sale Ratio Report'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.stock.to.sale.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
            'context': "{'search_default_company_id_groupby':1}",
        }

    def create_data(self, data):
        del data['company_name']
        del data['product_name']
        del data['product_category_name']
        del data['currency_name']
        return self.env['setu.stock.to.sale.bi.report'].create(data)

    def get_file_name(self):
        filename = "stock_to_sale_ratio_report"
        if self.get_report_from_beginning:
            filename = filename + "_upto_" + self.upto_date.strftime("%Y-%m-%d") + ".xlsx"
        else:
            filename = filename + "_from_" + self.start_date.strftime("%Y-%m-%d") + "_to_" + self.end_date.strftime(
                "%Y-%m-%d") + ".xlsx"
        return filename

    def prepare_data_to_write(self, ratio_data={}):
        company_wise_data = {}
        for data in ratio_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key, False):
                company_wise_data[key] = {data.get('product_id'): data}
            else:
                company_wise_data.get(key).update({data.get('product_id'): data})
        return company_wise_data

    def create_excel_workbook(self, file_pointer):
        # self.start_date.strftime("%Y-%m-%d")
        # file_name = self.get_file_name()
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    def create_excel_worksheet(self, workbook, sheet_name):
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(20)
        # worksheet.set_border()
        return worksheet

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 12, "Stock To Sale Ratio Report", wb_format)
        start_date, end_date = self.get_report_date_range()
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        report_string = ""
        if start_date == '1900-01-01':
            report_string = "Stock To Sale Ratio up to"
            worksheet.merge_range(2, 0, 2, 1, report_string, wb_format_left)
            worksheet.write(2, 2, end_date, wb_format_center)
        else:
            worksheet.write(2, 0, "From Date", wb_format_left)
            worksheet.write(2, 1, start_date, wb_format_center)
            worksheet.write(3, 0, "End Date", wb_format_left)
            worksheet.write(3, 1, end_date, wb_format_center)

    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 2, 20)
        worksheet.set_column(3, 16, 12)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook, worksheet)
        self.set_column_width(workbook, worksheet)

        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        list = ['Company', 'Company Currency', 'Product', 'Category', 'Opening Stock', 'Closing Stock', 'Average Stock',
                'Sales', 'Sales Return', 'Net Sales', 'Average Cost', 'Ratio', 'Ratio status']
        c = 0
        for i in list:
            format = even_normal_right_format
            if c == 0 or c == 1 or c == 2:
                format = normal_left_format
            elif c % 2 == 0:
                format = odd_normal_right_format
            worksheet.write(row, c, i, format)
            c += 1

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        list = ['company_name','currency_name', 'product_name', 'product_category_name', 'opening', 'closing', 'avg_stock_value',
                'sales', 'sales_return', 'net_sales', 'avg_cost', 'ratio', 'ratio_status']
        c = 0
        for i in list:
            format = even_normal_right_format
            if c == 0 or c == 1 or c == 2:
                format = normal_left_format
            elif c % 2 == 0:
                format = odd_normal_right_format
            worksheet.write(row, c, data.get(i, ''), format)
            c += 1

        # return worksheet


class SetuStocktoSaleBIReport(models.TransientModel):
    _name = 'setu.stock.to.sale.bi.report'
    _description = """Stock To Sale Ratio Report"""

    company_id = fields.Many2one('res.company', "Company")
    currency_id = fields.Many2one('res.currency', "Currency")
    product_id = fields.Many2one('product.product', 'Product')
    categ_id = fields.Many2one('product.category', 'Product Category')
    opening = fields.Float('Opening Stock')
    closing = fields.Float('Closing Stock')
    avg_cost = fields.Float('Average Cost')
    avg_stock_value = fields.Float('Average Stock')
    sales = fields.Float('Sales')
    sales_return = fields.Float('Sales Return')
    net_sales = fields.Float('Net Sales')
    ratio = fields.Float('Ratio')
    ratio_status = fields.Char('Ratio Status')
    wizard_id = fields.Many2one("setu.stock.to.sale.report")
