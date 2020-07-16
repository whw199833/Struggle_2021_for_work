# flask简易demo

#### Flask 是一个使用 Python 编写的轻量级 Web 应用程序框架

使用时，我们需要在后端脚本中实现具体的处理逻辑，以及制定日志（方便追踪查看调用结果及错误信息）、封装逻辑函数处理的结果，并将结果封装成flask内置的Response对象，传递给前端。

具体例子请看 flask_demo.py（从前端发起requests请求，传入一个姓名，返回 Welcome + 姓名，参考requests_demo.py）

另外，**实际业务中往往对并发有一定要求**，所以我们会在 flask 服务外用 gunicorn 做进一步的封装，以满足并发需求，具体配置信息在 gunicorn.py；关于 gunicorn 框架，可以上网查找资料简单了解。

