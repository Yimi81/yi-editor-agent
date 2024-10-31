import os
import glob

def delete_meta_files(folder_path):
    # 构建文件路径模式
    file_pattern = os.path.join(folder_path, "*.meta")
    
    # 获取所有匹配的文件
    meta_files = glob.glob(file_pattern)
    
    # 删除所有匹配的文件
    for file_path in meta_files:
        try:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

# 示例用法
folder_path = rf"E:\Lilith\_Party\Screenshots_V15"  # 替换成你的文件夹路径
delete_meta_files(folder_path)
