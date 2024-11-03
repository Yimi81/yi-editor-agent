import json
import math
import os
import pandas as pd
import requests
import streamlit as st
from datetime import datetime


BASE_URL = 'http://10.1.2.119'
PARTY_ASSETS_ANNOTATION_PATH = rf"E:\Lilith\_Party\party-web-ui\party_assets_summary_info.json"
UNITY_URL = "http://10.1.50.209:5000/navigate"

# 后端api请求
def navigate_api(path):
    print(f"navigate_api path: {path}")
    data = {'path': path}
    json_data = json.dumps(data)
    response = requests.post(UNITY_URL, headers={"Content-Type": "application/json"}, data=json_data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f'Error: {response.status_code} {response.text}')


def call_query_api(query, numbers):
    url = f'{BASE_URL}:8888/vectory_query'
    data = {'query': query, 'numbers': numbers}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f'Error: {response.status_code} {response.text}')


def call_multi_query_api(query, numbers, bbox, color):
    url = f'{BASE_URL}:8888/multimodal_vectory_query'
    data = {'query': query, 'numbers': numbers, 'bbox': bbox, 'color': color}
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f'Error: {response.status_code} {response.text}')


def load_data():
    with open(PARTY_ASSETS_ANNOTATION_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.json_normalize(data)


def search_data(data, search_term, numbers, use_multi_query, bbox, color):
    with st.spinner('正在查询...'):
        if use_multi_query:
            query_results = call_multi_query_api(search_term, numbers, bbox, color)
        else:
            query_results = call_query_api(search_term, numbers)
    ids = query_results['ids']
    filtered_data = data[data['asset_id'].astype(str).isin(ids)]
    ordered_data = pd.DataFrame()
    for id in ids:
        ordered_data = pd.concat([
            ordered_data,
            filtered_data[filtered_data['asset_id'].astype(str) == id]
        ])
    return ordered_data


def paginate_data(data, page, items_per_page):
    start = page * items_per_page
    end = start + items_per_page
    return data[start:end]


def load_images(filtered_data):

    def extract_relative_path(absolute_path):
        return os.path.join(*absolute_path.split('/')[-2:])

    filtered_data = filtered_data.copy()
    filtered_data['Image'] = filtered_data['image_files_path'].apply(
        lambda paths: (f'{BASE_URL}:8001/{extract_relative_path(paths[0])}'
                       if len(paths) > 0 else None))
    filtered_data = filtered_data[[
        'asset_id', 'Image', 'asset_name', 'asset_desc_zh', 'asset_size', 'asset_prefab_path'
    ]]
    return filtered_data


# Asset search page
def asset_search():
    st.markdown(
        """
        <div style="background-color: #fefefe; padding: 10px; border-left: 6px solid #007BFF;">
            <strong>请输入提示词搜索美术资产。</strong><br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    data = load_data()

    filtered_data = data

    numbers = st.sidebar.slider('搜索结果显示数量', 0, 1000, 50)
    # Items per page slider
    items_per_page = st.sidebar.slider('每页显示数量', 10, len(filtered_data),
                                       len(filtered_data))

    # Add a checkbox to toggle between single and multi-query API calls
    use_multi_query = st.sidebar.checkbox('使用多模态向量搜索', value=False)

    # Sidebar for bbox inputs
    length = st.sidebar.number_input('长度', value=0.0, step=0.1, format='%.2f')
    width = st.sidebar.number_input('宽度', value=0.0, step=0.1, format='%.2f')
    height = st.sidebar.number_input('高度', value=0.0, step=0.1, format='%.2f')

    # Sidebar for color input
    color = st.sidebar.text_input('颜色', value='', placeholder='输入颜色')

    # Construct bbox list
    bbox = [length, width, height] if any([length, width, height]) else None

    # Initialize or reset search_term in session state
    if 'search_term' not in st.session_state:
        st.session_state.search_term = ''


    search_term = st.text_input(
        '搜索',
        value='',
        placeholder='🔍 搜索, 多模态检索目前只支持英文输入',
        key='search',
        label_visibility='hidden',
        on_change=lambda: st.session_state.update(
            {'search_term': st.session_state.search}),
    )

    # Use the current input value for search
    current_search_term = st.session_state.get('search', '')

    if current_search_term:
        filtered_data = search_data(filtered_data, current_search_term,
                                    numbers, use_multi_query, bbox, color)

    columns_to_display = [
        'asset_id', 'asset_name', 'asset_desc_zh', 'image_files_path', 'asset_size', 'asset_prefab_path'
    ]

    filtered_data = filtered_data[columns_to_display]

    # Pagination
    total_items = len(filtered_data)
    total_pages = math.ceil(total_items / items_per_page)

    def on_select():
        selection = st.session_state.df["selection"]["rows"][0]
        print(selection)

        select_data = filtered_data.iloc[selection]
        print(select_data)
        navigate_api(select_data['asset_prefab_path'])

    if total_pages <= 0:
        st.warning('没有找到相关记录，请尝试其他搜索条件。')
    else:
        # Sidebar for page navigation
        page = (st.sidebar.number_input(
            '页码', min_value=1, max_value=total_pages, value=1, step=1) - 1)

        # Paginate data
        paginated_data = paginate_data(filtered_data, page, items_per_page)

        with st.spinner('加载资产信息中...'):
            # Load images only for the current page
            paginated_data = load_images(paginated_data)

        # Reset index to remove the default index
        paginated_data = paginated_data.reset_index(drop=True)

        # Display data using st.dataframe with column configurations
        st.dataframe(
            paginated_data,
            column_config={
                'asset_id': st.column_config.Column('ID'),
                'Image': st.column_config.ImageColumn('Image'),
                'asset_name': st.column_config.Column('资产名称'),
                'asset_size': st.column_config.Column('资产大小'),
                'asset_desc_zh': st.column_config.Column('Description'),
            },
            use_container_width=True,
            height=800,
            on_select=on_select,
            key="df",
            selection_mode="single-row",
        )

        st.sidebar.write(f'总共有 {total_pages} 页，共 {total_items} 条记录。')

        st.write(
            f'当前第 {page + 1} 页，总共有 {total_pages} 页，共 {total_items} 条记录，翻页在侧边框。'
        )


# Project preprocess page
def project_preprocess():
    st.markdown(
        """
        <div style="background-color: #fefefe; padding: 10px; border-left: 6px solid #007BFF;">
            <strong>请输入项目文件夹路径进行预处理。</strong><br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    folder_path = st.text_input('', placeholder='请输入文件夹路径...')
    
    if os.path.isdir(folder_path):
        st.success(f'找到文件夹: {folder_path}')
        if st.button('开始预处理'):
            st.write(f'正在预处理文件夹: {folder_path}')
            # 在这里添加预处理逻辑
    else:
        st.warning('输入的路径不是一个有效的文件夹，请重新输入。')


# Main page
def main():
    # 设置页面配置
    st.set_page_config(page_title='Party 场景生成相关工具集', layout='wide')
    st.markdown(
        "<h1 style='text-align: center; color: black;'>Party 场景生成相关工具集</h1>",
        unsafe_allow_html=True,
    )

    # Sidebar for navigation
    st.sidebar.title('导航')
    page = st.sidebar.selectbox('选择页面', ['项目预处理', '资产搜索'])

    if page == '项目预处理':
        project_preprocess()
    elif page == '资产搜索':
        asset_search()

if __name__ == '__main__':
    main()
