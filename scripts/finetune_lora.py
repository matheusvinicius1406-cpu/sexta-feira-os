#!/usr/bin/env python3
"""
Fine-tune a local model on YOUR data with LoRA/QLoRA — how Sexta-Feira learns
your voice and knowledge and becomes *yours*.

This is a SEPARATE, heavy step. It is NOT part of the kernel's runtime deps and
does NOT run on the server. Run it on a machine with a GPU (a single 24GB card
handles 7B–13B comfortably). The whole loop stays offline.

--------------------------------------------------------------------------
THE LOOP (do this whenever you want the brain to "absorb" recent history):

  1. Live with the kernel: chat, and teach it facts (POST /api/v1/memory).
       -> your history accumulates in ./data/sexta_feira_os.db

  2. Export a dataset:
       cd backend-core && python ../scripts/export_training_data.py \
           --out ../data/dataset.jsonl

  3. Train an adapter (this script). Recommended stack (install separately):
       pip install unsloth  # or: transformers peft trl bitsandbytes accelerate datasets
       python scripts/finetune_lora.py \
           --base unsloth/llama-3.2-3b-instruct-bnb-4bit \
           --data data/dataset.jsonl --out data/adapters/sexta-v1

  4. Merge to GGUF and serve through Ollama (so runtime stays unchanged):
       # unsloth can export merged GGUF; then:
       ollama create sexta -f Modelfile      # Modelfile: FROM ./sexta-v1.gguf
       # point the kernel at it:  BRAIN_MODEL=sexta   in .env

That's it — the kernel keeps calling Ollama; only the model got smarter about you.
--------------------------------------------------------------------------

This file is intentionally a thin, well-commented driver so you can read and
trust every line before running it on your data.
"""
import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description="LoRA fine-tune on your local dataset")
    ap.add_argument("--base", default="unsloth/llama-3.2-3b-instruct-bnb-4bit",
                    help="base open-weights model to specialize")
    ap.add_argument("--data", default="data/dataset.jsonl", help="chat JSONL from export step")
    ap.add_argument("--out", default="data/adapters/sexta-v1", help="output adapter dir")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq", type=int, default=2048)
    args = ap.parse_args()

    try:
        from unsloth import FastLanguageModel  # type: ignore
        from unsloth.chat_templates import get_chat_template  # type: ignore
        from datasets import load_dataset  # type: ignore
        from trl import SFTTrainer  # type: ignore
        from transformers import TrainingArguments  # type: ignore
    except ImportError:
        raise SystemExit(
            "Dependências de treino não instaladas. Este passo roda numa máquina "
            "com GPU:\n    pip install unsloth datasets trl transformers peft "
            "bitsandbytes accelerate\n"
            "Depois rode este script novamente."
        )

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base, max_seq_length=args.max_seq, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=16, lora_dropout=0.0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
    )
    tokenizer = get_chat_template(tokenizer, chat_template="llama-3.1")

    dataset = load_dataset("json", data_files=args.data, split="train")

    def fmt(batch):
        texts = [
            tokenizer.apply_chat_template(m, tokenize=False, add_generation_prompt=False)
            for m in batch["messages"]
        ]
        return {"text": texts}

    dataset = dataset.map(fmt, batched=True)

    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=dataset,
        dataset_text_field="text", max_seq_length=args.max_seq,
        args=TrainingArguments(
            per_device_train_batch_size=2, gradient_accumulation_steps=4,
            warmup_steps=5, num_train_epochs=args.epochs, learning_rate=args.lr,
            logging_steps=10, optim="adamw_8bit", output_dir=args.out,
            save_strategy="epoch",
        ),
    )
    trainer.train()
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"✅ Adapter salvo em {args.out}. Próximo passo: exportar GGUF e "
          f"`ollama create sexta` (veja o cabeçalho deste arquivo).")


if __name__ == "__main__":
    main()
