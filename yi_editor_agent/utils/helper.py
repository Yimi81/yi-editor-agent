import os
import json
import pandas as pd
from tqdm import tqdm
from yi_editor_agent.utils.config import OUTPUT_PATH

def analyze_folder_structure(root_folder, output_file):
    folder_info = {}

    # 获取所有文件和子文件夹的路径列表
    all_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            all_files.append(os.path.join(root, file))

    # 使用 tqdm 显示进度条
    for file_path in tqdm(all_files, desc="Analyzing folders"):
        folder_name = os.path.dirname(file_path)
        if folder_name not in folder_info:
            folder_info[folder_name] = {'file_types': {}}
        
        file_extension = os.path.splitext(file_path)[1]
        if file_extension in folder_info[folder_name]['file_types']:
            folder_info[folder_name]['file_types'][file_extension] += 1
        else:
            folder_info[folder_name]['file_types'][file_extension] = 1

    # 按一级目录分组
    grouped_info = {}
    for folder_path, info in folder_info.items():
        relative_path = os.path.relpath(folder_path, root_folder)
        top_level_dir = relative_path.split(os.sep)[0]
        if top_level_dir == '.':
            continue
        else:
            group_key = top_level_dir

        if group_key not in grouped_info:
            grouped_info[group_key] = []

        grouped_info[group_key].append({folder_path: info})

    # 将 grouped_info 保存为 JSON 文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(grouped_info, f, ensure_ascii=False, indent=4)

    return grouped_info



# 爬取Unity项目下所有脚本文件
def get_all_script_files_for_unity(content_path, output_csv):
    script_data = []

    # 常见资产文件后缀，按类型分类
    asset_extensions = {
        "script": [".cs", ".lua"],
    }

    # 反转字典以便快速查找文件类型
    extension_to_type = {ext: type_ for type_, exts in asset_extensions.items() for ext in exts}

    # 统计文件总数以便初始化进度条
    total_files = sum([len(files) for _, _, files in os.walk(content_path)])

    # 遍历Assets目录，找到各种资产，包括子文件夹中的文件
    with tqdm(total=total_files, desc="Processing files") as pbar:
        for root, _, files in os.walk(content_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extension_to_type:
                    asset_type = extension_to_type[ext]
                    asset_path = os.path.join(root, file)
                    asset_name = os.path.basename(asset_path)
                    # asset_id = os.path.relpath(asset_path, content_path)  # 使用相对路径作为资产ID
                    asset_path_relative = os.path.relpath(asset_path, os.path.dirname(content_path))  # 从Assets开始的路径

                    # 收集数据
                    script_data.append({
                        'Name': asset_name,
                        'Type': asset_type,
                        'Path': asset_path_relative
                    })
                pbar.update(1)  # 更新进度条

    # 将数据转换为pandas DataFrame并保存为CSV
    df = pd.DataFrame(script_data)
    df.to_csv(output_csv, index=False)

# 爬取UE项目资产文本相关信息



if __name__ == "__main__":
    # content_path = rf'F:\Unity\party_scene_yiguofeng\prototype\Assets'
    # output_csv = os.path.join(OUTPUT_PATH, 'output.csv')
    # get_all_script_files_for_unity(content_path, output_csv)
    analyze_folder_structure("D:\Party_Program_YGF\Client\Assets", "folder_info.json")