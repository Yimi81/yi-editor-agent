"""
Author: Guofeng Yi
Date: 2024-08-19
LastEditors: Yimi81
LastEditTime: 2024-08-26
FilePath: /lilith-agents/lilith_agents/memory/tag_async.py
Description: 对Party美术资产进行打标
Copyright (c) 2024 by Lilith Games R&D Platform Algorithm Team, All Rights Reserved.
"""

import argparse
import asyncio
import base64
import json
import mimetypes
import os

import pandas as pd
from openai import APIStatusError, AsyncAzureOpenAI, BadRequestError


ASSET_ANNOTATION_PROMPT = """
您是一名专业的标签编写员，专门根据图片创建准确的自然语言描述标签。您将根据提供的侧视图、正视图和俯视图进行标注。请结合上述三种视图生成更详细和准确的标签。您的回应应仅通过生成包含以下内容的JSON文件：

简短自然语言描述：结合颜色、材质、风格、氛围、大小、形状、用途和场景生成简短描述，格式如下：
一[量词][具体用途或特性][具体物品类型]，主要颜色为[主色]，[描述其他颜色特征]，[主要材质]材质，[大小特征]，[形状特征]，适合[用途]，适用于[场景]，营造出[氛围]氛围，[风格]风格。

请避免对具体物品如“床”、“植物”、“车”或“杯子”进行模糊描述，而是要提供更详细的描述，如“双人床”、“多肉植物”、“卡车”或“酒杯”。

您可以提供更合适的风格和氛围描述。

请按以下格式返回信息：
{{
"asset_desc": "[简短自然语言描述]"
}}

示例输出：
{{
"asset_desc": "一张双人床，主要颜色为白色，床头和床架为浅木色，木质材质，中等大小，方形床头和简约直线设计，适合休息，适用于卧室，营造出宁静和舒适的氛围，斯堪的纳维亚风格。"
}}
"""


api_base = 'https://ai2team.openai.azure.com/'
api_key = '3d97a348a4a24119ac590d12a4751509'
deployment_name = 'ai2team-gpt4o'
api_version = '2024-06-01'  # this might change in the future


def count_subfolders(directory):
    items = os.listdir(directory)
    subfolders = [
        item for item in items if os.path.isdir(os.path.join(directory, item))
    ]
    return len(subfolders)


def get_subfolder_names(directory_path):
    """获取指定目录下的一级子文件夹名称列表.

    :param directory_path: 目录路径
    :return: 一级子文件夹名称列表
    """
    return [
        name for name in os.listdir(directory_path)
        if os.path.isdir(os.path.join(directory_path, name))
    ]


def find_missing_resources(directory_path, table_path):
    """找出资产表格中没有出现在图片文件夹一级子文件夹名称列表中的资源id.

    :param directory_path: 图片文件夹路径
    :param table_path: 资产表格路径
    :return: 没有对应图片文件夹的资源id列表
    """
    subfolder_names = get_subfolder_names(directory_path)
    table = pd.read_csv(table_path)

    missing_resources = []
    for resource_id in table['资源ID']:
        resource_subfolder = resource_id.split('/')[-1]
        if resource_subfolder not in subfolder_names:
            missing_resources.append(resource_id)

    return missing_resources


def get_existing_resource_info(directory_path, table_path):
    """遍历表格，如果资源ID不在missing_resources里，则遍历directory_path，
    根据资源ID的最后一个/后的字符串找到对应的图片子文件夹，返回资源id，资源名称以及对应的图片文件夹路径列表.

    :param directory_path: 图片文件夹路径
    :param table_path: 资产表格路径
    :return: 资源id，资源名称及图片文件夹路径的列表
    """
    subfolder_names = get_subfolder_names(directory_path)
    table = pd.read_csv(table_path)
    missing_resources = find_missing_resources(directory_path, table_path)

    existing_resource_info = []

    for index, row in table.iterrows():
        resource_id = row['资源ID']
        resource_name = row['资源名称']
        resource_subfolder = resource_id.split('/')[-1]

        if resource_subfolder not in missing_resources:
            subfolder_path = os.path.join(directory_path, resource_subfolder)
            if os.path.exists(subfolder_path):
                image_files_path = []
                for root, dirs, files in os.walk(subfolder_path):
                    for file in files:
                        image_files_path.append(os.path.join(root, file))

                existing_resource_info.append({
                    'asset_id':
                    resource_id,
                    'asset_name':
                    resource_name,
                    'image_folder_path':
                    subfolder_path,
                    'image_files_path':
                    image_files_path,
                })

    return existing_resource_info


async def process_asset_2(client, image_files_path, semaphore, asset_id,
                          asset_name, asset_info):
    async with semaphore:
        image_data = []
        for img_path in image_files_path:
            with open(img_path, 'rb') as image_file:
                mime_type, _ = mimetypes.guess_type(img_path)
                image = f'data:{mime_type};base64,' + base64.b64encode(
                    image_file.read()).decode('utf-8')
                image_data.append(image)

        messages = [
            {
                'role': 'system',
                'content': 'You are a helpful assistant.'
            },
            {
                'role':
                'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[0]
                        }
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[1]
                        }
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[2]
                        }
                    },
                    {
                        'type':
                        'text',
                        'text': (prompt_with_raw.format(asset_info=asset_info)
                                 if asset_name != '未打标签' else prompt),
                    },
                ],
            },
        ]

        try:
            response = await client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                max_tokens=4000,
                response_format={'type': 'json_object'},
            )

            print(response)
            if response:
                description = response.choices[0].message.content
                print(description)

            result = {asset_id: json.loads(description)}
            return result

        except (BadRequestError, APIStatusError) as e:
            print(
                f'Skipping asset {asset_id} due to content filter violation: {e}'
            )
            return {asset_id: None}


async def process_asset(client, image_files_path, semaphore, asset_id,
                        asset_name):
    async with semaphore:
        image_data = []
        for img_path in image_files_path:
            with open(img_path, 'rb') as image_file:
                mime_type, _ = mimetypes.guess_type(img_path)
                image = f'data:{mime_type};base64,' + base64.b64encode(
                    image_file.read()).decode('utf-8')
                image_data.append(image)

        messages = [
            {
                'role': 'system',
                'content': 'You are a helpful assistant.'
            },
            {
                'role':
                'user',
                'content': [
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[0]
                        }
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[1]
                        }
                    },
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': image_data[2]
                        }
                    },
                    {
                        'type':
                        'text',
                        'text': (ASSET_ANNOTATION_PROMPT.format(
                            asset_name=asset_name) if asset_name != '未打标签' else
                                 ASSET_ANNOTATION_PROMPT_NO_ASSET_NAME),
                    },
                ],
            },
        ]

        try:
            response = await client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                max_tokens=4000,
                response_format={'type': 'json_object'},
            )

            print(response)
            if response:
                description = response.choices[0].message.content
                print(description)

            result = {asset_id: json.loads(description)}
            return result

        except (BadRequestError, APIStatusError) as e:
            print(
                f'Skipping asset {asset_id} due to content filter violation: {e}'
            )
            return {asset_id: None}


async def main():
    parser = argparse.ArgumentParser(
        description='Automatically batch label images.')
    parser.add_argument(
        '--directory_path',
        default='/data/markyi/Party/Al_NeedsTextures',
        help='资产图片文件夹',
    )
    parser.add_argument(
        '--table_path',
        default=
        '/home/markyi/lilith/lilith-agents/lilith_agents/memory/ResourceIndexLibrary.csv',
        help='资产表格文件',
    )
    parser.add_argument(
        '--output_path',
        default=
        '/home/markyi/lilith/lilith-agents/lilith_agents/memory/output_zh_v3.json',
        help='The path to save the output JSON file',
    )
    args = parser.parse_args()

    client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        base_url=f'{api_base}/openai/deployments/{deployment_name}',
    )

    existing_resource_info = get_existing_resource_info(
        args.directory_path, args.table_path)

    semaphore = asyncio.Semaphore(
        50)  # Adjust the number to control concurrency
    tasks = []

    df = pd.read_csv(args.table_path)

    for resource in existing_resource_info:
        # 读取df中id为asset_id的行
        info = df[df['资源ID'] == resource['asset_id']].iloc[0]
        asset_name = info['资源名称']
        asset_desc = info['资源描述']
        asset_info = f'物体名称：{asset_name}; 物体描述：{asset_desc}'
        # print(asset_info)
        tasks.append(
            process_asset_2(
                client,
                resource['image_files_path'],
                semaphore,
                resource['asset_id'],
                resource['asset_name'],
                asset_info,
            ))

    results = await asyncio.gather(*tasks)

    # Save the results to a JSON file
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    asyncio.run(main())
