from odoo import fields, models, api, _
from . import setu_excel_formatter
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_inventory_coverage_report.library import xlsxwriter


class SetuInventoryCoverageReport(models.TransientModel):
    _inherit = 'setu.inventory.coverage.report'

    abc_analysis_type = fields.Selection([('all', 'All'),
                                          ('high_sales', 'High Sales (A)'),
                                          ('medium_sales', 'Medium Sales (B)'),
                                          ('low_sales', 'Low Sales (C)')], "ABC Classification", default="all")

    def download_report_in_listview(self):
        tree_view_id = False
        if self._context.get('is_abc', False):
            tree_view_id = self.env.ref(
                'setu_inventory_coverage_abc_analysis_report.setu_inventory_coverage_abc_analysis_bi_report_tree_inherit').id
            res = super(SetuInventoryCoverageReport, self.with_context(abc_tree_id=tree_view_id)).download_report_in_listview()
            res.update({"name": 'Inventory Coverage ABC Report'})
        else:
            res = super().download_report_in_listview()
        return res

    def write_report_data_header(self, workbook, worksheet, row):
        worksheet, row, column_no = super().write_report_data_header(workbook=workbook, worksheet=worksheet, row=row)
        if self._context.get("is_abc", False):
            even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
            even_normal_right_format.set_text_wrap()
            if self._context.get('is_abc', False):
                worksheet.write(row, column_no + 15, 'Classification', even_normal_right_format)
        return workbook, row, column_no

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        worksheet, row, column_no = super().write_data_to_worksheet(workbook=workbook, worksheet=worksheet, data=data, row=row)
        if self._context.get("is_abc", False):
            even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
            even_normal_right_format.set_text_wrap()
            if self._context.get('is_abc', False):
                worksheet.write(row, column_no + 15, data.get('analysis_category', ''), even_normal_right_format)
        return worksheet, row, column_no


class SetuABCXYZAnalysisBIReport(models.TransientModel):
    _inherit = 'setu.inventory.coverage.analysis.bi.report'

    analysis_category = fields.Selection([('A', 'A'),
                                          ('B', 'B'),
                                          ('C', 'C')], "ABC Classification")
