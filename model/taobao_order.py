# -*- encoding: utf-8 -*-

from datetime import datetime, timedelta
from openerp.osv import fields,osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

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
        'total_price': fields.float(u'总价'),
        'order_state': fields.selection([
            ('not_paid', u'等待买家付款'), ('paid', u'买家已付款'), ('send', u'卖家已发货'),
            ('success', u'交易成功'), ('drop', u'交易关闭'), ('not_paid_and_not_send', u'待付款和待发货订单'),
            ('refunding', u'退款中的订单'), ('front_paid', u'定金已付'), ('exceptional', u'异常订单')
        ], u'订单状态', required=True),
        'buyer_detail': fields.char(u'收件人信息', size=100),
        'order_line': fields.one2many('taobao.order.line', 'order_id', u'淘宝订单行', readonly=True, copy=True),
        'sync_state': fields.selection([('none', u'未同步'), ('update', u'待更新'), ('done', u'已同步')], u'同步状态', required=True, readonly=True),
        'orgin_string': fields.char(u'源数据', readonly=True)
    }

    _defaults = {
        'sync_state': 'none',
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Order Reference must be unique!'),
    ]

    def create_sale_order_line(self, cr, uid, product_id, partner_id, pricelist_id, qty, price_unit, context=None):
        line_obj = self.pool.get('sale.order.line')
        line_vals = line_obj.product_id_change(cr, uid, [], pricelist_id, product_id, qty=qty, uom=1, partner_id=partner_id, context=context)['value']
        line_vals.update({'product_id': product_id , 'price_unit':price_unit, 'product_uom_qty': qty } )
        if line_vals.get('tax_id') != None:
            line_vals['tax_id'] = [(6, 0, line_vals['tax_id'])]
        return (0, 0, line_vals)

    def create_sale_order(self, cr, uid, order, context=None):
        order_obj = self.pool.get('sale.order')
        line_obj = self.pool.get('sale.order.line')
        product_match_obj = self.pool.get('taobao.product.match')

        #如果订单已存在，则跳过创建，直接返回订单id
        order_ids = order_obj.search(cr, uid, [('name', '=', order['name'])], context = context)
        if order_ids:
            return order_ids[0]

        order_val = self.remount_sale_order_val(cr, uid, order, context = context)

        order_id = order_obj.create(cr, uid, order_val, context = context)
        return order_id

    def assets_state(self, cr, uid, taobao_order, context=None):
        state = taobao_order.order_state

        if state == 'not_paid_and_not_send' or state == 'refunding' or state == 'front_paid' or state == 'exceptional':
           raise osv.except_osv(u'订单同步失败', u'暂不支持该状态下的订单同步，请手动同步: "%s"' % (taobao_order['name']))
        return True

    def remount_sale_order_val(self, cr, uid, order, context=None):
        order_obj = self.pool.get('sale.order')
        line_obj = self.pool.get('sale.order.line')
        product_match_obj = self.pool.get('taobao.product.match')
        
        partner_ids = self.pool.get('res.partner').search(cr, uid, [('name', '=', u'淘宝客户')], context = context)
        partner_id = partner_ids[0]

        note = '昵称: ' + order.buyer + '\n' + '地址: ' + order.buyer_detail

        order_val = order_obj.onchange_partner_id(cr, uid, [], partner_id, context=context)['value']
        order_val.update({
            'name': order.name,
            'note': note,
            'date_order':  order.pay_date or order.order_date,      #付款时间
            'create_date': order.order_date,    #拍下时间
            'partner_id': partner_id,
            'picking_policy': 'direct',
            'order_policy': 'manual',
            'order_line': [],
        })

        for line in order.order_line:
            #添加订单明细行
            product_id = product_match_obj.find_product(cr, uid, line.product_id, context = context)
            qty = line.qty
            # 如果子订单行自动关闭或者已取消，则按照数量0发货
            if order.order_state != 'drop' and (line.line_state == 'close' or line.line_state == 'cancel'):
                qty = 0
            sale_line = self.create_sale_order_line(cr, uid, product_id, partner_id, order_val['pricelist_id'], qty, line.price_unit, context=context)
            order_val['order_line'].append(sale_line)

        if order.freight > 0:
            #邮费
            product_id = self.pool.get('product.product').search(cr, uid, [('name', '=', u'邮费')], context = context)[0]
            sale_line = self.create_sale_order_line(cr, uid, product_id, partner_id, order_val['pricelist_id'], 1, order.freight, context=context)
            order_val['order_line'].append(sale_line)
        return order_val

    def update_sale_order(self, cr, uid, taobao_order, context=None):
        order_obj = self.pool.get('sale.order')
        order_ids = order_obj.search(cr, uid, [('name', '=', taobao_order['name'])], context = context)
        if not order_ids:
            raise osv.except_osv(u'订单同步失败', u'无法找到对应的销售订单: "%s"' % (taobao_order['name']))
        sale_order = order_obj.browse(cr, uid, order_ids[0], context = context)

        # 更新订单基本信息，包括订单行数据
        order_val = self.remount_sale_order_val(cr, uid, taobao_order, context = context)
        sale_order_lines = len(sale_order.order_line)
        for i, line in enumerate(order_val['order_line']):
            # 更新旧的订单行
            if i < sale_order_lines:
                sale_order_line = sale_order.order_line[i]
                order_val['order_line'][i] = (1, sale_order_line.id, line[2])

        # 如果之前的行数多余现在的行数，则删除多余的订单行
        if len(order_val['order_line']) < sale_order_lines:
            for i in range(order_val['order_line'], sale_order_lines):
                order_val['order_line'].append( (2, sale_order.order_line[i].id) )

        order_obj.write(cr, uid, order_ids, order_val, context = context)

        self.assets_state(cr, uid, taobao_order, context = context)

        def datetime2day(time):
            return (datetime.strptime(time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8)).strftime(DEFAULT_SERVER_DATE_FORMAT)

        # 取消订单
        if taobao_order.order_state == 'drop':
            order_obj.action_cancel(cr, uid, order_ids, context = context)
            return True

        # 未支付，不改变状态
        if taobao_order.order_state == 'not_paid':
            return True

        # # TODO: 已支付，未发货也不改变状态，因为买家可能在发货之前退款或者退部分货? 待确认
        # if taobao_order.order_state == 'paid':
        #     return True

        # 已支付，先确认订单
        if sale_order.state == 'draft':
            order_obj.action_button_confirm(cr, uid, order_ids, context = context)

        # 服务类产品销售订单, 确认日期改为发货日期
        if not sale_order.picking_ids or len(sale_order.picking_ids) == 0:
            day_date = datetime2day(taobao_order.delivery_date)
            order_obj.write(cr, uid, [sale_order.id], { 'date_confirm': day_date }, context = context)
        
        if taobao_order.order_state == 'paid':
            return True

        # 检查库存可用
        stock_picking_obj = self.pool.get('stock.picking')
        stock_move_obj = self.pool.get('stock.move')
        for pick in sale_order.picking_ids:
            if pick.state == 'done':
                continue
            if pick.state == 'confirmed':
                stock_picking_obj.action_assign(cr, uid, pick.ids, context = context)
            if pick.state != 'assigned':
                to_move_names = [x.name for x in pick.move_lines if x.state not in ('draft', 'cancel', 'assigned', 'done')]
                display_name = ','.join(to_move_names)
                raise osv.except_osv(u'订单同步失败', u'下面产品无法发货: "%s"。请检查库存' % (display_name))
        
        # 发货
        for pick in sale_order.picking_ids:
            if pick.state == 'done':
                continue
            pick_context = context.copy()
            pick_context.update({
                'active_model': 'stock.picking',
                'active_ids': pick.ids,
                'active_id': len(pick.ids) and pick.ids[0] or False
            })
            # 设置发货时间
            stock_picking_obj.do_transfer(cr, uid, pick.ids, context = pick_context)
            stock_picking_obj.write(cr, uid, pick.ids, {'date_done': taobao_order.delivery_date}, context=context)
            for move_line in pick.move_lines:
                stock_move_obj.write(cr, uid, move_line.ids, {'date': taobao_order.delivery_date}, context=context)


        # 确认发票
        invoice_obj = self.pool.get('account.invoice')
        if not sale_order.invoice_exists:
            vals = order_obj.manual_invoice(cr, uid, order_ids, context = context)
            inv_id = vals['res_id']
        else:
            inv_id = sale_order.invoice_ids[0].id
        
        for inv in sale_order.invoice_ids:
            if inv.state == 'draft':
                day_date = datetime2day(taobao_order.delivery_date)
                inv.write({'date_invoice': day_date, 'date_due': day_date})
                invoice_obj.signal_workflow(cr, uid, [inv.id], 'invoice_open')

        if taobao_order.order_state == 'send':
            return True

        # 确认付款   inv.state == 'open'
        journal_pool = self.pool.get('account.journal')
        journal_id = journal_pool.search(cr, uid, [('name', '=', u'银行')], context = context)[0]
        journal = journal_pool.browse(cr, uid, [journal_id], context = context)[0]
        for inv in sale_order.invoice_ids:
            if inv.state != 'open':
                continue
            # 设置发票确认日期
            day_date = datetime2day(taobao_order.end_date)
            inv = inv.with_context(date_p=day_date)
            inv.write({'date_due': day_date})
            period = inv.period_id.with_context(context).find(day_date)[:1]
            inv.pay_and_reconcile(
                pay_amount=inv.amount_total,
                pay_account_id=journal.default_debit_account_id.id,
                period_id=period.id,
                pay_journal_id=journal_id,
                writeoff_acc_id=journal.default_debit_account_id.id,
                writeoff_period_id=period.id,
                writeoff_journal_id=journal_id,
                name='/'
            )
        return True

    def action_sync(self, cr, uid, ids, context=None):
        for taobao_order in self.browse(cr, uid, ids, context=context):
            if taobao_order.sync_state == 'none' or context['force']:
                self.create_sale_order(cr, uid, taobao_order, context=context)
            if taobao_order.sync_state != 'done' or context['force']:
                self.update_sale_order(cr, uid, taobao_order, context=context)
        self.write(cr, uid, ids, {'sync_state': 'done'}, context=context)
        return True

class taobao_order_line(osv.osv):
    _name = 'taobao.order.line'
    _description = u'淘宝订单行'
    _columns = {
        'order_id': fields.many2one('taobao.order', u'订单', required=True, ondelete='cascade', select=True, readonly=True),
        'product_id': fields.char(u'名称'),
        'qty': fields.float(u'数量'),
        'price_unit': fields.float(u'单价', required=True),
        'line_state': fields.selection([
            ('wait_pay', u'等待付款'), ('wait_send', u'等待发货'), ('send', u'已发货'),
            ('success', u'交易成功'), ('close', u'自动关闭'), ('cancel', u'已取消')
        ], u'子订单状态', required=True,  readonly=True),
    }