import unreal

# 创建AssetRegistry以获取资产列表
asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

# 设置过滤器仅查询StaticMesh
filter = unreal.ARFilter(
    class_names=["StaticMesh"],  # 只查找StaticMesh类型
    package_paths=["/Game"],     # 选择扫描的路径
    recursive_paths=True         # 遍历子目录
)

# 获取符合条件的资产数据
assets = asset_registry.get_assets(filter)

# 遍历每个StaticMesh并获取其缩略图
for idx, asset_data in enumerate(assets):
    if idx > 100:
        break
    # 获取对象路径
    object_path = str(asset_data.package_name) + "." + str(asset_data.asset_name)
    print(object_path)
    
    # 加载StaticMesh资产
    static_mesh = unreal.EditorAssetLibrary.load_asset(object_path)
    
    # 确保资产加载成功
    if static_mesh:
        # 生成缩略图
        # unreal.ThumbnailTools.generate_thumbnail_for_object(static_mesh)
        
        # 保存缩略图
        unreal.PythonBPLib.save_thumbnail(object_path, rf"E:\Yi\yi-editor-agent\data\{asset_data.asset_name}.png")
    else:
        print(f"Failed to load asset: {object_path}")
