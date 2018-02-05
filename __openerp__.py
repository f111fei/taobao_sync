# -*- encoding: utf-8 -*-

{
    'name': '淘宝订单同步',
    'version': '1.0',
    "category" : "Hidden",
    'description': """ 本模块实现：
    1) 淘宝销售订单导入
    2) 淘宝销售订单同步
    3) 淘宝商品同步
    4) 根据淘宝订单状态自动发货
    5) 根据淘宝订单状态自动确认发票
    """,
    'author': 'xzper',
    'website': 'http://xzper.com',
    'depends': ['sale'],
    'init_xml': [],
    'data': [
        'wizard/taobao_order_sync_wizard.xml',
        'view/sale_order_dates_view.xml',
        'view/taobao_view.xml',
        'taobao_action.xml'
     ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'application': True,
}