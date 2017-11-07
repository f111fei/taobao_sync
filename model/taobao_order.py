# -*- encoding: utf-8 -*-

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import base64
import csv, json
from datetime import datetime, timedelta
from openerp.osv import fields,osv

keymap = {}
keymap[u'订单编号'] = 'name'
keymap[u'订单号'] = 'name'
keymap[u'买家会员名'] = 'buyer'
keymap[u'买家昵称'] = 'buyer'
keymap[u'拍下时间'] = 'order_date'
keymap[u'付款时间'] = 'pay_date'
keymap[u'发货时间'] = 'delivery_date'
keymap[u'交易结束时间'] = 'end_date'
keymap[u'运费'] = 'freight'
keymap[u'订单状态'] = 'order_state'
keymap[u'收件人信息'] = 'buyer_detail'

keymap[u'属性'] = 'product_id'
keymap[u'数量'] = 'qty'
keymap[u'实际单价'] = 'price_unit'
keymap[u'子订单状态'] = 'line_state'

class taobao_order(osv.osv):
    _name = 'taobao.order'
    _description = u"淘宝订单"

    _columns = {
        'name': fields.char(u'订单编号', required=True, copy=False, readonly=True, select=True),
        'buyer': fields.char(u'买家昵称', size=20, required=True),
        'order_date': fields.datetime(u'拍下时间', select=True),
        'pay_date': fields.datetime(u'付款时间', select=True),
        'delivery_date': fields.datetime(u'发货时间', select=True),
        'end_date': fields.datetime(u'交易结束时间', select=True),
        'freight': fields.float(u'运费'),
        'order_state': fields.char(u'订单状态', size=20),
        'buyer_detail': fields.char(u'收件人信息', size=100),
        'order_line': fields.one2many('taobao.order.line', 'order_id', u'淘宝订单行', readonly=True, copy=True),
        'sync_state': fields.selection([('none', u'未同步'), ('update', u'待更新'), ('done', u'已同步')], u'同步状态', required=True, readonly=True)
    }

    _defaults = {
        'sync_state': 'none',
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Order Reference must be unique!'),
    ]

class taobao_order_line(osv.osv):
    _name = 'taobao.order.line'
    _description = u'淘宝订单行'
    _columns = {
        'order_id': fields.many2one('taobao.order', u'订单', required=True, ondelete='cascade', select=True, readonly=True),
        'product_id': fields.char(u'名称'),
        'qty': fields.float(u'数量'),
        'price_unit': fields.float(u'单价', required=True),
        'line_state': fields.char(u'订单状态'),
    }

class taobao_order_import(osv.osv_memory):
    _name = "taobao.order.import"
    _description = u"淘宝订单导入"

    _columns = {
        'data': fields.binary(u'文件', required=True)
    }

    def read_csv(self, data):
        csv_rows = []

        reader = csv.reader(StringIO(base64.decodestring(data)), quotechar='"', delimiter=',')
        # read the first line of the file (it contains columns titles);

        title = []
        for row in reader:
            for i in range(len(row)):
                key = row[i].decode("utf-8")
                if keymap.has_key(key):
                    title.append(keymap[key])
                else:
                    title.append('__' + key)
            break
        linenum = 0
        for row in reader:
            row_data = {}
            for i in range(len(title)):
                key = title[i]
                extra_col = key.startswith('__')
                if not extra_col:
                    value = row[i].decode("utf-8")
                    if value.find('="') == 0:
                        value = value.replace('="', '').replace('"', '')
                    row_data[key] = value
            csv_rows.append(row_data)
            
        return csv_rows

    def create_order(self, cr, uid, order, context=None):
        order_obj = self.pool.get('taobao.order')
        line_obj = self.pool.get('taobao.order.line')
        
        def strptime(time):
            return (datetime.strptime(time, '%Y-%m-%d %H:%M:%S',) - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

        vals = {
            'name': order['name'],
            'order_date': strptime(order['order_date']),
            'pay_date': strptime(order['pay_date']),
            'delivery_date': strptime(order['delivery_date']),
            'end_date': strptime(order['end_date']),
            'freight': order['freight'],
            'order_state': order['order_state'],
            'buyer': order['buyer'],
            'buyer_detail': order['buyer_detail'],
            'order_line': [],
        }
        for line in order['lines']:
            vals['order_line'].append( (0, 0, line) )

        order_obj.create(cr, uid, vals, context = context)
        return True

    def update_order(self, cr, uid, order, context=None):
        return True

    def marge_orders(self, orders):
        result = []
        order_dic = {}

        def create_line(order):
            line = {
                'product_id': order['product_id'],
                'qty': order['qty'],
                'price_unit': order['price_unit'],
                'line_state': order['line_state']
            }
            del order['product_id']
            del order['qty']
            del order['price_unit']
            del order['line_state']
            order['lines'] = [line]
            return order
            
        for order in orders:
            new_order = create_line(order)
            if order_dic.has_key(new_order['name']):
                last_order = order_dic[new_order['name']]
                last_order['lines'] = last_order['lines'] + new_order['lines']
            else:
                result.append(new_order)
                order_dic[new_order['name']] = new_order
        return result


    def import_order(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('taobao.order')

        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0])
        orders = self.read_csv(this.data)
        orders = self.marge_orders(orders)

        for order in orders:
            order_ids = order_obj.search(cr, uid, [('name', '=', order['name'])], context = context)
            if not order_ids:
                self.create_order(cr, uid, order, context)
            else:
                self.update_order(cr, uid, order, context)


        return True