import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from tabulate import tabulate

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Read JSON conversations from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    """Return 0 / 0.5 / 1 depending on how many expected facts appear."""
    answer_lower = answer.lower()
    matches = sum(1 for e in expected if e.lower() in answer_lower)
    if len(expected) == 0:
        return 0.0
    return matches / len(expected)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Add a lightweight quality score for offline mode."""
    # For offline, we'll just return the recall points to keep it simple.
    return recall_points(answer, expected)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Evaluate one agent over many conversations."""
    total_recall = 0.0
    total_quality = 0.0
    num_questions = 0
    total_compactions = 0
    
    last_user_id = ""

    for conv in conversations:
        thread_id = conv["id"]
        user_id = conv["user_id"]
        last_user_id = user_id
        
        # Feed all turns to the agent
        for turn in conv["turns"]:
            agent.reply(user_id=user_id, thread_id=thread_id, message=turn)
            
        total_compactions += agent.compaction_count(thread_id)
        
        # Ask recall questions in a FRESH thread
        recall_thread_id = f"{thread_id}_recall"
        
        for rq in conv["recall_questions"]:
            num_questions += 1
            question = rq["question"]
            expected = rq["expected_contains"]
            
            ans = agent.reply(user_id=user_id, thread_id=recall_thread_id, message=question)
            content = ans["content"]
            
            recall = recall_points(content, expected)
            quality = heuristic_quality(content, expected)
            
            total_recall += recall
            total_quality += quality
            
    # Calculate tokens
    if isinstance(agent, BaselineAgent):
        agent_tokens = sum(s.token_usage for s in agent.sessions.values())
        prompt_tokens = sum(s.prompt_tokens_processed for s in agent.sessions.values())
    else:
        agent_tokens = sum(agent.thread_tokens.values())
        prompt_tokens = sum(agent.thread_prompt_tokens.values())
    
    avg_recall = total_recall / num_questions if num_questions else 0.0
    avg_quality = total_quality / num_questions if num_questions else 0.0
    
    mem_size = getattr(agent, "memory_file_size", lambda uid: 0)(last_user_id) if last_user_id else 0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=agent_tokens,
        prompt_tokens_processed=prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_quality,
        memory_growth_bytes=mem_size,
        compactions=total_compactions
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Print a markdown table or tabulated output."""
    headers = ["Agent", "Agent Tokens", "Prompt Tokens", "Recall", "Quality", "Mem (bytes)", "Compactions"]
    table_data = [
        [
            r.agent_name, 
            r.agent_tokens_only, 
            r.prompt_tokens_processed, 
            f"{r.recall_score:.2f}", 
            f"{r.response_quality:.2f}", 
            r.memory_growth_bytes, 
            r.compactions
        ]
        for r in rows
    ]
    return tabulate(table_data, headers=headers, tablefmt="github")


def main() -> None:
    """Run both benchmark suites."""
    config = load_config(Path(__file__).resolve().parent.parent)
    data_dir = config.data_dir
    
    std_convs = load_conversations(data_dir / "conversations.json")
    stress_convs = load_conversations(data_dir / "advanced_long_context.json")
    
    print("=== Standard Benchmark ===")
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    
    row1 = run_agent_benchmark("Baseline", baseline, std_convs, config)
    row2 = run_agent_benchmark("Advanced", advanced, std_convs, config)
    
    print(format_rows([row1, row2]))
    
    print("\n=== Long-Context Stress Benchmark ===")
    baseline_stress = BaselineAgent(config, force_offline=True)
    advanced_stress = AdvancedAgent(config, force_offline=True)
    
    row3 = run_agent_benchmark("Baseline", baseline_stress, stress_convs, config)
    row4 = run_agent_benchmark("Advanced", advanced_stress, stress_convs, config)
    
    print(format_rows([row3, row4]))


if __name__ == "__main__":
    main()
