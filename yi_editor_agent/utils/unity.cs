using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using System.IO;
using System;
using Unity.EditorCoroutines.Editor;
using System.Threading;
using UnityEditor.SceneManagement;

public class AssetInfoCollector : MonoBehaviour
{
    [MenuItem("Tools/Collect All Asset Info")]
    public static void CollectAllAssetInfoMenu()
    {
        CollectAllAssetInfo("Assets/CollectedInfo", "Assets/Prefabs", "Assets/Materials", result => {
            Debug.Log("All asset info collection completed: " + result);
        });
    }

    [MenuItem("Tools/Collect Prefab Info")]
    public static void CollectPrefabInfoMenu()
    {
        CollectPrefabInfo("Assets/PrefabInfo", null, result => {
            Debug.Log("Prefab info collection completed: " + result);
        });
    }

    [MenuItem("Tools/Collect Material Info")]
    public static void CollectMaterialInfoMenu()
    {
        CollectMaterialInfo("Assets/MaterialInfo", null, result => {
            Debug.Log("Material info collection completed: " + result);
        });
    }

    public static void CollectAllAssetInfo(string saveDir, string prefabSearchDir, string materialSearchDir, Action<bool> onComplete)
    {
        Debug.Log($"CollectAllAssetInfo started, saveDir: {saveDir}, prefabSearchDir: {prefabSearchDir}, materialSearchDir: {materialSearchDir}");

        List<AssetInfo> assetInfos = new List<AssetInfo>();

        CollectPrefabInfo(saveDir, prefabSearchDir, assetInfos, prefabResult => {
            if (prefabResult)
            {
                CollectMaterialInfo(saveDir, materialSearchDir, assetInfos, materialResult => {
                    if (materialResult)
                    {
                        SaveAllAssetInfos(assetInfos, saveDir);
                        onComplete(true);
                    }
                    else
                    {
                        onComplete(false);
                    }
                });
            }
            else
            {
                onComplete(false);
            }
        });
    }

    public static void CollectPrefabInfo(string saveDir, string searchDir, Action<bool> onComplete)
    {
        List<AssetInfo> assetInfos = new List<AssetInfo>();
        CollectPrefabInfo(saveDir, searchDir, assetInfos, onComplete);
    }

    public static void CollectPrefabInfo(string saveDir, string searchDir, List<AssetInfo> assetInfos, Action<bool> onComplete)
    {
        Debug.Log($"CollectPrefabInfo started, saveDir: {saveDir}, searchDir: {searchDir}");

        string[] allPrefabGuids = string.IsNullOrEmpty(searchDir) ?
            AssetDatabase.FindAssets("t:Prefab") :
            AssetDatabase.FindAssets("t:Prefab", new[] { searchDir });

        // Limit to the first 1000 prefabs for testing
        int limit = Mathf.Min(allPrefabGuids.Length, 1000);
        string[] limitedPrefabGuids = new string[limit];
        Array.Copy(allPrefabGuids, limitedPrefabGuids, limit);

        if (!Directory.Exists(saveDir))
        {
            Directory.CreateDirectory(saveDir);
            Debug.Log($"Created directory: {saveDir}");
        }

        Debug.Log($"limitedPrefabGuids length: {limitedPrefabGuids.Length}");

        CountdownEvent countdown = new CountdownEvent(limitedPrefabGuids.Length);

        foreach (string guid in limitedPrefabGuids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);

            if (prefab != null)
            {
                Debug.Log($"Processing prefab: {prefab.name}");

                if (IsStaticMesh(prefab) || IsSkinnedMesh(prefab))
                {
                    AssetInfo assetInfo = new AssetInfo
                    {
                        Name = prefab.name,
                        Path = assetPath,
                        Type = GetPrefabType(prefab),
                        ThumbnailPaths = new List<string>()
                    };

                    // Start the coroutine to generate the thumbnails
                    Debug.Log($"Starting thumbnail generation for: {prefab.name}");
                    EditorCoroutineUtility.StartCoroutineOwnerless(GenerateThumbnailsCoroutine(prefab, prefab.name, saveDir, (thumbnailPaths) =>
                    {
                        if (thumbnailPaths != null && thumbnailPaths.Count == 2) // Ensure both thumbnails are generated
                        {
                            assetInfo.ThumbnailPaths = thumbnailPaths;
                            assetInfos.Add(assetInfo);
                            Debug.Log($"Thumbnail generation completed for: {prefab.name}");
                        }
                        else
                        {
                            Debug.Log($"Thumbnail generation failed for: {prefab.name}");
                        }

                        countdown.Signal();
                    }));
                }
                else
                {
                    Debug.Log($"Prefab {prefab.name} does not have suitable components for thumbnail generation.");
                    countdown.Signal();
                }
            }
            else
            {
                Debug.Log($"Failed to load prefab at path: {assetPath}");
                countdown.Signal();
            }
        }

        EditorCoroutineUtility.StartCoroutineOwnerless(WaitForCompletion(countdown, onComplete));
    }

    public static void CollectMaterialInfo(string saveDir, string searchDir, Action<bool> onComplete)
    {
        List<AssetInfo> assetInfos = new List<AssetInfo>();
        CollectMaterialInfo(saveDir, searchDir, assetInfos, onComplete);
    }

    public static void CollectMaterialInfo(string saveDir, string searchDir, List<AssetInfo> assetInfos, Action<bool> onComplete)
    {
        Debug.Log($"CollectMaterialInfo started, saveDir: {saveDir}, searchDir: {searchDir}");

        string[] allMaterialGuids = string.IsNullOrEmpty(searchDir) ?
            AssetDatabase.FindAssets("t:Material") :
            AssetDatabase.FindAssets("t:Material", new[] { searchDir });

        // Filter out only .mat files
        List<string> materialGuids = new List<string>();
        foreach (string guid in allMaterialGuids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            if (assetPath.EndsWith(".mat", StringComparison.OrdinalIgnoreCase))
            {
                materialGuids.Add(guid);
            }
        }

        int limit = Mathf.Min(materialGuids.Count, 1000);
        string[] limitedMaterialGuids = new string[limit];
        materialGuids.CopyTo(0, limitedMaterialGuids, 0, limit);

        if (!Directory.Exists(saveDir))
        {
            Directory.CreateDirectory(saveDir);
            Debug.Log($"Created directory: {saveDir}");
        }

        Debug.Log($"limitedMaterialGuids length: {limitedMaterialGuids.Length}");

        CountdownEvent countdown = new CountdownEvent(limitedMaterialGuids.Length);

        foreach (string guid in limitedMaterialGuids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);

            if (material != null)
            {
                Debug.Log($"Processing material: {material.name}");

                AssetInfo assetInfo = new AssetInfo
                {
                    Name = material.name,
                    Path = assetPath,
                    Type = "Material",
                    ThumbnailPaths = new List<string>()
                };

                // Start the coroutine to get the thumbnail
                Debug.Log($"Starting thumbnail retrieval for: {material.name}");
                EditorCoroutineUtility.StartCoroutineOwnerless(GenerateMaterialThumbnailCoroutine(material, material.name, saveDir, (thumbnailPath) =>
                {
                    if (!string.IsNullOrEmpty(thumbnailPath))
                    {
                        assetInfo.ThumbnailPaths.Add(thumbnailPath);
                        assetInfos.Add(assetInfo);
                        Debug.Log($"Thumbnail retrieval completed for: {material.name}");
                    }
                    else
                    {
                        Debug.Log($"Thumbnail retrieval failed for: {material.name}");
                    }

                    countdown.Signal();
                }));
            }
            else
            {
                Debug.Log($"Failed to load material at path: {assetPath}");
                countdown.Signal();
            }
        }

        EditorCoroutineUtility.StartCoroutineOwnerless(WaitForCompletion(countdown, onComplete));
    }

    private static IEnumerator WaitForCompletion(CountdownEvent countdown, Action<bool> onComplete)
    {
        while (countdown.CurrentCount > 0)
        {
            yield return null;
        }
        onComplete(true);
    }

    private static string GetPrefabType(GameObject prefab)
    {
        if (IsStaticMesh(prefab))
        {
            return "Static Mesh";
        }
        else if (IsSkinnedMesh(prefab))
        {
            return "Skinned Mesh";
        }
        else
        {
            return "Other";
        }
    }

    private static bool IsStaticMesh(GameObject prefab)
    {
        return prefab.GetComponentInChildren<MeshFilter>() != null && prefab.GetComponentInChildren<MeshRenderer>() != null;
    }

    private static bool IsSkinnedMesh(GameObject prefab)
    {
        return prefab.GetComponentInChildren<SkinnedMeshRenderer>() != null;
    }

    private static IEnumerator GenerateThumbnailsCoroutine(GameObject prefab, string prefabName, string saveDir, Action<List<string>> callback)
    {
        List<string> thumbnailPaths = new List<string>();

        if (prefab.GetComponentInChildren<MeshRenderer>() != null || prefab.GetComponentInChildren<SkinnedMeshRenderer>() != null)
        {
            Debug.Log($"Generating thumbnails for {prefabName}");

            // Create a temporary scene
            var tempScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);

            // Create a temporary camera
            GameObject cameraObject = new GameObject("TempCamera");
            Camera camera = cameraObject.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0, 0, 0, 0); // 设置背景为透明
            camera.orthographic = true;
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 100f;
            camera.fieldOfView = 14;

            // Remove shadows by using ambient light and adjusting rendering settings
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = Color.white;

            // Instantiate the prefab in the scene
            GameObject instance = Instantiate(prefab);
            Bounds bounds = new Bounds(instance.transform.position, Vector3.zero);
            foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>())
            {
                bounds.Encapsulate(renderer.bounds);
            }

            // List of viewpoints (front, side)
            List<Vector3> cameraPositions = new List<Vector3>
            {
                bounds.center - Vector3.forward * (bounds.extents.magnitude * 1.5f), // Front view
                bounds.center - new Vector3(Mathf.Cos(Mathf.Deg2Rad * 60), 0, Mathf.Sin(Mathf.Deg2Rad * 60)) * (bounds.extents.magnitude * 1.5f), // 60-degree side view
            };

            foreach (Vector3 cameraPosition in cameraPositions)
            {
                camera.transform.position = cameraPosition;
                camera.transform.LookAt(bounds.center);
                camera.orthographicSize = bounds.extents.magnitude * 1.1f;

                // Render the camera's view to a RenderTexture
                RenderTexture renderTex = new RenderTexture(512, 512, 24);
                camera.targetTexture = renderTex;
                camera.Render();

                // Create a new texture and read the RenderTexture contents into it
                RenderTexture.active = renderTex;
                Texture2D screenshot = new Texture2D(renderTex.width, renderTex.height, TextureFormat.RGBA32, false);
                screenshot.ReadPixels(new Rect(0, 0, renderTex.width, renderTex.height), 0, 0);
                screenshot.Apply();
                RenderTexture.active = null;

                // Check if the screenshot is not all black
                if (!IsTextureBlack(screenshot))
                {
                    // Save the screenshot
                    byte[] bytes = screenshot.EncodeToPNG();
                    string thumbnailPath = Path.Combine(saveDir, $"{prefabName}_{cameraPositions.IndexOf(cameraPosition)}.png");
                    File.WriteAllBytes(thumbnailPath, bytes);

                    Debug.Log($"Saved thumbnail for {prefabName} at {thumbnailPath}");

                    thumbnailPaths.Add(thumbnailPath);
                }

                // Clean up
                camera.targetTexture = null; // Unassign the RenderTexture from the camera before destroying it
                UnityEngine.Object.DestroyImmediate(screenshot);
                UnityEngine.Object.DestroyImmediate(renderTex);
            }

            UnityEngine.Object.DestroyImmediate(cameraObject);
            UnityEngine.Object.DestroyImmediate(instance);

            // Unload the temporary scene
            EditorSceneManager.CloseScene(tempScene, true);
        }
        else
        {
            Debug.Log($"Prefab {prefabName} does not have suitable components for rendering thumbnails.");
        }

        callback(thumbnailPaths);
        yield return null;
    }

    private static IEnumerator GenerateMaterialThumbnailCoroutine(Material material, string materialName, string saveDir, Action<string> callback)
    {
        string thumbnailPath = null;

        // Get the built-in thumbnail from AssetPreview
        Texture2D thumbnail = AssetPreview.GetAssetPreview(material);
        while (thumbnail == null)
        {
            yield return null;
            thumbnail = AssetPreview.GetAssetPreview(material);
        }

        if (thumbnail != null)
        {
            // Save the thumbnail
            byte[] bytes = thumbnail.EncodeToPNG();
            thumbnailPath = Path.Combine(saveDir, $"{materialName}.png");
            File.WriteAllBytes(thumbnailPath, bytes);

            Debug.Log($"Saved thumbnail for {materialName} at {thumbnailPath}");
        }

        callback(thumbnailPath);
    }

    private static bool IsTextureBlack(Texture2D texture)
    {
        Color[] pixels = texture.GetPixels();
        foreach (Color pixel in pixels)
        {
            if (pixel != Color.black)
            {
                return false;
            }
        }
        return true;
    }

    private static void SaveAllAssetInfos(List<AssetInfo> assetInfos, string saveDir)
    {
        AllAssetInfos allAssetInfos = new AllAssetInfos
        {
            AssetInfos = assetInfos
        };

        string json = JsonUtility.ToJson(allAssetInfos, true);
        string jsonPath = Path.Combine(saveDir, "AllAssetInfo.json");
        File.WriteAllText(jsonPath, json);

        Debug.Log($"All asset information collected and saved to {jsonPath}");
    }

    [System.Serializable]
    public class AssetInfo
    {
        public string Name;
        public string Path;
        public string Type;
        public List<string> ThumbnailPaths;
    }

    [System.Serializable]
    public class AllAssetInfos
    {
        public List<AssetInfo> AssetInfos;
    }
}
