---
license: apache-2.0
tags:
- generated_from_trainer
metrics:
- wer
model-index:
- name: whisper-base-ar-quran
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

# whisper-base-ar-quran

This model is a fine-tuned version of [openai/whisper-base](https://huggingface.co/openai/whisper-base) on the None dataset.
It achieves the following results on the evaluation set:
- Loss: 0.0839
- Wer: 5.7544

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 0.0001
- train_batch_size: 16
- eval_batch_size: 8
- seed: 42
- distributed_type: multi-GPU
- num_devices: 8
- total_train_batch_size: 128
- total_eval_batch_size: 64
- optimizer: Adam with betas=(0.9,0.999) and epsilon=1e-08
- lr_scheduler_type: linear
- lr_scheduler_warmup_steps: 500
- training_steps: 5000
- mixed_precision_training: Native AMP

### Training results

| Training Loss | Epoch | Step | Validation Loss | Wer     |
|:-------------:|:-----:|:----:|:---------------:|:-------:|
| 0.1092        | 0.05  | 250  | 0.1969          | 13.3890 |
| 0.0361        | 0.1   | 500  | 0.1583          | 10.6375 |
| 0.0192        | 0.15  | 750  | 0.1109          | 8.8468  |
| 0.0144        | 0.2   | 1000 | 0.1157          | 7.9754  |
| 0.008         | 0.25  | 1250 | 0.1000          | 7.5360  |
| 0.0048        | 1.03  | 1500 | 0.0933          | 6.8227  |
| 0.0113        | 1.08  | 1750 | 0.0955          | 6.9638  |
| 0.0209        | 1.13  | 2000 | 0.0824          | 6.3586  |
| 0.0043        | 1.18  | 2250 | 0.0830          | 6.3444  |
| 0.002         | 1.23  | 2500 | 0.1015          | 6.3025  |
| 0.0013        | 2.01  | 2750 | 0.0863          | 6.0639  |
| 0.0014        | 2.06  | 3000 | 0.0905          | 6.0213  |
| 0.0018        | 2.11  | 3250 | 0.0864          | 6.0293  |
| 0.0008        | 2.16  | 3500 | 0.0887          | 5.9308  |
| 0.0029        | 2.21  | 3750 | 0.0777          | 5.9159  |
| 0.0022        | 2.26  | 4000 | 0.0847          | 5.8749  |
| 0.0005        | 3.05  | 4250 | 0.0827          | 5.8352  |
| 0.0003        | 3.1   | 4500 | 0.0826          | 5.7800  |
| 0.0006        | 3.15  | 4750 | 0.0833          | 5.7625  |
| 0.0003        | 3.2   | 5000 | 0.0839          | 5.7544  |


### Framework versions

- Transformers 4.26.0.dev0
- Pytorch 1.13.0+cu117
- Datasets 2.7.1.dev0
- Tokenizers 0.13.2