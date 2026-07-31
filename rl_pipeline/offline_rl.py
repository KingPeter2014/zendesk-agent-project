"""
Offline RL demo: converts logged trajectories to an ORPO fine-tuning dataset
and runs a training loop using Hugging Face TRL on Qwen2.5-0.5B.

Usage:
    python rl_pipeline/offline_rl.py

Downloads Qwen/Qwen2.5-0.5B (~1GB) on first run.
Uses CPU if no GPU is available (slow but functional for demo purposes).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from rl_pipeline.trajectory_logger import TrajectoryLogger
from rl_pipeline.reward_functions import composite_reward


MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = Path("data/orpo_model")
DATASET_PATH = Path("data/orpo_dataset.json")
MIN_TRAJECTORIES = 10
TRAINING_STEPS = 50  # Keep low for demo; increase for real training


def _trajectory_to_orpo_sample(traj: dict) -> dict | None:
    """
    Convert a trajectory record into an ORPO prompt/chosen/rejected triplet.
    Chosen = high-reward trajectory summary; Rejected = low-reward alternative.
    """
    reward = traj.get("reward") or 0.0
    steps = traj.get("steps", [])
    if not steps:
        return None

    ticket_id = traj["ticket_id"][:8]
    outcome = traj.get("outcome", "unknown")

    tool_calls = [
        tc["tool_name"]
        for step in steps
        for tc in step.get("tool_calls", [])
    ]
    tool_summary = ", ".join(tool_calls) if tool_calls else "none"

    prompt = f"Resolve ticket {ticket_id}. Available tools: lookup_order, process_refund, check_policy, escalate_ticket, send_notification."

    if reward >= 0.6:
        chosen = f"I will {tool_summary}. Outcome: {outcome}. This achieves the objective efficiently."
        rejected = f"I will escalate immediately without investigation. Outcome: escalated."
    else:
        chosen = f"I should have used {tool_summary} more carefully. Better approach: lookup first, then act."
        rejected = f"I will {tool_summary}. Outcome: {outcome}. This approach was suboptimal."

    return {
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "reward": reward,
    }


def build_dataset(logger: TrajectoryLogger) -> list[dict]:
    trajectories = logger.fetch_all()
    if len(trajectories) < MIN_TRAJECTORIES:
        print(f"Only {len(trajectories)} trajectories found. Generating synthetic ones for demo...")
        trajectories = _generate_synthetic_trajectories(500)

    samples = [_trajectory_to_orpo_sample(t) for t in trajectories]
    samples = [s for s in samples if s is not None]

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATASET_PATH, "w") as f:
        json.dump(samples, f, indent=2)

    print(f"Dataset: {len(samples)} samples → {DATASET_PATH}")
    return samples


def _generate_synthetic_trajectories(n: int) -> list[dict]:
    """Generate synthetic trajectory records when real data is sparse."""
    tools = ["lookup_order", "process_refund", "check_policy", "escalate_ticket", "send_notification"]
    outcomes = ["resolved", "resolved", "resolved", "escalated", "failed"]
    records = []
    for i in range(n):
        num_steps = random.randint(1, 4)
        steps = []
        for _ in range(num_steps):
            tool = random.choice(tools)
            steps.append({
                "tool_calls": [{"tool_name": tool, "error": None if random.random() > 0.1 else "timeout"}]
            })
        outcome = random.choice(outcomes)
        records.append({
            "trajectory_id": f"synthetic_{i}",
            "ticket_id": f"ticket_{i:05d}",
            "agent_id": "billing-001",
            "steps": steps,
            "outcome": outcome,
            "reward": random.uniform(0.0, 1.0) if outcome == "resolved" else random.uniform(-0.3, 0.5),
            "latency_ms": random.uniform(100, 3000),
        })
    return records


def run_training(samples: list[dict]) -> dict:
    """Run ORPO fine-tuning using HF TRL."""
    try:
        import torch
        from datasets import Dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from trl import ORPOConfig, ORPOTrainer
    except ImportError as e:
        print(f"Missing dependency: {e}. Install with: pip install trl transformers datasets torch")
        return {"error": str(e)}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Training on: {device} (CPU training is slow — expected for demo)")

    print(f"Loading tokeniser and model: {MODEL_ID} ...")
    tokeniser = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32)

    hf_data = {
        "prompt": [s["prompt"] for s in samples],
        "chosen": [
            [{"role": "user", "content": s["prompt"]}, {"role": "assistant", "content": s["chosen"]}]
            for s in samples
        ],
        "rejected": [
            [{"role": "user", "content": s["prompt"]}, {"role": "assistant", "content": s["rejected"]}]
            for s in samples
        ],
    }
    dataset = Dataset.from_dict(hf_data)
    split = dataset.train_test_split(test_size=0.1, seed=42)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config = ORPOConfig(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=1,
        max_steps=TRAINING_STEPS,
        per_device_train_batch_size=2,
        learning_rate=8e-6,
        logging_steps=10,
        save_steps=TRAINING_STEPS,
        report_to="none",
        remove_unused_columns=False,
        max_length=256,
        max_prompt_length=128,
    )

    trainer = ORPOTrainer(
        model=model,
        args=config,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        tokenizer=tokeniser,
    )

    print(f"Starting ORPO training ({TRAINING_STEPS} steps)...")
    train_result = trainer.train()

    report = {
        "model": MODEL_ID,
        "device": device,
        "training_steps": TRAINING_STEPS,
        "dataset_size": len(samples),
        "train_loss": round(train_result.training_loss, 4),
        "output_dir": str(OUTPUT_DIR),
    }

    report_path = OUTPUT_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Training complete. Report → {report_path}")
    return report


def main() -> None:
    logger = TrajectoryLogger()
    print(f"Loaded {logger.count()} trajectories from database")

    samples = build_dataset(logger)
    report = run_training(samples)

    from rich.console import Console
    from rich.panel import Panel
    Console().print(Panel(json.dumps(report, indent=2), title="RL Training Report", border_style="green"))


if __name__ == "__main__":
    main()
