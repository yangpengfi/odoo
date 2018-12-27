# @author: Xiao
# @email: voewjwz@sina.com
# @time: 12/21/18

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import os
import logging
import json
from collections import OrderedDict
try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

logger = logging.getLogger(__name__)

base_url = 'http://127.0.0.1:8069'
db = 'odoo236'
user = 'ic'
pwd = 'ic'

def connet_ic():
    """
    获取session
    :return:
    """
    data = {'jsonrpc': '2.0', 'params': {'db': db, 'login': user, 'password': pwd}}
    request = requests.post(base_url + '/web/session/authenticate', json=data)
    try:
        res = request.json()
        session = res['result'].get('session_id')
    except Exception as e:
        logger.error(e)
        session = None
    return session

def test_request():
    session = connet_ic()
    if session:
        headers = {'X-Openerp-Session-Id': session}
        data = {}
        res = requests.post(base_url+'/import/getpartner', json=data, headers=headers)
        result = res.json()
        print(result)

def Excel_to_json(file):
    wb = xlrd.open_workbook(file)
    convert_list = []
    sh = wb.sheet_by_index(0)
    title = sh.row_values(0)  # 表头，json文件的key
    for rownum in range(1, sh.nrows):
        rowvalue = sh.row_values(rownum)
        single = OrderedDict()  # 有序字典
        for colnum in range(0, len(rowvalue)):
            print("key:{0}, value:{1}".format(title[colnum], rowvalue[colnum]))
            single[title[colnum]] = rowvalue[colnum]
        convert_list.append(single)

    j = json.dumps(convert_list)

    with open("/home/xiao/file.json", "w", encoding="utf8") as f:
        f.write(j)

if __name__ == '__main__':
    # test_request()
    file = '/home/xiao/idt1129.xlsx'
    Excel_to_json(file)