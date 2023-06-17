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
            'product_id': {'input': 'product_id', 'label': _('Search with product_id')},
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
    
            'payment_mode': {'label': _('Payment Mode'), 'order': 'payment_mode', 'sequence': 3},
            'product_id': {'label': _('Category'), 'order': 'product_id', 'sequence': 4},
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
            'payment_mode': 'payment_mode',
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
        request.session['my_expense_history'] = expenses.ids[:100]

        groupby_mapping = self._get_groupby_expenses_mapping()
        group = groupby_mapping.get(groupby)
        if group:
            grouped_expenses = [expense.concat(*g) for k, g in groupbyelem(expenses, itemgetter(group))]
        else:
            grouped_expenses = [expenses]
        allocations = expenses.search([('employee_id', '=', request.env.user.employee_id.id)])
      
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
            # 'allocations': leave_allocations,
        })
        return request.render("portal_expenses.portal_my_expense_list", values)



    @http.route(['/create/expense'], type='http', auth="user", website=True)
    def expense_create(self, **post):
    # def expense_create(self, name, employee_id, product_id, date, payment_mode,total_amount,):
        employee = request.env.user.employee_id
        domain=[('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', request.env.user.company_id.id)]
        product_id = request.env['product.product'].sudo().search(domain)
        # payment_mode = request.env['hr.expense'].sudo().search([('payment_mode','=','own_account')])
        payment_modes = ['own_account','company_account']
        values = {
            'employee': employee,
            'product_id': product_id,
            'payment_modes': payment_modes,
            # 'date': date,
            # 'page_name': 'create_expense',
        }
        return request.render("portal_expenses.portal_apply_expense", values)


    
    @http.route(['/save/expense'], type='http', auth="user", website=True)
    def save_expense(self, **post):
        field_list = ['date', 'product_id', 'total_amount', 'payment_mode' ,'name','company']
        value = []
        product_id_domain=[('can_be_expensed', '=', True), '|', ('company_id', '=', False), ('company_id', '=', request.env.user.company_id.id)]
        product_id = request.env['product.product'].sudo().search(product_id_domain)
        employee = request.env.user.employee_id
        payment_mode = request.env['hr.expense'].payment_mode
        payment_modes = ['own_account','company_account']
        # company = request.env['res.company'].search(domain)
        # company = request.env['res.company'].search([('company_id', '=', False), ('company_id', '=', request.env.user.company_id.id)])

        for key in post:
            value.append(post[key])
            print("keeeeey",key, "vaaaaaalue", value)
        # if any([field not in post.keys() for field in field_list]) or not all(value) or not post:
        #     post.update({
        #         'employee': employee,
        #         'product_id': product_id,
        #         'payment_mode': payment_mode,
        #         'page_name': 'create_expense',
        #         'error': 'Some Required Fields are Missing.'
        #     })
        #     print("pppppppppppooooooooossssst",post)
        #     return request.render("portal_expenses.portal_apply_expense", post)


       
        vals = {
            'employee_id': request.env.user.employee_id.id,
            'product_id': post.get('product_id'),
            'date': post.get('date'),
            'payment_mode': post.get('payment_mode'),
            # 'company': company,
            'total_amount': post.get('total_amount'),
            'name': post.get('name'),
            'description': post.get('description'),

        }
        print("ooooooooooooooo",vals)
        request.env['hr.expense'].sudo().create(vals)
        return request.redirect('/my/expense')