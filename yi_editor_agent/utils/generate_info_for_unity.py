import os
import pandas as pd

def main(content_path, output_csv):
    asset_data = []

    # 常见资产文件后缀，按类型分类
    asset_extensions = {
        "scene": [".unity"],
        "prefab": [".prefab"],
        "material": [".mat"],
        #"shader": [".shader", ".cginc"],
        #"script": [".cs", ".js", ".boo"],
        "texture": [".png", ".jpg", ".jpeg", ".tga", ".bmp", ".gif", ".psd", ".tif", ".tiff"],
        #"model": [".fbx", ".obj", ".dae", ".3ds", ".dxf"],
        #"audio": [".wav", ".mp3", ".ogg", ".aiff", ".aif"],
        #"video": [".mp4", ".mov", ".avi"],
        "animation": [".anim", ".controller"],
        #"font": [".ttf", ".otf", ".fnt"],
        #"scriptable_object": [".asset"],
        #"gui_skin": [".guiskin"],
        #"physics_material": [".physicmaterial", ".physicsmaterial2d"],
        #"config": [".json", ".xml"],
        #"dll": [".dll"],
        #"text": [".txt", ".csv"]
    }

    # 反转字典以便快速查找文件类型
    extension_to_type = {ext: type_ for type_, exts in asset_extensions.items() for ext in exts}

    # 遍历Assets目录，找到各种资产，包括子文件夹中的文件
    for root, _, files in os.walk(content_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extension_to_type:
                asset_type = extension_to_type[ext]
                asset_path = os.path.join(root, file)
                asset_name = os.path.basename(asset_path)
                asset_id = os.path.relpath(asset_path, content_path)  # 使用相对路径作为资产ID
                asset_path_relative = os.path.relpath(asset_path, os.path.dirname(content_path))  # 从Assets开始的路径

                # 收集数据
                asset_data.append({
                    'asset_id': asset_id,
                    'asset_name': asset_name,
                    'asset_type': asset_type,
                    'asset_path': asset_path_relative
                })


    # 将数据转换为pandas DataFrame并保存为CSV
    df = pd.DataFrame(asset_data)
    df.to_csv(output_csv, index=False)

if __name__ == "__main__":
    content_path = '/Users/lilithgames/markyi/ai2thor/unity/Assets'
    output_csv = 'output.csv'
    main(content_path, output_csv)
