import argparse
import asyncio
import base64
import json
import mimetypes
import os
import logging
from logging.handlers import RotatingFileHandler

from openai import APIStatusError, AsyncAzureOpenAI, BadRequestError
from yi_editor_agent.utils.config import LOG_PATH  # 导入 LOG_PATH


IMAGE_ASSET_PROMPT = """
您是一名专业的标签编写员，专门根据图片创建准确的自然语言描述标签。您将根据提供的正视图、侧视图进行标注。请结合上述三种视图生成更详细和准确的标签。您的回应应仅通过生成包含以下内容的JSON文件：

简短自然语言描述：结合颜色、材质、风格、氛围、大小、形状、用途和场景生成简短描述，格式如下：
一[量词][具体用途或特性][具体物品类型]，主要颜色为[主色]，[描述其他颜色特征]，[主要材质]材质，[大小特征]，[形状特征]，适合[用途]，适用于[场景]，营造出[氛围]氛围，[风格]风格。

请避免对具体物品进行模糊描述, 如“床”、“植物”、“车”或“杯子”，而是要提供更详细的描述，如“双人床”、“多肉植物”、“卡车”或“酒杯”。

注意：
如果图片中没有物体，请返回“无效数据”。

请按以下格式返回信息：
{{
"asset_desc": "[简短自然语言描述]"
}}

示例输出：
{{
"asset_desc": "一张双人床，主要颜色为白色，床头和床架为浅木色，木质材质，中等大小，方形床头和简约直线设计，适合休息，适用于卧室，营造出宁静和舒适的氛围，斯堪的纳维亚风格。"
}}
"""

IMAGE_MAT_PROMPT = """
您是一名专业的标签编写员，专门根据Unity中材质球的缩略图图片创建准确的自然语言描述标签。您将根据提供的图片进行标注。您的回应应仅通过生成包含以下内容的JSON文件：

简短自然语言描述，描述该材质球的颜色，适合用于哪些物品。尤其如果该材质球的色彩适合用于室内的墙壁和地板(如卧室、客厅、厨房、卫生间、书房等)，请在描述中提及。格式如下：

{{
"asset_desc": "[简短自然语言描述，中文]"
}}

示例输出：
{{
"asset_desc": "一种带有光泽的蓝色和深棕色材质，具有分段的布料质感。适合用于衣物如连帽衫或夹克，呈现柔软的布料外观，不适合用于墙壁或地板。"
}}

注意：
如果图片中没有物体，请返回“无效数据”。
"""


api_base = 'https://ai2team.openai.azure.com/'
api_key = '3d97a348a4a24119ac590d12a4751509'
deployment_name = 'ai2team-gpt4o'
api_version = '2024-06-01'  # this might change in the future

# Configure logging
log_file_path = os.path.join(LOG_PATH, 'image_tagging.log')
logger = logging.getLogger('ImageTaggingLogger')
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)

# Create formatters and add them to the handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

async def process_asset(client, image_files_path, semaphore, asset_id, asset_name, asset_type):
    async with semaphore:
        logger.info(f'Processing asset {asset_id} ({asset_name})')
        image_data = []

        if asset_type == "mat" and isinstance(image_files_path, str):
            with open(image_files_path, 'rb') as image_file:
                mime_type, _ = mimetypes.guess_type(image_files_path)
                image = f'data:{mime_type};base64,' + base64.b64encode(
                    image_file.read()).decode('utf-8')
                image_data.append(image)
            
                messages = [
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant.'
                },
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': image_data[0]
                            }
                        },
                        {
                            'type': 'text',
                            'text': IMAGE_MAT_PROMPT,
                        },
                    ],
                },
            ]
        else:
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
                    'role': 'user',
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
                            'type': 'text',
                            'text': IMAGE_ASSET_PROMPT,
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

            if response:
                description = response.choices[0].message.content
                result = {asset_id: json.loads(description)}
                logger.info(f'Successfully processed asset {asset_id} ({asset_name})')
                return result

        except (BadRequestError, APIStatusError) as e:
            logger.error(f'Skipping asset {asset_id} ({asset_name}) due to content filter violation: {e}')
            return {asset_id: None}


async def tag_assets_images(data_path, output_path):
    client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        base_url=f'{api_base}/openai/deployments/{deployment_name}',
    )

    semaphore = asyncio.Semaphore(50)  # Adjust the number to control concurrency
    tasks = []

    # 读取json文件
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    prefab_infos = data.get('PrefabInfos', [])
    material_infos = data.get('MaterialInfos', [])
    logger.info(f'Loaded {len(prefab_infos)} prefab assets and {len(material_infos)} material assets from {data_path}')

    for asset in prefab_infos:
        asset_id = asset['Path']
        asset_name = asset['Name']
        image_files_path = asset['ThumbnailPaths']
        tasks.append(
            process_asset(
                client,
                image_files_path,
                semaphore,
                asset_id,
                asset_name,
                "prefab"
            )
        )

    for asset in material_infos:
        asset_id = asset['Path']
        asset_name = asset['Name']
        image_file_path = asset['ThumbnailPath']
        tasks.append(
            process_asset(
                client,
                image_file_path,
                semaphore,
                asset_id,
                asset_name,
                "mat"
            )
        )

    results = await asyncio.gather(*tasks)

    # Save the descriptions back into the original data structure
    for asset in prefab_infos:
        asset_id = asset['Path']
        description = next((result[asset_id] for result in results if result.get(asset_id)), None)
        if description:
            asset['Description'] = description

    for asset in material_infos:
        asset_id = asset['Path']
        description = next((result[asset_id] for result in results if result.get(asset_id)), None)
        if description:
            asset['Description'] = description["asset_desc"]

    # Save the updated data back to a JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info(f'Successfully saved updated data to {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automatically batch label images.')
    parser.add_argument(
        '--data_path',
        default='E:\Yi\yi-editor-agent\data\AllAssetInfo.json',
        help='The path to the input JSON file',
    )
    parser.add_argument(
        '--output_path',
        default='E:\Yi\yi-editor-agent\output.json',
        help='The path to save the output JSON file',
    )
    args = parser.parse_args()

    asyncio.run(tag_assets_images(args.data_path, args.output_path))
