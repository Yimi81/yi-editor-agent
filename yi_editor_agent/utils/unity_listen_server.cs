using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using UnityEditor;
using UnityEngine;
using System.Net;
using System.IO;

public class AssetListenServer : EditorWindow
{
    private HttpListener listener;
    private Thread listenerThread;

    [MenuItem("Tools/Start Web Server")]
    public static void ShowWindow()
    {
        GetWindow<AssetListenServer>("Web Server");
    }

    private void OnEnable()
    {
        listener = new HttpListener();
        listener.Prefixes.Add("http://0.0.0.0:5000/");
        listener.Prefixes.Add("http://localhost:5000/");
        listener.Prefixes.Add("http://10.1.50.209:5000/");
        listener.Prefixes.Add($"http://{Dns.GetHostName()}:5000/");
        listener.Start();
        Debug.Log("Web Server Start");
        listenerThread = new Thread(new ThreadStart(HandleRequests));
        listenerThread.Start();
    }

    private void OnDisable()
    {
        listener.Stop();
        Debug.Log("Web Server Stop");
        listenerThread.Abort();
    }

    private void HandleRequests()
    {
        while (listener.IsListening)
        {
            var context = listener.GetContext();
            var request = context.Request;
            var response = context.Response;

            if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/navigate")
            {
                using (var reader = new System.IO.StreamReader(request.InputStream, request.ContentEncoding))
                {
                    var json = reader.ReadToEnd();
                    var data = JsonUtility.FromJson<PathRequest>(json);
                    EditorApplication.delayCall += () =>
                    {
                        NavigateToAsset(data.path);
                        // Call Windows API after delay to bring Unity to front
                        EditorApplication.delayCall += BringUnityEditorToFront;
                    };
                }

                var responseString = "{\"message\": \"Path received\"}";
                var buffer = System.Text.Encoding.UTF8.GetBytes(responseString);
                response.ContentLength64 = buffer.Length;
                var output = response.OutputStream;
                output.Write(buffer, 0, buffer.Length);
                output.Close();
            }
            else if (request.HttpMethod == "POST" && request.Url.AbsolutePath == "/project_info")
            {
                using (var reader = new System.IO.StreamReader(request.InputStream, request.ContentEncoding))
                {
                    var json = reader.ReadToEnd();
                    var data = JsonUtility.FromJson<ProjectInfoRequest>(json);
                    EditorApplication.delayCall += () =>
                    {
                        AssetInfoCollector.CollectPrefabInfo(data.outputPath);
                    };
                }

                var responseString = "{\"message\": \"CollectPrefabInfo started\"}";
                var buffer = System.Text.Encoding.UTF8.GetBytes(responseString);
                response.ContentLength64 = buffer.Length;
                var output = response.OutputStream;
                output.Write(buffer, 0, buffer.Length);
                output.Close();
            }
        }
    }

    private void NavigateToAsset(string assetPath)
    {
        var asset = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(assetPath);
        if (asset != null)
        {
            Selection.activeObject = asset;
            EditorGUIUtility.PingObject(asset);
            Debug.Log($"Navigated to asset: {assetPath}");

            // Switch to Project window
            EditorApplication.ExecuteMenuItem("Window/General/Project");
        }
        else
        {
            Debug.LogError($"Asset not found: {assetPath}");
        }
    }

    private void BringUnityEditorToFront()
    {
        IntPtr unityWindowHandle = FindUnityEditorWindow();
        Debug.Log($"Unity window handle: {unityWindowHandle}");
        if (unityWindowHandle != IntPtr.Zero)
        {
            Debug.Log("Bringing Unity editor window to front.");
            // Restore the window if it is minimized
            ShowWindow(unityWindowHandle, SW_RESTORE);
            // Bring to front
            bool flag = SetForegroundWindow(unityWindowHandle);
            if (flag)
            {
                Debug.Log("Unity editor window brought to front.");
            }
            else
            {
                Debug.LogError("Failed to bring Unity editor window to front.");
            }
        }
        else
        {
            Debug.LogError("Unity editor window not found.");
        }
    }

    private IntPtr FindUnityEditorWindow()
    {
        IntPtr unityWindowHandle = IntPtr.Zero;
        EnumWindows((hWnd, lParam) =>
        {
            if (IsWindowVisible(hWnd))
            {
                StringBuilder title = new StringBuilder(256);
                GetWindowText(hWnd, title, title.Capacity);

                if (title.ToString().Contains("Unity"))
                {
                    unityWindowHandle = hWnd;
                    return false; // Stop enumeration
                }
            }
            return true; // Continue enumeration
        }, IntPtr.Zero);

        return unityWindowHandle;
    }

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

    [DllImport("user32.dll")]
    private static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    private const int SW_RESTORE = 9;

    [Serializable]
    private class PathRequest
    {
        public string path;
    }

    [Serializable]
    private class ProjectInfoRequest
    {
        public string projectPath;
        public string outputPath;
    }
}
