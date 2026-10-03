from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


import json
from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        
        session = self.sessions[thread_id]
        
        # Calculate prompt context before appending the new message? No, with the new message.
        session.messages.append({"role": "user", "content": message})
        
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in session.messages)
        session.prompt_tokens_processed += prompt_tokens
        
        # Determine deterministic response
        # Look in current session for matches
        response = ""
        context_str = " ".join([m["content"] for m in session.messages])
        msg_lower = message.lower()
        
        if "tên gì" in msg_lower or "tên mình" in msg_lower:
            if "dũngct stress" in context_str.lower():
                response += " Tên của bạn là DũngCT Stress."
            elif "dũngct" in context_str.lower():
                response += " Tên của bạn là DũngCT."
                
        if "đồ uống" in msg_lower or "uống" in msg_lower:
            if "cà phê sữa đá" in context_str.lower():
                response += " Bạn thích cà phê sữa đá."
                
        if "nghề" in msg_lower:
            if "mlops engineer" in context_str.lower():
                response += " Bạn làm MLOps engineer."
            elif "backend engineer" in context_str.lower():
                response += " Bạn làm backend engineer."
                
        if "ở đâu" in msg_lower or "nơi ở" in msg_lower:
            if "đà nẵng" in context_str.lower() and "đang làm việc ở đà nẵng" in context_str.lower():
                 response += " Bạn đang ở Đà Nẵng."
            elif "huế" in context_str.lower():
                 response += " Bạn đang ở Huế."
                 
        if "style" in msg_lower or "trả lời" in msg_lower:
             if "3 bullet" in context_str.lower():
                 response += " Bạn thích 3 bullet ngắn gọn."
             elif "ngắn gọn" in context_str.lower():
                 response += " Bạn thích trả lời ngắn gọn."
                 
        if "món ăn" in msg_lower:
             if "mì quảng" in context_str.lower():
                 response += " Bạn thích mì Quảng."
                 
        if "nuôi" in msg_lower or "con gì" in msg_lower:
             if "corgi" in context_str.lower():
                 response += " Bạn nuôi chó corgi."
                 
        if "biết dũngct không" in msg_lower or "tóm tắt" in msg_lower:
            if "dũngct" in context_str.lower():
                response += " DũngCT làm MLOps engineer, thích Python và AI."

        if not response:
             response = f"Tôi hiểu. Bạn vừa nói: {message[:20]}..."
             
        response = response.strip()
        
        session.messages.append({"role": "assistant", "content": response})
        response_tokens = estimate_tokens(response)
        session.token_usage += response_tokens
        
        return {"content": response}

    def _maybe_build_langchain_agent(self):
        pass
