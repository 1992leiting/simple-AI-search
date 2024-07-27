import streamlit as st
from llm import vllm_chat
import requests
import bs4
import json
from langchain_community.utilities import SearxSearchWrapper
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures._base import TimeoutError


def extract_text_from_html(url: str) -> str:
    print("== extract_text_from_html: ", url)
    try:
        download = requests.get(url, timeout=10)
        soup = bs4.BeautifulSoup(download.text, "html.parser")
        text = soup.get_text()

        blocks = text.split("\n")
        result = "".join([block.strip() for block in blocks if len(block) > 20])
        return result
    except:
        return None
    


def get_searx_search_results(query: str, num_results: int = 3, categories: str = "general") -> list:
    """
    Search the web using Searx and return the results.
    """
    search = SearxSearchWrapper(searx_host="http://oracle.leiting6.cn:8080")
    results = search.results(
        query,
        num_results=num_results,
        categories=categories
    )

    return results


def merge_scrapped_data(search_results: list):
    all_content = ''
    for result in search_results:
        id = result['id']
        title = result['title']
        link = result['link']
        content = result['content']
        line = f"编号{id}标题：{title}，编号{id}链接：{link}，编号{id}内容：{content}\n"
        all_content += line
    return all_content[:5000]


def convert_to_list(input_string):
    cleaned_elements = input_string.replace('[', '').replace(']', '').replace("\"", '').replace("'", '').replace(' ', '').split(',')
    
    return cleaned_elements


def generate_search_keywords():
    # tmp
    if st.session_state['net_access'] == '不联网':
        st.session_state['loop_data']['search_keywords'] = []
        return

    loop_data = st.session_state['loop_data']
    raw_question = loop_data['raw_question']
    
    system_prompt = f"""
    你是善于进行网络搜索的小助手，负责把问题转换为联网搜索关键字。请根据问题提出最多3个搜索关键词，并以python列表的形式输出。比如：问题是“深圳有哪些好玩的地方”，可以回答：“["深圳旅游景点","深圳美食"]。
    有些需要分步骤搜索的问题，也根据每一步的需要提出多个搜索词，比如：问题是“爱因斯坦和慈禧太后谁年龄大？”，你可以回答：["爱因斯坦出生时间","慈禧太后出生时间"]。搜索关键词不限于中文，如果涉及专业名词也可以用英文关键词。
    """
    user_prompt = f"""
    问题为：{raw_question}，请根据问题提出搜索词。
    """

    full_response = ''
    response = vllm_chat(user_prompt, temp=0.1, top_p=0.9, stream=True, system_prompt=system_prompt)
    for text in response:
        full_response += text
    
    print('full_response:', full_response)

    try:
        kw = convert_to_list(full_response)
    except BaseException as e:
        kw = [full_response]
    st.session_state['loop_data']['search_keywords'] = kw

    with st.session_state.cont:
        with st.expander('搜索关键词已生成'):
            for word in kw:
                st.write(word)


def get_related_links():
    # tmp
    if st.session_state['net_access'] == '不联网':
        st.session_state['loop_data']['search_results'] = []
        return

    loop_data = st.session_state['loop_data']
    search_keywords = loop_data['search_keywords']

    results = []
    with ThreadPoolExecutor(max_workers=len(search_keywords)) as executor:
        futures = {executor.submit(get_searx_search_results, query): query for query in search_keywords}

        for future in as_completed(futures):
            try:
                content = future.result()
                results += content
            except TimeoutError:
                # print(f"抓取超时: {futures[future]['link']}")
                future.cancel()
            except Exception as e:
                # print(f"抓取出错: {futures[future]['link']}, 错误: {e}")
                future.cancel()

    # 去重，如果results中元素的link值相同则删除
    unique_results = []
    for result in results:
        link = result.get('link')
        if link:
            if link not in [result.get('link') for result in unique_results]:
                unique_results.append(result)
    st.session_state['loop_data']['search_results'] = unique_results
    
    with st.session_state.cont:
        with st.expander('搜索结果整理完成'):
            for id, result in enumerate(unique_results):
                title = result['title']
                link = result['link']
                line = f"[{id+1}. {title}]({link})\n"
                st.write(line)


def scrap_web_data():
    if st.session_state['net_access'] == '不联网':
        st.session_state['loop_data']['scrapped_data'] = []
        return

    loop_data = st.session_state['loop_data']
    results = loop_data['search_results']

    scrap_results = []
    i = 1
    with ThreadPoolExecutor(max_workers=len(results)) as executor:
        futures = {executor.submit(extract_text_from_html, result['link']): result for result in results if 'link' in result}

        for future in as_completed(futures):
            try:
                content = future.result()
                if content:
                    content = content[:2000]
                    scrap_results.append({
                        'id': i,
                        'title': futures[future]['title'],
                        'link': futures[future]['link'],
                        'content': content
                    })
                    i += 1
            except TimeoutError:
                print(f"抓取超时: {futures[future]['link']}")
                future.cancel()
            except Exception as e:
                print(f"抓取出错: {futures[future]['link']}, 错误: {e}")
                future.cancel()

    st.session_state['loop_data']['scrapped_data'] = scrap_results
    all_content = json.dumps(scrap_results, ensure_ascii=False)
    with st.session_state.cont:
        with st.expander("抓取结果整理完成"):
            st.write(all_content)


def filter_scrapped_data():
    pass


def sumarize():
    loop_data = st.session_state['loop_data']
    raw_question = loop_data['raw_question']
    scrapped_data = loop_data['scrapped_data']
    all_content = merge_scrapped_data(scrapped_data)

    if st.session_state['net_access'] == '联网':
        system_prompt = '你是一个善于回答问题的AI助手，负责根据问题和已经搜集到的信息，整理出最终答案。'
        if st.session_state['answer_style'] == '详细':
            user_prompt = f"""
            原始问题为：{raw_question}，针对这个问题，联网搜索到如下信息来源：{all_content}

            请根据以上信息整理出最终答案，注意：
            1. 请善于列举要点进行问题回答，对每一个要点进行子项展开，用树形结构来帮助理解；
            2. 每条子项的内容都在后面用markdown超链接的形式备注信息来源编号，比如子项是根据编号为3的信息输出的,编号3的链接为www.source.com，则在这条输出后面增加：[```3```](www.source.com)；记住是在每一条子项后面添加超链接，而不是在总结完成后添加，而且超链接不需要单独作为一个子项；
            3. 一定要保持使用中文，一定要避免中英文混排。
            4. 总结输出时，尽量覆盖到更多的来源，不要只根据一两条来源来做总结
            """
        else:
            user_prompt = f"""
            原始问题为：{raw_question}，针对这个问题，联网搜索到如下信息来源：{all_content}，请根据袁术问题做简要的回答，不要过多解释。
            """

    else:
        system_prompt = '你是一个善于回答问题的AI助手，请认真回答问题。'
        user_prompt = f"""
        问题为：{raw_question}
        """
        if st.session_state['answer_style'] == '详细':
            user_prompt += f"""
            请针对问题整理出最终答案，注意：善于列举要点进行问题回答，对每一个要点进行子项展开，提供的信息要尽量详细，帮助提问者更好的理解问题；"""
        else:
            user_prompt += '请针对问题作出简短的回答，不要过多解释。'

    response = vllm_chat(user_prompt, history=[], temp=0.7, top_p=0.9, stream=True, system_prompt=system_prompt)
    reponses = st.session_state.cont.write_stream(response)
    st.session_state['loop_data']['summary'] = ''.join(_ for _ in reponses)
    

def get_chat_title(question):
    prompt = f"""
    你是一个AI助手，现在需要你为用户生成一个标题，请根据用户的问题本身生成一个简短的标，不要引申，
    用户问题为：{question}
    """

    response = vllm_chat(prompt, temp=0.1, system_prompt='')
    full_response = ''.join(_ for _ in response).replace('\"', '').replace('\\', '')
    
    return full_response