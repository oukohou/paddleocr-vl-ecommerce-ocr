#!/bin/bash
PYTHON="C:/Users/oukoh/.workbuddy/binaries/python/versions/3.13.12/python.exe"
SKILL_DIR="C:/Users/oukoh/AppData/Local/Programs/WorkBuddy/resources/app.asar.unpacked/resources/builtin-skills/buddy-multimodal-generation"
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDg3OTQzNDgsImlhdCI6MTc3ODU3NjY2NiwiYXV0aF90aW1lIjoxNzc3MjU4MzQ4LCJqdGkiOiI1OTVhYjhjNS0wMzg3LTQ1ODAtYTgzNC02MzE4YjY5NWEyNWQiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI2ZjYxOTBhOS05MTM3LTQzN2EtOGUyMC0zY2VkYTExZDFiMDQiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMDE4YWQ0NzktMDcxOS00M2RlLWFmMDEtYWQ5Nzc0OGNjN2I2IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi55KH54-gIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTM1NDA2NDgyMTgifQ.rbZHHtmyGthaf2tptawv0fve61ZTmanMJvw4NctS_4td9KEh97K4dTB6e23PaQgumkSUn0CI64EMymGRStGbaXW-uCkSNOSUQ0iV2TavdIaUXjWFefUk0mrGNEPWSpQksUIqzO0CkK5F4AkydlWz32NcvbXp3CYo9e-Z8oSm1SCGiC1l5kzUbXzyF5NeTicafPmogA4LiiT4sHxSvw8QnXqBU2Grc_CU7gup48P6x0jEe4BEPEVMa7BaYbEaEExbGkQCl22s2XDvAsunqOYLhRoQpZ0iTn5W19Qa8Q9LsnV4F0ZgYOWeFToM6XpX5OiECaY-Y0xESVeh3fFrl69Ksg"

PROMPT1="电商产品详情页截图，手机展示页面，白色简洁背景，上方是手机产品图，下方有文字说明区域，中文界面风格，高清质感，适合添加文字"
PROMPT2="电商促销海报背景，橙色渐变底色，现代简约风格，留白区域适合添加文字，高清质感"
PROMPT3="黑色背景电商banner，霓虹灯光效果，科技感，适合添加促销文案，深色主题"

echo "Submitting image 1..."
echo -n "$TOKEN" | "$PYTHON" "$SKILL_DIR/scripts/buddy-cloud.py" image "$PROMPT1" --resolution 1024:1024 --token-stdin --no-poll
echo ""

echo "Submitting image 2..."
echo -n "$TOKEN" | "$PYTHON" "$SKILL_DIR/scripts/buddy-cloud.py" image "$PROMPT2" --resolution 1024:1024 --token-stdin --no-poll
echo ""

echo "Submitting image 3..."
echo -n "$TOKEN" | "$PYTHON" "$SKILL_DIR/scripts/buddy-cloud.py" image "$PROMPT3" --resolution 1024:1024 --token-stdin --no-poll
echo ""
