import requests, json

# 本地调用时，ip 设置为 0.0.0.0 即可；否则需要指定具体的 ip
# 另外需要指定对应端口和路由（demo中端口：11330，路由：test）
url = "http://0.0.0.0:11330/test"
headers = {
    "Content-Type": "application/json"
}
text = "Robbin"
body = {
    "text": text,
}
r = requests.post(url, headers=headers, data=json.dumps(body))
print(r.status_code)
# 获取保存在字典中的对应结果
# 返回的 r.text 是 str格式，需要先转换为 json
res = json.loads(r.text)["response"]
print(res)