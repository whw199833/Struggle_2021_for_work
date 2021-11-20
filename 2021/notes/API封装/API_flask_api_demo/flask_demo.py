from __future__ import print_function
import numpy as np

from flask import Flask, request, Response
import sys
import json
import os
from loguru import logger
import time
import requests

# 指定日志
BASE_DIR = "./"
def log_init(BASE_DIR=BASE_DIR):
    log_file_path = os.path.join(BASE_DIR, 'Log/test_right.log')
    err_log_file_path = os.path.join(BASE_DIR, 'Log/test_err.log')
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add(log_file_path, rotation="100 MB", encoding='utf-8')  # Automatically rotate too big file
    logger.add(err_log_file_path, rotation="100 MB", encoding='utf-8',
               level='ERROR')  # Automatically rotate too big file
    return logger

logger = log_init()

app = Flask(__name__)



def f(text):
    """处理具体逻辑的函数/类
    """
    return "Welcome " + text.strip() + ' !'



@app.route('/test', methods=['POST'])
def helper():
    request_json = request.json
    text = request_json["text"]
    try :
        logger.info("Get guest name:{}".format(text))
        res = {}
        # 处理后端的具体逻辑，并将结果保存到字典；最终传递给前端
        res["response"] = f(text)
        
    except Exception as e:
        logger.error("测试失败，请算法工程师查看！")
        logger.error(e)
        return Response(json.dumps([], ensure_ascii=False, indent=4), status=200)
    
    return Response(json.dumps(res, ensure_ascii=False, indent=4), status=200)



logger.info("欢迎使用flask-demo演示系统")
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=11225, debug=True, use_reloader=False)
