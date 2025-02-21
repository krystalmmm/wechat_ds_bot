from flask import Flask, request, jsonify
import requests
import hashlib
import time
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 微信公众号配置
WECHAT_TOKEN = 'wechat_ds_bot_2025'  # 微信公众号的 Token
WECHAT_AES_KEY = 'LXxFbmjsS5tCD3A9UO8XI0vtFevrl5OgRuxx0Y0sTRC'  # 微信公众号的 EncodingAESKey

# DeepSeek API 配置
DEEPSEEK_API_URL = 'https://wechat-ds-bot.vercel.app/'  # DeepSeek API 的 URL，但因为我们用的是vercel，所以这里是vercel的url
DEEPSEEK_API_KEY = 'sk-a67d0f343e2149399839af4d304fb758'  # DeepSeek API 的 Key

# 验证微信公众号服务器的有效性
@app.route('/wechat/callback', methods=['GET'])
def wechat_verify():
    signature = request.args.get('signature', '')
    timestamp = request.args.get('timestamp', '')
    nonce = request.args.get('nonce', '')
    echostr = request.args.get('echostr', '')

    # 验证签名
    if check_signature(signature, timestamp, nonce):
        return echostr
    else:
        return 'Verification failed', 403

# 处理微信公众号消息
@app.route('/wechat/callback', methods=['POST'])
def wechat_callback():
    # 解析 XML 数据
    xml_data = request.data
    root = ET.fromstring(xml_data)
    msg_type = root.find('MsgType').text
    from_user = root.find('FromUserName').text
    to_user = root.find('ToUserName').text
    content = root.find('Content').text if root.find('Content') is not None else ''

    # 调用 DeepSeek API 处理消息
    if msg_type == 'text':
        reply_content = call_deepseek_api(content)
    else:
        reply_content = '暂不支持此类型消息'

    # 返回 XML 格式的回复
    reply_xml = generate_reply_xml(to_user, from_user, reply_content)
    return reply_xml, {'Content-Type': 'application/xml'}

# 验证签名
def check_signature(signature, timestamp, nonce):
    tmp_list = sorted([WECHAT_TOKEN, timestamp, nonce])
    tmp_str = ''.join(tmp_list)
    sha1 = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    return sha1 == signature

# 调用 DeepSeek API
def call_deepseek_api(message):
    headers = {
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'message': message
    }
    response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get('reply', '')
    else:
        return '调用 DeepSeek API 失败'

# 生成回复 XML
def generate_reply_xml(to_user, from_user, content):
    return f'''
    <xml>
        <ToUserName><![CDATA[{to_user}]]></ToUserName>
        <FromUserName><![CDATA[{from_user}]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{content}]]></Content>
    </xml>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)