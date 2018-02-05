 # -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp import tools

class sale_report(osv.osv):
    _inherit = "sale.report"
    _columns = {
        'send_date': fields.datetime(u'发货时间', readonly=True),
        'done_date': fields.date(u'完成时间', readonly=True),
    }

    _depends = {
        'sale.order': [
            'send_date', 'done_date'
        ]
    }

    def _select(self):
        return  super(sale_report, self)._select() + ", s.send_date as send_date, s.done_date as done_date"

    def _group_by(self):
        return super(sale_report, self)._group_by() + ", s.send_date, s.done_date"
