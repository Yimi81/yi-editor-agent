import argparse
import asyncio
import base64
import json
import mimetypes
import os
import logging
from logging.handlers import RotatingFileHandler

import pandas as pd
from openai import APIStatusError, AsyncAzureOpenAI, BadRequestError, AzureOpenAI
from yi_editor_agent.utils.config import LOG_PATH, OUTPUT_PATH 
from yi_editor_agent.utils.helper import analyze_folder_structure

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

FOLDER_PROMPT = """

我有一个 Unity 项目的文件夹结构，其中包含了不同的一级文件夹。每个文件夹包含不同类型的文件，我已经收集了这些文件夹下的文件类型，文件路径，文件名称和数量。请你根据这些信息，分析并描述每个一级文件夹的主要用途，并以 Markdown 格式输出结果。

以下是 {project_directory} 目录下, 一级的文件类型统计信息：

{folder_info}

请根据上述文件类型信息，考虑子文件夹路径，名称和数量，分析并描述每个一级文件夹的主要用途。

输出格式示例：

```markdown
# 项目结构分析

## Folder1
- **C# 脚本**: 10
- **图片文件**: 5
- **预制件文件**: 2

**主要用途**: 该文件夹包含大量的 C# 脚本，可能用于游戏逻辑和功能实现。同时包含一些图片文件和预制件，可能用于游戏对象和 UI 的定义。

## Folder2
- **3D 模型文件**: 3
- **材质文件**: 4
- **图片文件**: 2

**主要用途**: 该文件夹主要包含 3D 模型和材质文件，可能用于游戏中的 3D 资源和视觉效果定义。

## Folder3
- **Unity 场景文件**: 1

**主要用途**: 该文件夹包含 Unity 场景文件，可能定义了游戏中的一个或多个场景。

## Folder4
- **音频文件**: 10
- **音乐文件**: 2

**主要用途**: 该文件夹包含大量的音频文件，可能用于游戏中的音效和背景音乐。

## Folder5
- **着色器文件**: 5
- **C# 脚本**: 3

**主要用途**: 该文件夹包含着色器文件和一些 C# 脚本，可能用于定义游戏中的视觉效果和渲染逻辑。
```

---

请根据上述格式和提供的信息进行分析。
"""

api_base = "https://ai2team.openai.azure.com/"
api_key = "3d97a348a4a24119ac590d12a4751509"
deployment_name = "ai2team-gpt4o"
api_version = "2024-06-01"  # this might change in the future

# Configure logging
log_file_path = os.path.join(LOG_PATH, "image_tagging.log")
logger = logging.getLogger("ImageTaggingLogger")
logger.setLevel(logging.INFO)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler(
    log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5
)

# Create formatters and add them to the handlers
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


async def process_asset(client, image_files_path, semaphore, asset_id, asset_name):
    async with semaphore:
        logger.info(f"Processing asset {asset_id} ({asset_name})")
        image_data = []

        for img_path in image_files_path:
            with open(img_path, "rb") as image_file:
                mime_type, _ = mimetypes.guess_type(img_path)
                image = f"data:{mime_type};base64," + base64.b64encode(
                    image_file.read()
                ).decode("utf-8")
                image_data.append(image)

        if len(image_data) == 1:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data[0]}},
                        {
                            "type": "text",
                            "text": IMAGE_MAT_PROMPT,
                        },
                    ],
                },
            ]
        else:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data[0]}},
                        {"type": "image_url", "image_url": {"url": image_data[1]}},
                        {
                            "type": "text",
                            "text": IMAGE_ASSET_PROMPT,
                        },
                    ],
                },
            ]

        try:
            response = await client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )

            if response:
                description = response.choices[0].message.content
                result = {asset_id: json.loads(description)}
                logger.info(f"Successfully processed asset {asset_id} ({asset_name})")
                return result

        except (BadRequestError, APIStatusError) as e:
            logger.error(
                f"Skipping asset {asset_id} ({asset_name}) due to content filter violation: {e}"
            )
            return {asset_id: None}


async def tag_assets_images(data_path, output_path):
    client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        base_url=f"{api_base}/openai/deployments/{deployment_name}",
    )

    semaphore = asyncio.Semaphore(50)  # Adjust the number to control concurrency
    tasks = []

    # 读取json文件
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    asset_infos = data.get("AssetInfos", [])
    logger.info(
        f"Loaded {len(asset_infos)} prefab assets and {len(asset_infos)} material assets from {data_path}"
    )

    for asset in asset_infos:
        asset_id = asset["Path"]
        asset_name = asset["Name"]
        image_files_path = asset["ThumbnailPaths"]
        tasks.append(
            process_asset(client, image_files_path, semaphore, asset_id, asset_name)
        )

    results = await asyncio.gather(*tasks)

    # Prepare the data for saving
    output_data = []
    for asset in asset_infos:
        asset_id = asset["Path"]
        description = next(
            (result[asset_id] for result in results if result.get(asset_id)), None
        )
        if description:
            output_data.append(
                {
                    "Path": asset["Path"],
                    "Name": asset["Name"],
                    "Type": asset["Type"],
                    "Description": description["asset_desc"],
                }
            )

    # Save the updated data to a CSV file using pandas
    df = pd.DataFrame(output_data)
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Successfully saved updated data to {output_path}")


def tag_project_folder_info(root_folder, folder_info):
    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        base_url=f"{api_base}/openai/deployments/{deployment_name}",
    )

    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": FOLDER_PROMPT.format(
                    project_directory=root_folder, folder_info=folder_info
                ),
            },
        ]
        response = client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            max_tokens=4096,
        )

        if response:
            description = response.choices[0].message.content
            logger.info(f"Successfully get folder info for {root_folder}")
            return description

    except (BadRequestError, APIStatusError) as e:
        logger.error(e)
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automatically batch label images.")
    parser.add_argument(
        "--data_path",
        default="E:\\Yi\\yi-editor-agent\\data\\AllAssetInfo.json",
        help="The path to the input JSON file",
    )
    parser.add_argument(
        "--output_path",
        default="E:\\Yi\\yi-editor-agent\\output\\output.csv",
        help="The path to save the output CSV file",
    )
    parser.add_argument(
        "--folder_info_path",
        default="E:\\Yi\\yi-editor-agent\\output\\folder_info.md",
        help="The path to save the folder info markdown file",
    )
    parser.add_argument(
        "--root_folder",
        default=rf"D:\Party_Program_YGF\Client\Assets",
        help="The root folder of the Unity project",
    )

    args = parser.parse_args()

    # asyncio.run(tag_assets_images(args.data_path, args.output_path))

    folder_info = analyze_folder_structure(args.root_folder)

    folder_description = tag_project_folder_info(args.root_folder, folder_info)

    if folder_description:
        with open(args.folder_info_path, "w", encoding="utf-8") as f:
            f.write(folder_description)
        logger.info(f"Successfully saved folder info to {args.folder_info_path}")
