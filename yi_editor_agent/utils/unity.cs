using UnityEditor;
using UnityEngine;
using System.Collections.Generic;
using System.IO;

public class PrefabInfoCollector : MonoBehaviour
{
    [MenuItem("Tools/Collect Prefab Info")]
    public static void CollectPrefabInfo()
    {
        string[] allPrefabGuids = AssetDatabase.FindAssets("t:Prefab");
        List<PrefabInfo> prefabInfos = new List<PrefabInfo>();

        string thumbnailsDir = "Assets/PrefabThumbnails";
        if (!Directory.Exists(thumbnailsDir))
        {
            Directory.CreateDirectory(thumbnailsDir);
        }

        foreach (string guid in allPrefabGuids)
        {
            string assetPath = AssetDatabase.GUIDToAssetPath(guid);
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);

            if (prefab != null)
            {
                PrefabInfo prefabInfo = new PrefabInfo
                {
                    Name = prefab.name,
                    Path = assetPath,
                    Type = GetPrefabType(prefab),
                    ComponentNames = GetComponentNames(prefab),
                    Tags = prefab.tag,
                    Layer = LayerMask.LayerToName(prefab.layer),
                    CreationDate = GetCreationDate(assetPath),
                    ModificationDate = GetModificationDate(assetPath),
                    ThumbnailPaths = GetPrefabThumbnails(prefab, guid, thumbnailsDir)
                };

                prefabInfos.Add(prefabInfo);
            }
        }

        // Serialize the collected information to a JSON file or directly store it in your vector database
        string json = JsonUtility.ToJson(new PrefabInfoList(prefabInfos), true);
        File.WriteAllText("Assets/PrefabInfo.json", json);

        Debug.Log("Prefab information collected and saved to Assets/PrefabInfo.json");
    }

    private static string GetPrefabType(GameObject prefab)
    {
        if (IsStaticMesh(prefab))
        {
            return "Static Mesh";
        }
        else if (IsUIElement(prefab))
        {
            return "UI Element";
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

    private static bool IsUIElement(GameObject prefab)
    {
        return prefab.GetComponentInChildren<RectTransform>() != null || prefab.GetComponentInChildren<CanvasRenderer>() != null;
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

    private static List<string> GetPrefabThumbnails(GameObject prefab, string guid, string saveDir)
    {
        List<string> thumbnailPaths = new List<string>();

        if (IsStaticMesh(prefab))
        {
            // Generate three views (front, side, top)
            thumbnailPaths.Add(GenerateThumbnail(prefab, guid, saveDir, "Front"));
            thumbnailPaths.Add(GenerateThumbnail(prefab, guid, saveDir, "Side"));
            thumbnailPaths.Add(GenerateThumbnail(prefab, guid, saveDir, "Top"));
        }
        else
        {
            // Generate a single thumbnail for other types
            string thumbnailPath = GenerateThumbnail(prefab, guid, saveDir, "Preview");
            thumbnailPaths.Add(thumbnailPath);
        }

        return thumbnailPaths;
    }

    private static string GenerateThumbnail(GameObject prefab, string guid, string saveDir, string view)
    {
        Texture2D thumbnail = AssetPreview.GetAssetPreview(prefab);
        
        // If still null, try using GetMiniThumbnail
        if (thumbnail == null)
        {
            thumbnail = AssetPreview.GetMiniThumbnail(prefab);
        }

        if (thumbnail != null)
        {
            // Create a new readable texture
            Texture2D readableThumbnail = new Texture2D(thumbnail.width, thumbnail.height, TextureFormat.RGBA32, false);
            RenderTexture rt = RenderTexture.GetTemporary(thumbnail.width, thumbnail.height, 0, RenderTextureFormat.Default, RenderTextureReadWrite.Linear);

            Graphics.Blit(thumbnail, rt);
            RenderTexture previous = RenderTexture.active;
            RenderTexture.active = rt;
            readableThumbnail.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            readableThumbnail.Apply();
            RenderTexture.active = previous;
            RenderTexture.ReleaseTemporary(rt);

            byte[] bytes = readableThumbnail.EncodeToPNG();
            string thumbnailPath = Path.Combine(saveDir, $"{guid}_{view}.png");
            File.WriteAllBytes(thumbnailPath, bytes);

            Object.DestroyImmediate(readableThumbnail);
            return thumbnailPath;
        }
        else
        {
            Debug.LogWarning($"Thumbnail generation failed for prefab: {prefab.name}");
            return string.Empty;
        }
    }

    [System.Serializable]
    public class PrefabInfo
    {
        public string Name;
        public string Path;
        public string Type;
        public List<string> ComponentNames;
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
