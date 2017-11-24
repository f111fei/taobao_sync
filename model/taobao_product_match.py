# -*- encoding: utf-8 -*-

from openerp.osv import fields,osv

class taobao_product_match(osv.osv):
    _name = 'taobao.product.match'
    _description = u"淘宝商品匹配"

    _columns = {
        'name': fields.char(u'淘宝产品名', required=True),
        'product_id': fields.many2one('product.product', '产品', domain=[('sale_ok', '=', True)], required=True, ondelete='cascade'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '淘宝产品名 must be unique!')
    ]

    def find_product(self, cr, uid, name, context=None):
        match_ids = self.search(cr, uid, [('name', '=', name)], context = context)
        if len(match_ids) == 1:
            match_obj = self.browse(cr, uid, match_ids[0], context=context)
            return match_obj.product_id.id
        else:
            raise osv.except_osv(u'匹配错误', u'找不到匹配的产品: "%s"' % (name))
