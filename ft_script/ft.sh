CUDA_VISIBLE_DEVICES=0,1 \
swift sft \
    --model_type qwen2-7b-instruct \
    --dataset ft_data.json \
    --num_train_epochs 10 \
    --save_steps 10\
    --sft_type lora \
    --output_dir output