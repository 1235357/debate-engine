import json
from typing import Optional, Dict, Any, List
import litellm
from litellm import completion


class LLMProvider:
    """LLM 供应商"""
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        """初始化"""
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.params = params or {}
        
        # 配置 litellm
        litellm.set_verbose = False
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        stream: bool = False,
    ) -> str:
        """完成文本"""
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        try:
            response = completion(
                model=self.model,
                messages=all_messages,
                api_key=self.api_key,
                base_url=self.base_url,
                stream=stream,
                **self.params,
            )
            
            if stream:
                full_text = ""
                for chunk in response:
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            full_text += delta.content
                return full_text
            else:
                return response.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM completion: {e}")
            raise
    
    def complete_structured(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """完成结构化输出"""
        # 构建结构化输出的系统提示
        schema_instruction = f"""
你必须严格按照以下 JSON Schema 格式输出，不要输出任何 Schema 之外的内容：

{json.dumps(schema, ensure_ascii=False, indent=2)}

只输出 JSON，不要有任何前缀说明或 Markdown 代码块标记。
"""
        enhanced_system = system_prompt + "\n\n" + schema_instruction
        
        # 调用模型
        raw_response = self.complete(
            messages=messages,
            system_prompt=enhanced_system,
            stream=False,
        )
        
        # 清理响应
        clean = raw_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        # 解析 JSON
        try:
            return json.loads(clean.strip())
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            print(f"Raw response: {raw_response}")
            raise
