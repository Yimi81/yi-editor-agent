using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using System.IO;
using System;
using UnityEditor.SceneManagement;
using Unity.EditorCoroutines.Editor;

public class AssetInfoCollector : MonoBehaviour
{
    // Remove the static readonly saveDir field
    // private static readonly string saveDir = @"E:\Images"; // Comment this out as it will be passed as a parameter

    [MenuItem("Tools/Collect Prefab Info")]
    public static void CollectPrefabInfo(string saveDir)
    {
        Debug.Log("CollectPrefabInfo started");

        string[] allPrefabGuids = AssetDatabase.FindAssets("t:Prefab");

        // Limit to the first 500 prefabs for testing
        int limit = Mathf.Min(allPrefabGuids.Length, 1000);
        string[] limitedPrefabGuids = new string[limit];
        Array.Copy(allPrefabGuids, limitedPrefabGuids, limit);

        List<PrefabInfo> prefabInfos = new List<PrefabInfo>();

        if (!Directory.Exists(saveDir))
        {
            Directory.CreateDirectory(saveDir);
            Debug.Log($"Created directory: {saveDir}");
        }

        Debug.Log($"limitedPrefabGuids length: {limitedPrefabGuids.Length}");

        foreach (string guid in limitedPrefabGuids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);

            if (prefab != null)
            {
                Debug.Log($"Processing prefab: {prefab.name}");

                if (IsStaticMesh(prefab) || IsSkinnedMesh(prefab))
                {
                    PrefabInfo prefabInfo = new PrefabInfo
                    {
                        Name = prefab.name,
                        Path = assetPath,
                        Type = GetPrefabType(prefab),
                        Tags = prefab.tag,
                        Layer = LayerMask.LayerToName(prefab.layer),
                        CreationDate = GetCreationDate(assetPath),
                        ModificationDate = GetModificationDate(assetPath),
                    };

                    // Start the coroutine to generate the thumbnails
                    Debug.Log($"Starting thumbnail generation for: {prefab.name}");
                    EditorCoroutineUtility.StartCoroutineOwnerless(GenerateThumbnailsCoroutine(prefab, prefab.name, saveDir, (thumbnailPaths) =>
                    {
                        if (thumbnailPaths != null && thumbnailPaths.Count == 2) // Ensure both thumbnails are generated
                        {
                            prefabInfo.ThumbnailPaths = thumbnailPaths;
                            prefabInfos.Add(prefabInfo);
                            SavePrefabInfos(prefabInfos, saveDir); // Pass saveDir to SavePrefabInfos
                            Debug.Log($"Thumbnail generation completed for: {prefab.name}");
                        }
                        else
                        {
                            Debug.Log($"Thumbnail generation failed for: {prefab.name}");
                        }
                    }));
                }
                else
                {
                    Debug.Log($"Prefab {prefab.name} does not have suitable components for thumbnail generation.");
                }
            }
            else
            {
                Debug.Log($"Failed to load prefab at path: {assetPath}");
            }
        }

        Debug.Log("CollectPrefabInfo completed");
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

    private static List<string> GetComponentNames(GameObject prefab)
    {
        Component[] components = prefab.GetComponentsInChildren<Component>();
        List<string> componentNames = new List<string>();

        foreach (Component component in components)
        {
            if (component != null) // Ensure component is not null
            {
                componentNames.Add(component.GetType().Name);
            }
        }

        return componentNames;
    }

    private static string GetCreationDate(string assetPath)
    {
        string fullPath = Path.Combine(Application.dataPath.Replace("Assets", ""), assetPath);
        return File.GetCreationTime(fullPath).ToString("yyyy-MM-dd HH:mm:ss");
    }

    private static string GetModificationDate(string assetPath)
    {
        string fullPath = Path.Combine(Application.dataPath.Replace("Assets", ""), assetPath);
        return File.GetLastWriteTime(fullPath).ToString("yyyy-MM-dd HH:mm:ss");
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

    private static void SavePrefabInfos(List<PrefabInfo> prefabInfos, string saveDir)
    {
        string json = JsonUtility.ToJson(new PrefabInfoList(prefabInfos), true);
        string jsonPath = Path.Combine(saveDir, "PrefabInfo.json");
        File.WriteAllText(jsonPath, json);

        Debug.Log($"Prefab information collected and saved to {jsonPath}");
    }

    [System.Serializable]
    public class PrefabInfo
    {
        public string Name;
        public string Path;
        public string Type;
        public string Tags;
        public string Layer;
        public string CreationDate;
        public string ModificationDate;
        public List<string> ThumbnailPaths;

        // Add other fields as needed
    }

    [System.Serializable]
    public class PrefabInfoList
    {
        public List<PrefabInfo> PrefabInfos;

        public PrefabInfoList(List<PrefabInfo> prefabInfos)
        {
            PrefabInfos = prefabInfos;
        }
    }
}
