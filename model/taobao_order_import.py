# -*- encoding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import re
import base64
import xlrd
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
keymap[u'收件人'] = 'buyer_detail'
keymap[u'属性'] = 'product_id'
keymap[u'数量'] = 'qty'
keymap[u'实际单价'] = 'price_unit'
keymap[u'子订单状态'] = 'line_state'
keymap[u'总价'] = 'total_price'

order_statemap = {
    u'等待买家付款': 'not_paid',
    u'买家已付款': 'paid',
    u'卖家已发货': 'send',
    u'已发货': 'send',
    u'交易成功': 'success',
    u'交易关闭': 'drop',
    u'待付款和待发货订单': 'not_paid_and_not_send',
    u'退款中的订单': 'refunding',
    u'定金已付': 'front_paid',
    u'异常订单': 'exceptional'
}

order_line_statemap = {
    u'等待付款': 'wait_pay',
    u'等待发货': 'wait_send',
    u'卖家已发货': 'send',
    u'交易成功': 'success',
    u'自动关闭': 'close',
    u'已取消': 'cancel'
}

class taobao_order_import(osv.osv_memory):
    _name = "taobao.order.import"
    _description = u"淘宝订单导入"

    _columns = {
        'format': fields.selection([('csv', u'CSV文件'), ('xls', u'XLS/XLSX文件')], u'文件类型', required=True),
        'data': fields.binary(u'文件', required=True)
    }

    _defaults = {
        'format': 'xls'
    }

    def read_xls(self, data):
        xls_rows = []
        workbook = xlrd.open_workbook(file_contents=base64.decodestring(data))
        sheet = workbook.sheet_by_index(0)
        title_row = sheet.row_values(0)
        nrows = sheet.nrows
        title_list = []
        name_column = 0
        for i in range(len(title_row)):
            key = title_row[i]
            if key == u'宝贝名称':
                name_column = i
            if keymap.has_key(key):
                title_list.append(keymap[key])
            else:
                title_list.append('__' + key)

        for i in range(1, nrows):
            row = sheet.row_values(i)
            row_data = {}
            for i in range(len(title_list)):
                key = title_list[i]
                extra_col = key.startswith('__')
                if not extra_col:
                    value = str(row[i]).decode("utf-8-sig")
                    if value.find('="') == 0:
                        value = value.replace('="', '').replace('"', '')
                    # 如果商品属性列的值不存在，使用宝贝名称代替属性
                    if key == 'product_id' and value.strip()=='' :
                        value = str(row[name_column]).decode("utf-8-sig")
                    row_data[key] = value
            xls_rows.append(row_data)
        return xls_rows

    def read_csv(self, data):
        csv_rows = []

        reader = csv.reader(StringIO(base64.decodestring(data)), quotechar='"', delimiter=',')
        # read the first line of the file (it contains columns titles);

        title_list = []
        name_column = 0
        for row in reader:
            for i in range(len(row)):
                key = row[i].decode("utf-8-sig")
                if key == u'宝贝名称':
                    name_column = i
                if keymap.has_key(key):
                    title_list.append(keymap[key])
                else:
                    title_list.append('__' + key)
            break

        for row in reader:
            row_data = {}
            for i in range(len(title_list)):
                key = title_list[i]
                extra_col = key.startswith('__')
                if not extra_col:
                    value = row[i].decode("utf-8-sig")
                    if value.find('="') == 0:
                        value = value.replace('="', '').replace('"', '')
                    if key == 'product_id' and value.strip()=='' :
                        value = row[name_column].decode("utf-8-sig")
                    row_data[key] = value
            csv_rows.append(row_data)
            
        return csv_rows

    def strptime(self, time):
        if not time.strip():
            return None
        format = '%Y-%m-%d %H:%M'
        if re.search(r'\d+-\d+-\d+ \d+:\d+:\d+', time):
            format = '%Y-%m-%d %H:%M:%S'
        return (datetime.strptime(time, format,) - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

    def create_order_vals(self, order):
        vals = {
            'name': order['name'],
            'order_date': self.strptime(order['order_date']),
            'pay_date': self.strptime(order['pay_date']),
            'delivery_date': self.strptime(order['delivery_date']),
            'end_date': self.strptime(order['end_date']),
            'freight': order['freight'],
            'total_price': order['total_price'],
            'order_state': order_statemap[order['order_state']],
            'buyer': order['buyer'],
            'buyer_detail': order['buyer_detail'],
            'order_line': [],
            'orgin_string': json.dumps(order, sort_keys=True)
        }

        for line in order['lines']:
            vals['order_line'].append( (0, 0, line) )

        return vals

    def create_order(self, cr, uid, order, context=None):
        order_obj = self.pool.get('taobao.order')
        vals = self.create_order_vals(order)
        vals.update({ 'orgin_string': json.dumps(vals, sort_keys=True) })
        order_obj.create(cr, uid, vals, context = context)
        return True

    def update_order(self, cr, uid, order, id, context=None):
        order_obj = self.pool.get('taobao.order')
        taobao_order = order_obj.browse(cr, uid, id, context = context)
        vals = self.create_order_vals(order)
        orgin_string = json.dumps(vals, sort_keys=True)
        if taobao_order.orgin_string == orgin_string:
            return True
        vals.update({ 'orgin_string': orgin_string })
        if taobao_order.sync_state == 'done':
            vals.update({ 'sync_state': 'update' })
        for line in taobao_order.order_line:
            # 删除旧的订单行
            vals['order_line'].append( (2, line.id) )
        order_obj.write(cr, uid, [id], vals, context = context)

    # 合并订单行
    def marge_orders(self, orders):
        result = []
        order_dic = {}

        def create_line(order):
            line = {
                'product_id': order['product_id'],
                'qty': order['qty'],
                'price_unit': order['price_unit'],
                'line_state': order_line_statemap[order['line_state']]
            }
            del order['product_id']
            del order['qty']
            del order['price_unit']
            del order['line_state']
            order['lines'] = [line]
            return order

        last_order_name = ""    
        for order in orders:
            new_order = create_line(order)
            # 给没有订单号的订单行添加订单号
            if not new_order['name'].strip():
                new_order['name'] = last_order_name

            # 如果已存在订单号，则合并订单
            if order_dic.has_key(new_order['name']):
                last_order = order_dic[new_order['name']]
                last_order['lines'] = last_order['lines'] + new_order['lines']
            else:
                result.append(new_order)
                order_dic[new_order['name']] = new_order
            last_order_name = new_order['name']
        return result

    def import_order(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('taobao.order')

        if context is None:
            context = {}
        this = self.browse(cr, uid, ids[0])
        if this.format == 'xls':
            orders = self.read_xls(this.data)
        else:
            orders = self.read_csv(this.data)
        orders = self.marge_orders(orders)

        for order in orders:
            order_ids = order_obj.search(cr, uid, [('name', '=', order['name'])], context = context)
            if not order_ids:
                self.create_order(cr, uid, order, context)
            else:
                self.update_order(cr, uid, order, order_ids[0], context)
        return True