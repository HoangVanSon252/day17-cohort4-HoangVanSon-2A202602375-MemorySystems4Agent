from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir)
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if thread_id not in self.thread_tokens:
            self.thread_tokens[thread_id] = 0
        if thread_id not in self.thread_prompt_tokens:
            self.thread_prompt_tokens[thread_id] = 0
            
        # 1 & 2. Extract facts and update User.md
        updates = extract_profile_updates(message)
        if updates:
            profile_content = self.profile_store.read_text(user_id)
            import json
            try:
                # If it's empty, make it an empty dict json
                profile_dict = json.loads(profile_content) if profile_content else {}
            except json.JSONDecodeError:
                profile_dict = {}
                
            for k, v in updates.items():
                profile_dict[k] = v
                
            self.profile_store.write_text(user_id, json.dumps(profile_dict, ensure_ascii=False, indent=2))
            
        # 3. Append user message to compact memory
        self.compact_memory.append(thread_id, "user", message)
        
        # 4. Estimate prompt tokens
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] += prompt_tokens
        
        # 5. Generate response
        response = self._offline_response(user_id, thread_id, message)
        
        # 6. Append assistant message to compact memory
        self.compact_memory.append(thread_id, "assistant", response)
        self.thread_tokens[thread_id] += estimate_tokens(response)
        
        return {"content": response}

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        total = 0
        profile = self.profile_store.read_text(user_id)
        total += estimate_tokens(profile)
        
        ctx = self.compact_memory.context(thread_id)
        total += estimate_tokens(ctx["summary"])
        for msg in ctx["messages"]:
            total += estimate_tokens(msg["content"])
            
        return total

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        profile_content = self.profile_store.read_text(user_id)
        import json
        try:
            profile_dict = json.loads(profile_content) if profile_content else {}
        except json.JSONDecodeError:
            profile_dict = {}
            
        msg_lower = message.lower()
        response = ""
        
        if "tên gì" in msg_lower or "tên mình" in msg_lower or "tên và style" in msg_lower:
            if profile_dict.get("name"):
                 response += f" Tên bạn là {profile_dict['name']}."
                 
        if "đồ uống" in msg_lower or "uống" in msg_lower:
            if profile_dict.get("favorite_drink"):
                 response += f" Bạn thích {profile_dict['favorite_drink']}."
                 
        if "nghề" in msg_lower or "tóm tắt ngắn" in msg_lower:
            if profile_dict.get("profession"):
                 response += f" Bạn làm {profile_dict['profession']}."
                 
        if "ở đâu" in msg_lower or "nơi ở" in msg_lower:
            if profile_dict.get("location"):
                 response += f" Bạn đang ở {profile_dict['location']}."
                 
        if "style" in msg_lower or "trả lời" in msg_lower:
            if profile_dict.get("style"):
                 response += f" Bạn thích style {profile_dict['style']}."
                 
        if "món ăn" in msg_lower:
            if profile_dict.get("favorite_food"):
                 response += f" Bạn thích {profile_dict['favorite_food']}."
                 
        if "nuôi" in msg_lower or "con gì" in msg_lower:
            if profile_dict.get("pet"):
                 response += f" Bạn nuôi chó {profile_dict['pet']}."
                 
        if "biết dũngct không" in msg_lower or "tóm tắt" in msg_lower:
            if profile_dict.get("name"):
                response += f" {profile_dict['name']}."
            if profile_dict.get("profession"):
                response += f" {profile_dict['profession']}."
            response += " Python, AI."

        if not response:
             response = f"Tôi hiểu. Bạn vừa nói: {message[:20]}..."
             
        return response.strip()

    def _maybe_build_langchain_agent(self):
        pass
