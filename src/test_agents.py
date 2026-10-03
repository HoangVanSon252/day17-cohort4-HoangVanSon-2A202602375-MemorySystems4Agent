import json
from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import LabConfig
from model_provider import ProviderConfig
from memory_store import UserProfileStore


def make_config(tmp_path: Path):
    """Build an isolated config for tests."""
    model = ProviderConfig(provider="openai", model_name="test", temperature=0)
    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path,
        state_dir=tmp_path / "state",
        compact_threshold_tokens=20,
        compact_keep_messages=2,
        model=model,
        judge_model=model
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Verify `User.md` can be created, updated, and edited."""
    store = UserProfileStore(tmp_path)
    
    store.write_text("user1", "Hello World")
    assert store.read_text("user1") == "Hello World"
    
    changed = store.edit_text("user1", "World", "Vietnam")
    assert changed is True
    assert store.read_text("user1") == "Hello Vietnam"
    
    assert store.file_size("user1") > 0


def test_compact_trigger(tmp_path: Path) -> None:
    """Verify long threads trigger compaction."""
    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)
    
    thread_id = "test_thread"
    for i in range(10):
        msg = f"This is a long message {i} to trigger compaction. " * 5
        agent.reply("user1", thread_id, msg)
        
    assert agent.compaction_count(thread_id) > 0
    assert len(agent.compact_memory.context(thread_id)["messages"]) == 2


def test_cross_session_recall(tmp_path: Path) -> None:
    """Verify advanced remembers across sessions and baseline does not."""
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    baseline.reply("user1", "thread1", "Tôi tên là DũngCT.")
    advanced.reply("user1", "thread1", "Tôi tên là DũngCT.")
    
    b_ans = baseline.reply("user1", "thread2", "Tôi tên gì?")
    a_ans = advanced.reply("user1", "thread2", "Tôi tên gì?")
    
    assert "DũngCT" not in b_ans["content"]
    assert "DũngCT" in a_ans["content"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Compare prompt load of baseline vs advanced on a long thread."""
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    thread_id = "long_thread"
    
    for i in range(15):
        msg = f"Đây là một tin nhắn rất dài nhằm mục đích tăng lượng token trong luồng {i} " * 5
        baseline.reply("user1", thread_id, msg)
        advanced.reply("user1", thread_id, msg)
        
    b_prompt = baseline.prompt_token_usage(thread_id)
    a_prompt = advanced.prompt_token_usage(thread_id)
    
    assert a_prompt < b_prompt
