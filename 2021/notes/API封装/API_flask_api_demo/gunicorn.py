# coding=utf-8
import multiprocessing

# 这边写127.0.0.1只会监听内网端口，需要写出0.0.0.0才能监听外网端口
bind = '0.0.0.0:11330'
# 设置工作进程数
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 1

# 设置等待服务的客户数量，默认即为2048
backlog = 2048
# 设置工作模式，对性能影响很大，默认为sync
worker_class = "gevent"
# 设置每个线程最大并发量，默认为1000
worker_connections = 3000
# 设置守护进程,将进程交给supervisor管理，默认即为False
daemon = False
# 设置进程文件路径
# pidfile = '/var/run/gunicorn.pid'
# 设置访问日志和错误信息日志路径
# accesslog = './logs/acess.log'
#
# errorlog = './logs/error.log'
# # 设置日志格式
# access_log_format = '%(h)s %(l)s %(u)s %(t)s %(l)s %(D)s'
# # 设置日志等级
# loglevel = 'info'

timeout = 3600
