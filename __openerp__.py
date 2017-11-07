# -*- encoding: utf-8 -*-

{
    'name': '淘宝',
    'version': '1.0',
    "category" : "Hidden",
    'description': """ 本模块实现：
    1) 淘宝等电商网店的订单导入
    2) 自动将ERP的库存回写到电商网店
    3) 订单的运单号回写到电商网店
    4) 如果买家已签收，自动为订单开Invoice，自动确认，形成应付账款
    5) 自动导入电商网店的对账单
    """,
    'author': 'xzper',
    'website': 'http://xzper.com',
    'depends': ['sale'],
    'init_xml': [],
    'data': [
        'view/taobao_view.xml',
        'taobao_action.xml'
     ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'application': True,
}