from flask import Flask, request, jsonify, make_response
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

# DeepSeek API Settings
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
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
    print(f"Received XML: {xml_data}")

    try:
        root = ET.fromstring(xml_data)

        # Extract the message content
        msg_type = root.find("MsgType").text
        from_user = root.find("FromUserName").text
        to_user = root.find("ToUserName").text

        # Simple response
        response = "Received your message! This is a test message."

        # Create the XML response
        response_xml = f"""
        <xml>
        <ToUserName><![CDATA[{from_user}]]></ToUserName>
        <FromUserName><![CDATA[{to_user}]]></FromUserName>
        <CreateTime>{int(time.time())}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{response}]]></Content>
        </xml>
        """

        print(f"Sending response: {response_xml}")
        return response_xml, 200, {"Content-Type": "application/xml"}
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return "success"  # Return "success" to avoid WeChat server retrying


"""
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
# <xml>
#    <ToUserName><![CDATA[{from_user}]]></ToUserName>
#    <FromUserName><![CDATA[{to_user}]]></FromUserName>
#    <CreateTime>{int(time.time())}</CreateTime>
#    <MsgType><![CDATA[text]]></MsgType>
#    <Content><![CDATA[{deepseek_reply}]]></Content>
# </xml>
# return response_xml, 200, {"Content-Type": "application/xml"}
# else:
#    return ""


"""
def call_deepseek_api(message):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,  # Optional parameter
        "max_tokens": 2048,  # Optional parameter
    }

    print(f"Sending request to DeepSeek API: {payload}")

    try:
        response = requests.post(
            DEEPSEEK_API_URL, json=payload, headers=headers, timeout=5
        )
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
"""


# Call DeepSeek API to get a response
def call_deepseek_api(message):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 1000,
    }

    # Update API URL
    api_url = "https://api.deepseek.com/v1/chat/completions"
    print(f"Sending request to DeepSeek API URL: {api_url}")
    print(f"With payload: {payload}")

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    try:
        # response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response = session.post(api_url, json=payload, headers=headers, timeout=30)
        print(f"Response status code: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text[:500]}...")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed with detailed error: {str(e)}")
        return f"API request failed: {str(e)}"

    try:
        deepseek_response = response.json()
        print(f"DeepSeek API response: {deepseek_response}")

        if "choices" in deepseek_response and len(deepseek_response["choices"]) > 0:
            return deepseek_response["choices"][0]["message"]["content"]
        else:
            return f"API response format error: {deepseek_response}"
    except Exception as e:
        return f"Error processing API response: {str(e)}"


# Test the DeepSeek API
@app.route("/wechat/test", methods=["GET"])
def test_deepseek():
    test_message = request.args.get("message", "Test DeepSeek API")
    result = call_deepseek_api(test_message)
    return jsonify({"message": test_message, "response": result})


# Simple test endpoint
@app.route("/wechat/simple-test", methods=["GET"])
def simple_test():
    return jsonify({"status": "ok", "message": "Server is working"})


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
