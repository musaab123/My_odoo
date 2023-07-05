# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models



class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    date_creation = fields.Date('Created Date', required=True, default=fields.Date.today())


    def print_custom_report(self):
        return self.env.ref("employee_extra_data.action_report_prosys_delevry_slip_pdf_custom").report_action(self)
    
    def print_sallary_report(self):
        return self.env.ref("employee_extra_data.action_report_prosys_delevry_slip_pdf_custom_tu").report_action(self)

