# -*- coding: utf-8 -*- #
from openerp.osv import osv, fields

class taobao_order_sync_wizard(osv.osv_memory):
    _name = 'taobao.order.sync.wizard'

    _columns = {
        'force': fields.boolean('强制同步', help="选择该项将对已同步订单重新强制同步."),
    }
    _defaults = {
        'force': False
    }
 
    def taobao_order_sync(self, cr, uid, ids, context=None):
        sync_obj = self.browse(cr, uid, ids)[0]

        if not context:
            context = {}
        sync_context = dict(context, force=sync_obj.force)

        order_obj = self.pool.get('taobao.order')
        order_obj.action_sync(cr, uid, context.get(('active_ids'), []), context=sync_context)    
        return {'type': 'ir.actions.act_window_close'}
 