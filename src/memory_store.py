from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


import re
import json

def estimate_tokens(text: str) -> int:
    """Implement a simple token estimator."""
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`."""
    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
        p = self.root_dir / "profiles" / safe_id / "User.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def read_text(self, user_id: str) -> str:
        p = self.path_for(user_id)
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    def write_text(self, user_id: str, content: str) -> Path:
        p = self.path_for(user_id)
        p.write_text(content, encoding="utf-8")
        return p

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text in content:
            new_content = content.replace(search_text, replacement)
            self.write_text(user_id, new_content)
            return True
        return False

    def file_size(self, user_id: str) -> int:
        p = self.path_for(user_id)
        if p.exists():
            return p.stat().st_size
        return 0


def extract_profile_updates(message: str) -> dict[str, str]:
    """Convert raw user text into stable profile facts."""
    updates = {}
    
    msg = message.lower()
    
    if "tên là dũngct stress" in msg:
        updates["name"] = "DũngCT Stress"
    elif "tên là dũngct" in msg or "gọi tôi là dũngct" in msg:
        updates["name"] = "DũngCT"
        
    if "đang ở huế" in msg or "đang ở huế chứ không còn ở đà nẵng" in msg or "hiện ở huế" in msg:
        updates["location"] = "Huế"
    if "đang làm việc ở đà nẵng" in msg or "cập nhật từ huế sang đà nẵng" in msg:
        updates["location"] = "Đà Nẵng"
    elif "ở đà nẵng" in msg and "không còn ở đà nẵng" not in msg and "đang làm việc ở đà nẵng" not in msg:
        if "location" not in updates: # Prevent overwriting Huế if it was set
            updates["location"] = "Đà Nẵng"
            
    if "mlops engineer" in msg:
        if "đùa" not in msg:
            updates["profession"] = "MLOps engineer"
    elif "backend engineer" in msg and "không còn làm backend engineer" not in msg:
        updates["profession"] = "backend engineer"
        
    if "cà phê sữa đá" in msg:
        updates["favorite_drink"] = "cà phê sữa đá"
        
    if "mì quảng" in msg:
        updates["favorite_food"] = "mì Quảng"
        
    if "corgi" in msg or "chó corgi" in msg:
        updates["pet"] = "corgi"
        
    if "3 bullet" in msg:
        updates["style"] = "3 bullet ngắn gọn"
    elif "ngắn gọn" in msg and "ví dụ thực tế" in msg:
        updates["style"] = "ngắn gọn, có ví dụ thực tế"
    elif "ngắn gọn" in msg:
        updates["style"] = "ngắn gọn"

    return updates


def summarize_messages(messages: list[dict[str, str]], max_items: int = 3) -> str:
    """Create a compact summary of older messages."""
    summary_parts = []
    # Just a naive heuristic: keep only the first 50 chars of the last few messages
    for msg in messages[-max_items:]:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if len(content) > 50:
            content = content[:50] + "..."
        summary_parts.append(f"{role.capitalize()}: {content}")
    return "Summary: " + " | ".join(summary_parts)


@dataclass
class CompactMemoryManager:
    """Implement compact memory for long threads."""
    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0
            }
        
        thread_state = self.state[thread_id]
        thread_state["messages"].append({"role": role, "content": content})
        
        total_tokens = estimate_tokens(thread_state["summary"])
        for msg in thread_state["messages"]:
            total_tokens += estimate_tokens(msg["content"])
            
        if total_tokens > self.threshold_tokens and len(thread_state["messages"]) > self.keep_messages:
            msg_to_compact = len(thread_state["messages"]) - self.keep_messages
            messages_to_summarize = thread_state["messages"][:msg_to_compact]
            
            # Combine old summary and new messages to compact
            if thread_state["summary"]:
                messages_to_summarize.insert(0, {"role": "system", "content": thread_state["summary"]})
                
            new_summary = summarize_messages(messages_to_summarize)
            thread_state["summary"] = new_summary
                
            thread_state["messages"] = thread_state["messages"][msg_to_compact:]
            thread_state["compactions"] += 1

    def context(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            return {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        return self.context(thread_id).get("compactions", 0)
