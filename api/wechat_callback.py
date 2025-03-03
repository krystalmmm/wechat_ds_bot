from flask import Flask, request, jsonify, make_response
import requests
import xml.etree.ElementTree as ET
import hashlib
import time

app = Flask(__name__)

# DeepSeek API Settings
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_API_KEY = "sk-a67d0f343e2149399839af4d304fb758"

# WeChat Token
WECHAT_TOKEN = "ds_wechat_bot_2025"


# Handle the verification request from the WeChat server
@app.route("/wechat/callback", methods=["GET"])
def wechat_verify():
    print("WeChat callback endpoint hit!")
    # Retrieve the parameters sent by the WeChat server
    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")
    echostr = request.args.get("echostr", "")

    # Debugging logs
    print(
        f"Received WeChat request: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}"
    )

    # Check if any parameter is missing
    if not all([signature, timestamp, nonce, echostr]):
        print("Missing one or more parameters from WeChat request.")
        return "Missing parameters", 400

    # Generate the signature based on received timestamp, nonce, and token
    is_valid = check_signature(signature, timestamp, nonce)

    # Compare received signature with generated signature
    if is_valid:
        print("Signature is valid.")
        return echostr
    else:
        print("Invalid signature.")
        return "Invalid signature", 403


# Handle WeChat messages
@app.route("/wechat/callback", methods=["POST"])
def wechat_callback():
    # Parse the XML data sent by the WeChat server
    xml_data = request.data
    root = ET.fromstring(xml_data)

    # Extract the message content
    msg_type = root.find("MsgType").text
    if msg_type == "text":
        user_message = root.find("Content").text
        from_user = root.find("FromUserName").text
        to_user = root.find("ToUserName").text

        # Call the DeepSeek API to get a response
        deepseek_reply = call_deepseek_api(user_message)

        # Construct the XML response to return to the WeChat server
        response_xml = f"""
        <xml>
            <ToUserName><![CDATA[{from_user}]]></ToUserName>
            <FromUserName><![CDATA[{to_user}]]></FromUserName>
            <CreateTime>{int(time.time())}</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[{deepseek_reply}]]></Content>
        </xml>
        """
        return response_xml, 200, {"Content-Type": "application/xml"}
    else:
        return ""


# Call DeepSeek API to get a response
def call_deepseek_api(message):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message}],
    }

    print(f"Sending request to DeepSeek API: {payload}")

    try:
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        response.raise_for_status()  # Check HTTP Status Code
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")  # Print Error Message
        return "Sorry, there was an error processing your request."

    deepseek_response = response.json()
    print(f"DeepSeek API response: {deepseek_response}")  # Print API Response

    # Extract the response message from the API response
    if "choices" in deepseek_response and len(deepseek_response["choices"]) > 0:
        return deepseek_response["choices"][0]["message"]["content"]
    else:
        return "Sorry, I didn't understand that."


# Test the DeepSeek API
@app.route("/wechat/test", methods=["GET"])
def test_deepseek():
    test_message = request.args.get("message", "测试 DeepSeek API")
    result = call_deepseek_api(test_message)
    return jsonify({"message": test_message, "response": result})


# Verify the signature
def check_signature(signature, timestamp, nonce):
    token = WECHAT_TOKEN

    # Sort timestamp, nonce, and token in lexicographical order
    tmp_list = sorted([token, timestamp, nonce])

    # Concatenate the sorted list into a single string
    tmp_str = "".join(tmp_list)

    # Generate the SHA1 hash of the concatenated string
    calculated_signature = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()

    return calculated_signature == signature


# Generate a signature for testing
import hashlib


def generate_signature(token, timestamp, nonce):
    tmp_list = sorted([token, timestamp, nonce])
    tmp_str = "".join(tmp_list)
    tmp_str = hashlib.sha1(tmp_str.encode("utf-8")).hexdigest()
    return tmp_str


# Retrieve the signature for testing
token = WECHAT_TOKEN
timestamp = "123456789"
nonce = "123456"

signature = generate_signature(token, timestamp, nonce)
print(f"Signature: {signature}")

# Remove this block of code when deploying to production
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True, threaded=True)
