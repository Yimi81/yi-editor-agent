import os
import unreal
import pandas as pd

# 假设你有一个函数generate_description_from_images来生成描述
def generate_description_from_images(images):
    # Placeholder: 这里调用多模态LLM生成描述
    return "Generated description"

def capture_views(asset):
    # Captures front, side, and top views of the asset
    # Placeholder: 需要使用UE5的API实现截图功能
    front_view = f"{asset.get_name()}_front.png"
    side_view = f"{asset.get_name()}_side.png"
    top_view = f"{asset.get_name()}_top.png"
    return [front_view, side_view, top_view]

def main(content_path, output_csv):
    asset_data = []

    # 遍历content目录，找到StaticMesh和SkeletalMesh资产
    for root, dirs, files in os.walk(content_path):
        for file in files:
            if file.endswith('.uasset'):
                asset_path = os.path.join(root, file)
                asset = unreal.EditorAssetLibrary.load_asset(asset_path)
                
                if isinstance(asset, unreal.StaticMesh) or isinstance(asset, unreal.SkeletalMesh):
                    asset_id = asset.get_path_name()
                    asset_name = asset.get_name()
                    asset_type = "StaticMesh" if isinstance(asset, unreal.StaticMesh) else "SkeletalMesh"
                    asset_path = asset.get_path_name()
                    
                    # 截取三视图
                    images = capture_views(asset)
                    
                    # 生成描述
                    asset_description = generate_description_from_images(images)
                    
                    # 收集数据
                    asset_data.append({
                        'asset_id': asset_id,
                        'asset_name': asset_name,
                        'asset_type': asset_type,
                        'asset_description': asset_description,
                        'asset_thumbnail': images[0],  # 示例中使用front_view作为缩略图
                        'asset_path': asset_path
                    })

    # 将数据转换为pandas DataFrame并保存为CSV
    df = pd.DataFrame(asset_data)
    df.to_csv(output_csv, index=False)

if __name__ == "__main__":
    content_path = '/Users/lilithgames/markyi/UGit/AssetManageAgent/Content'
    output_csv = 'output.csv'
    main(content_path, output_csv)
