import re

with open('/app/brain_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定義新的/agent端點代碼
new_agent_code = '''@app.get("/agent")
async def get_agent_panel(request: Request):
    """代理執行介面頁面 - 加入帳號密碼認證"""
    auth = _require_auth(request)
    if isinstance(auth, RedirectResponse):
        return auth
    for d in (STATIC_DIR, FALLBACK_STATIC):
        p = d / "agent-panel.html"
        if p.exists():
            return FileResponse(str(p))
    return PlainTextResponse("agent-panel.html not found", status_code=404)'''

# 使用正則表達式替換舊的/agent端點
pattern = r'@app.get\("/agent"\)[\s\S]*?return PlainTextResponse\("agent-panel\.html not found", status_code=404\)'

# 檢查是否找到匹配
if re.search(pattern, content):
    content = re.sub(pattern, new_agent_code, content, count=1)
    with open('/app/brain_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('替換成功')
else:
    print('未找到匹配的/agent端點')