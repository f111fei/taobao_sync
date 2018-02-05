# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class sale_order_dates(osv.osv):
    """Add several date fields to Sale Orders, computed or user-entered"""
    _inherit = 'sale.order'

    def _get_send_date(self, cr, uid, ids, name, arg, context=None):
        """Compute the send date"""
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            has_send = True

            # 服务类产品销售订单
            if not order.picking_ids or len(order.picking_ids) == 0:
                # 使用确认日期做为发货日期
                if order.date_confirm:
                    send_date = datetime.strptime(order.date_confirm, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    dates_list.append(send_date)
                else:
                    has_send = False

            for pick in order.picking_ids:
                if pick.state == 'done':
                    dates_list.append(pick.date_done)
                else:
                    has_send = False
                    break
            if dates_list and has_send:
                res[order.id] = max(dates_list)
            else:
                res[order.id] = False
        return res

    def _get_invoice_paid_date(self, cr, uid, ids, name, arg, context=None):
        """Compute the invoice paid date"""
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            has_paid = True
            for invoice in order.invoice_ids:
                if invoice.state == 'paid':
                    dates_list.append(invoice.date_due)
                else:
                    has_paid = False
                    break
            if dates_list and has_paid:
                res[order.id] = max(dates_list)
            else:
                res[order.id] = False
        return res

    def _get_done_date(self, cr, uid, ids, name, arg, context=None):
        """Compute the done date"""
        res = {}
        dates_list = []
        for order in self.browse(cr, uid, ids, context=context):
            dates_list = []
            if order.state != 'done':
                res[order.id] = False
            else:
                send_date = order.send_date or self._get_send_date(cr, uid, [order.id], 'send_date', arg, context=context)[order.id]
                # 转换发货时间为发货日期
                if send_date:
                    send_date = datetime.strptime(send_date, DEFAULT_SERVER_DATETIME_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                    dates_list.append(send_date)
                paid_date = self._get_invoice_paid_date(cr, uid, [order.id], name, arg, context=context)[order.id]
                if not paid_date:
                    res[order.id] = False
                else:
                    dates_list.append(paid_date)
                    res[order.id] = max(dates_list)
        return res

    def _get_orders(self, cr, uid, ids, context=None):
        res = set()
        for pick in self.pool.get('stock.picking').browse(cr, uid, ids, context=context):
            if pick.state =='done' and pick.sale_id:
                res.add(pick.sale_id.id)
        return list(res)

    def _get_done_orders(self, cr, uid, ids, context=None):
        res = set()
        for order in self.pool.get('sale.order').browse(cr, uid, ids, context=context):
            if order.state =='done':
                res.add(order.id)
        return list(res)

    _columns = {
        'send_date': fields.function(_get_send_date, type='datetime', store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['date_confirm'], 10),
                'stock.picking': (_get_orders, ['id', 'state', 'date_done'], 10)
            },
            string=u'发货时间',
            help=u"所有货物调度完成的时间"),

        'done_date': fields.function(_get_done_date, type='date', store={
                'sale.order': (_get_done_orders, ['state'], 10)
            },
            string=u'交易完成日期',
            help=u"销售订单交易完成日期"),
    }
