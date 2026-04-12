import asyncio
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any
from ..orchestration import QuickCritiqueEngine
from ..schemas import CritiqueConfigSchema


class MCPHandler(BaseHTTPRequestHandler):
    """MCP 请求处理器"""
    
    def __init__(self, *args, **kwargs):
        self.engine = QuickCritiqueEngine()
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """处理 POST 请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data.decode('utf-8'))
            asyncio.run(self.handle_request(request))
        except Exception as e:
            self.send_error(500, str(e))
    
    async def handle_request(self, request: Dict[str, Any]):
        """处理请求"""
        tool_call = request.get('toolcall', {})
        function_name = tool_call.get('function', {}).get('name')
        arguments = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
        
        if function_name == 'debate_critique':
            await self.handle_debate_critique(arguments)
        else:
            self.send_error(404, f"Function {function_name} not found")
    
    async def handle_debate_critique(self, arguments: Dict[str, Any]):
        """处理辩论批评请求"""
        content = arguments.get('content', '')
        task_type = arguments.get('task_type', 'CODE_REVIEW')
        max_rounds = arguments.get('max_rounds', 2)
        provider_mode = arguments.get('provider_mode', 'stable')
        
        if not content:
            self.send_error(400, 'Content is required')
            return
        
        try:
            config = CritiqueConfigSchema(
                content=content,
                task_type=task_type,
                max_rounds=max_rounds,
                provider_mode=provider_mode,
            )
            
            consensus = await self.engine.critique(config)
            
            response = {
                "toolcall": {
                    "id": "debate-critique-response",
                    "type": "function",
                    "function": {
                        "name": "debate_critique",
                        "response": {
                            "content": consensus.model_dump()
                        }
                    }
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
        else:
            self.send_error(404, "Not found")


def start_mcp_server(host='0.0.0.0', port=8000):
    """启动 MCP 服务器"""
    server = HTTPServer((host, port), MCPHandler)
    print(f"MCP Server started on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    start_mcp_server()
