# -*- coding: utf-8 -*- #
from openerp.osv import osv, fields

class taobao_order_sync_wizard(osv.osv_memory):
    _name = 'taobao.order.sync.wizard'    
 
    def taobao_order_sync(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('taobao.order')
        order_obj.action_sync(cr, uid, context.get(('active_ids'), []), context=context)    
        return {'type': 'ir.actions.act_window_close'}
 