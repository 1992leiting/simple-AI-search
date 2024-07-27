CUDA_VISIBLE_DEVICES=0,1 \
swift sft \
    --model_type qwen2-7b-instruct \
    --dataset /edisk/projects/swift_ft/ft_data.json \
    --num_train_epochs 20 \
    --save_steps 10\
    --sft_type lora \
    --output_dir output