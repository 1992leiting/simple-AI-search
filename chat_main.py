import streamlit as st
from common import *
from functions import *
import os
from uuid import uuid4


# session数据结构:
#
# └ chat_title  # 本次对话的标题
# └ net_access  # 是否联网
# └ answer_style  # 回答风格
# └ loop_data  # 当前loop的数据
#   └ raw_question  # 用户输入的问题
#   └ search_keywords  # 搜索关键词
#   └ search_results  # 搜索结果
#   └ scrapped_data  # 抓取到的数据
#   └ summary  # 回答
# └ record  # 所有对话记录（从文件加载）
# └ uuid  # 当前session的uuid


# 页面加载流程:
#
# - 打印网页标题
# - 加载record
# - 打印AI提示语
# - 加载和打印history
# - 输入框


# 搜索阶段所有的process
process_list = [
    {'name': 'Generating search keywords...', 'func': generate_search_keywords},
    {'name': 'Getting related links...', 'func': get_related_links},
    {'name': 'Scrapping web data...', 'func': scrap_web_data},
    {'name': 'Filtering scrapped data...', 'func': filter_scrapped_data},
    {'name': 'Summarizing...', 'func': sumarize},
    {'name': 'Done', 'func': None},
]


def open_record(uuid):
    for record in st.session_state['record']:
        if record['uuid'] == uuid:
            print('load record: uuid')
            # st.session_state['loop_data'] = record['loop_data']
            st.session_state['history'] = record['history']
            st.session_state['chat_title'] = record['chat_title']
            st.session_state['uuid'] = record['uuid']

def start_search():
    # 创建一个chat_message用于输出
    chat_message = st.chat_message("ai")
    st.session_state.cont = chat_message  # 输出内容所在的位置

    # 当前loop的进度条
    with chat_message:
        progress_bar = st.progress(0)
    for i, process in enumerate(process_list):
        process_value = (i + 1)/len(process_list)
        progress_bar.progress(process_value, text=process['name'])
        if process['func']:
            process['func']()
    st.session_state['loop_data']['finished'] = True

    # ------search完成

    # 保存history
    st.session_state['history'].append(st.session_state['loop_data'].copy())

    # 设置chat title
    if not st.session_state['chat_title']:
        st.session_state['chat_title'] = get_chat_title(st.session_state['loop_data']['raw_question'])
    
    # 保存record
    cur_record = {
        # 'loop_data': st.session_state['loop_data'],
        'history': st.session_state['history'],
        'chat_title': st.session_state['chat_title'],
        'uuid': st.session_state['uuid'],
    }
    replace = False
    for i, record in enumerate(st.session_state['record']):
        if record['uuid'] == st.session_state['uuid']:
            st.session_state['record'][i] = cur_record
            replace = True
    if not replace:
        st.session_state['record'].append(cur_record)
    with open(record_file, 'w') as f:
        json.dump(st.session_state['record'], f, indent=4, ensure_ascii=False)


# --------主程序从这里开始
st.set_page_config(page_title="AI Search", layout='centered' if st.session_state.get('is_pc') else 'wide')

# 判断是否是PC界面而自动设置wide或者centered布局，TODO：偶尔会引起界面重载，需修复或者直接屏蔽
if not st.session_state.get('is_pc'):
    from streamlit_js_eval import streamlit_js_eval
    screen_width = streamlit_js_eval(js_expressions='screen.width', key='SCR')
    if screen_width:
        st.session_state['is_pc'] = screen_width > 1000
        if st.session_state['is_pc']:
            st.rerun()

if not st.session_state.get('chat_title'):
    # st.toast('开始搜索')
    st.session_state['chat_title'] = ''

st.title('AI Search')
st.logo('/edisk/projects/ai_search_web/AI.png')

# --------加载record
# 没有文件则创建
record_file = os.path.join('record', 'data.json')
if not os.path.exists(record_file):
    with open(record_file, 'w') as f:
        json.dump([], f)
# 加载到session.record
with open(record_file, 'r') as f:
    st.session_state['record'] = json.load(f)
# 设置sidebar
with st.sidebar:
    # 增加一个新建对话的额外按钮
    if st.button('新建对话', use_container_width=True, type='primary'):
        st.session_state.clear()
        with open(record_file, 'r') as f:
            st.session_state['record'] = json.load(f)
    for record in list(reversed(st.session_state['record'])):
        st.button(record['chat_title'], use_container_width=True, key=str(uuid4()), on_click=open_record, args=[record['uuid']])


# --------初始化session.loop_data/history
# 如果是新session则为空
if not st.session_state.get('loop_data'):
    st.session_state['loop_data'] = LOOP_DATA.copy()
if not st.session_state.get('history'):
    st.session_state['history'] = []
if not st.session_state.get('uuid'):
    st.session_state['uuid'] = str(uuid4())

with st.chat_message(name='ai'):
    st.write('有什么可以帮你的吗？')

# --------加载history
if st.session_state['history']:
    for history in st.session_state['history']:
        with st.chat_message(name='user'):
            st.write(history['raw_question'])

        with st.chat_message(name='ai'):
            if history['search_keywords']:
                with st.expander('搜索关键词已生成'):
                    st.write(history['search_keywords'])
            if history['search_results']:
                with st.expander('搜索结果整理完成'):
                    for id, result in enumerate(history['search_results']):
                        title = result['title']
                        link = result['link']
                        line = f"[{id+1}. {title}]({link})\n"
                        st.write(line)
            if history['scrapped_data']:
                with st.expander('抓取结果整理完成'):
                    st.write(history['scrapped_data'])
            st.write(history['summary'])

# 输入框
col1, col2, col3 = st.columns([2, 2, 6])
with col1:
    st.session_state['net_access'] = st.selectbox('是否联网', options=['联网', '不联网'], label_visibility='collapsed')
with col2:
    st.session_state['answer_style'] = st.selectbox('回答风格', options=['简洁', '详细'], label_visibility='collapsed')


chat_input = st.chat_input(placeholder='提问...')
if chat_input:
    with st.chat_message(name='user'):
        st.write(chat_input)
    st.session_state['loop_data']['raw_question'] = chat_input
    start_search()
    st.rerun()


