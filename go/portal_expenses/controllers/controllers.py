# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import http, _
from operator import itemgetter
from pytz import timezone, UTC
from odoo.addons.resource.models.resource import float_to_time
from collections import OrderedDict
from collections import namedtuple
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
from odoo.osv.expression import OR
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime
from odoo.tools import groupby as groupbyelem

DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')


class PortalAttendanceKnk(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if request.env.user._is_admin():
            domain = []
        else:
            domain = [('employee_id', '=', request.env.user.employee_id.id)]
        if 'expenses_count' in counters:
            expenses_count = request.env['hr.expense'].sudo().search_count(domain) \
                if request.env['hr.expense'].sudo().check_access_rights('read', raise_exception=False) else 0
            values['expenses_count'] = expenses_count

        return values

    def _get_searchbar_expenses_inputs(self):
        return {
            'all': {'input': 'all', 'label': _('Search in All')},
            'employee': {'input': 'employee', 'label': _('Search in Employee')},
            'payment_mode': {'input': 'payment_mode', 'label': _('Search with payment mode')},
            'category': {'input': 'category', 'label': _('Search with category')},


            
        }

    def _get_search_expenses_domain(self, search_in, search):
        search_domain = []
        if search_in in ('name', 'all'):
            search_domain = OR([search_domain, [('name', 'ilike', search)]])
        if search_in in ('employee', 'all'):
            search_domain = OR([search_domain, [('employee_id', 'ilike', search)]])
        if search_in in ('payment_mode', 'all'):
            search_domain = OR([search_domain, [('payment_mode', 'ilike', search)]])
        return search_domain

 

    def _get_searchbar_expenses_sortings(self):
        return {
    
            'payment_mode': {'label': _('payment mode'), 'order': 'holiday_status_id', 'sequence': 3},
            'category': {'label': _('Category'), 'order': 'cat', 'sequence': 4},
            'date': {'label': _('Date'), 'order': 'date', 'sequence': 4},

        }

    def _get_searchbar_expenses_groupby(self):
        values = {
            'none': {'input': 'none', 'label': _('None'), 'order': 1},
            'date': {'label': _('Date'), 'order': 'date', 'sequence': 4},
            
        }
        # return dict(sorted(values.items(), key=lambda item: item[1]["order"]))




    def _get_groupby_expenses_mapping(self):
        return {
            'payment_mode': 'holiday_status_id',
            'date': 'date',
        }


    def _get_order(self, order, groupby):
        groupby_mapping = self._get_groupby_expenses_mapping()
        field_name = groupby_mapping.get(groupby, '')
        if not field_name:
            return order
        return '%s, %s' % (field_name, order)
# stop hear ---------------------------------------------------------------------------------------------------------

    @http.route(['/my/expense', '/my/expense/page/<int:page>'], type='http', auth="user", website=True)
    def portal_expenses(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby=None, **kw):
        values = self._prepare_portal_layout_values()
        expenses = request.env['hr.expense'].sudo()
        _items_per_page = 20

        if request.env.user._is_admin():
            domain = []
        else:
            domain = [('employee_id', '=', request.env.user.employee_id.id)]
        searchbar_sortings = self._get_searchbar_expenses_sortings()
        searchbar_groupby = self._get_searchbar_expenses_groupby()
        searchbar_inputs = self._get_searchbar_expenses_inputs()
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': domain},
            # 'approved': {'label': _('Approved Time Off'), 'domain': [('state', '=', 'validate')]},
            # 'to_approve': {'label': _('To Approve'), 'domain': [('state', '=', 'confirm')]},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters.get(filterby, searchbar_filters.get('all'))['domain']

        if not groupby:
            groupby = 'none'

        if search and search_in:
            domain += self._get_search_expenses_domain(search_in, search)

        expenses_count = expenses.search_count(domain)

        pager = portal_pager(
            url="/my/expense",
            url_args={'search_in': search_in, 'search': search, 'groupby': groupby, 'filterby': filterby, 'sortby': sortby},
            total=expenses_count,
            page=page,
            step=_items_per_page
        )

        order = self._get_order(order, groupby)
        expenses = expenses.search(domain, order=order, limit=_items_per_page, offset=pager['offset'])
        request.session['my_leave_history'] = expenses.ids[:100]

        groupby_mapping = self._get_groupby_expenses_mapping()
        group = groupby_mapping.get(groupby)
        if group:
            grouped_expenses = [expense.concat(*g) for k, g in groupbyelem(expenses, itemgetter(group))]
        else:
            grouped_expenses = [expenses]

        values.update({
            'grouped_expenses': grouped_expenses,
            'page_name': 'expense',
            'pager': pager,
            'default_url': '/my/expense',
            'search_in': search_in,
            'search': search,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("portal_expenses.portal_my_expense_list", values)



    @http.route(['/create/expense'], type='http', auth="user", website=True)
    def apply_leave(self, **post):
        employee = request.env.user.employee_id
        domain = ['|', ('requires_allocation', '=', 'no'), '&', ('has_valid_allocation', '=', True), '&', ('virtual_remaining_leaves', '>', 0), ('max_leaves', '>', '0')]
        # leave_type = request.env['hr.leave.type'].search(domain)
        values = {
            'employee': employee,
            # 'leave_types': leave_type,
            'page_name': 'create_expense',
        }
        return request.render("portal_expenses.portal_apply_expense", values)


    
    @http.route(['/save/expense'], type='http', auth="user", website=True)
    def save_leave(self, **post):
        field_list = ['date', 'category', 'total', 'pay_type' ,'description','company']
        value = []
        domain = ['|', ('requires_allocation', '=', 'no'), '&', ('has_valid_allocation', '=', True), '&', ('virtual_remaining_leaves', '>', 0), ('max_expense', '>', '0')]
        category = request.env['product.product'].search(domain)
        date = datetime.strptime(post.get('datetime'), DF)
        pay_type = request.env['hr.expense'].search(domain)
        company = request.env['res.company'].search(domain)
        total = request.env['hr.expense'].search(domain)
        employee = request.env.user.employee_id

        for key in post:
            value.append(post[key])
        if any([field not in post.keys() for field in field_list]) or not all(value) or not post:
            post.update({
                'employee': employee,
                'category': category,
                'page_name': 'create_expense',
                'error': 'Some Required Fields are Missing.'
            })
            return request.render("portal_leave_knk.portal_apply_leave", post)
        # resource_calendar_id = employee.resource_calendar_id
        # domain_1 = [('calendar_id', '=', resource_calendar_id.id), ('display_type', '=', False)]
        # attendances = request.env['resource.calendar.attendance'].read_group(domain_1, ['ids:array_agg(id)', 'hour_from:min(hour_from)', 'hour_to:max(hour_to)', 'week_type', 'dayofweek', 'day_period'], ['week_type', 'dayofweek', 'day_period'], lazy=False)
        # attendances = sorted([DummyAttendance(group['hour_from'], group['hour_to'], group['dayofweek'], group['day_period'], group['week_type']) for group in attendances], key=lambda att: (att.dayofweek, att.day_period != 'morning'))
        # default_value = DummyAttendance(0, 0, 0, 'morning', False)
        # attendance_from = next((att for att in attendances if int(att.dayofweek) >= start_date.weekday()), attendances[0] if attendances else default_value)
        # attendance_to = next((att for att in reversed(attendances) if int(att.dayofweek) <= end_date.weekday()), attendances[-1] if attendances else default_value)
        # hour_from = float_to_time(attendance_from.hour_from)
        # hour_to = float_to_time(attendance_to.hour_to)
        # start_date = timezone(employee.tz).localize(datetime.combine(start_date, hour_from)).astimezone(UTC).replace(tzinfo=None)
        # end_date = timezone(employee.tz).localize(datetime.combine(end_date, hour_to)).astimezone(UTC).replace(tzinfo=None)
        # error = False
        # employee = request.env.user.employee_id
        # if start_date.date() > end_date.date():
        #     error = 'The start date must be anterior to the end date.'

        # domain = [
        #     ('date_from', '<', end_date),
        #     ('date_to', '>', start_date),
        #     ('employee_id', '=', employee.id),
        #     ('state', 'not in', ['cancel', 'refuse']),
        # ]
        # nholidays = request.env['hr.leave'].search(domain)
        # if nholidays:
        #     error = 'You can not set 2 time off that overlaps on the same day for the same employee.'
        # if error:
        #     post = {'employee': employee,
        #             'leave_types': leave_type,
        #             'page_name': 'create_leave',
        #             'error': error}
        #     return request.render("portal_leave_knk.portal_apply_leave", post)

        vals = {
            'employee_id': request.env.user.employee_id.id,
            'holiday_status_id': int(post.get('leave_type')),
            'category': category,
            'date': date,
            'pay_type': pay_type,
            'company': company,
            'total': total,
            'name': post.get('description'),
        }
        request.env['hr.expense'].create(vals)
        return request.redirect('/my/expense')