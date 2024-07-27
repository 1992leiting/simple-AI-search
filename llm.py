import openai
import os

# 替换成自己的api
print('url base', os.environ.get('VLLM_URL_BASE'))
client = openai.Client(
    api_key='sk-xxxxxxx',
    base_url=os.environ.get('VLLM_URL_BASE'),
)




def vllm_chat(msg, history=[], temp=0.7, top_p=0.9, stream=True, system_prompt=''):
    completion = client.chat.completions.create(
        model='vllm',
        messages=[
            {'role': 'system', 'content': system_prompt},
            *history,
            {'role': 'user', 'content': msg},
        ],
        temperature=temp,
        top_p=top_p,
        max_tokens=4096,
        stream=stream,
    )

    for chunk in completion:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


if __name__ == '__main__':
    for reponse in vllm_chat('介绍一下英伟达公司历史'):
        if reponse:
            print(reponse, end='')
    print('\n')