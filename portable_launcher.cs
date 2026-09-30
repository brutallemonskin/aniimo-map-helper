using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Windows.Forms;

class PortableLauncher {
    const string Url = "http://127.0.0.1:18731";
    static string Status() {
        try {
            var request = (HttpWebRequest)WebRequest.Create(Url + "/api/status");
            request.Timeout = 1000;
            using(var response = request.GetResponse())
            using(var reader = new StreamReader(response.GetResponseStream())) return reader.ReadToEnd();
        } catch { return ""; }
    }
    [STAThread]
    static void Main(string[] args) {
        var root = AppDomain.CurrentDomain.BaseDirectory;
        var app = Path.Combine(root,"app");
        var python = Path.Combine(root,"runtime","pythonw.exe");
        try {
#if STOP
            var pidFile = Path.Combine(app,"server.pid");
            if (!File.Exists(pidFile)) return;
            Process server;
            try { server=Process.GetProcessById(Int32.Parse(File.ReadAllText(pidFile))); }
            catch(ArgumentException) { return; }
            if (!String.Equals(server.MainModule.FileName,python,StringComparison.OrdinalIgnoreCase)) {
                MessageBox.Show("当前运行的不是这份便携版，请从对应助手退出。","地宫领航"); return;
            }
            if (!Status().Contains("indexed")) return;
            var request=(HttpWebRequest)WebRequest.Create(Url+"/api/shutdown");
            request.Method="POST"; request.ContentLength=0; request.Timeout=5000;
            using(var response=request.GetResponse()) {}
#else
            if (!File.Exists(python) || !File.Exists(Path.Combine(app,"server.py")))
                throw new Exception("文件不完整。请先解压整个压缩包，再双击启动助手。");
            var status=Status();
            if (status.Contains("indexed") && status.Contains("version")) {
                Process.Start(new ProcessStartInfo(Url){UseShellExecute=true}); return;
            }
            var info=new ProcessStartInfo(python,"-X utf8 \""+Path.Combine(app,"server.py")+"\" --no-browser") {
                WorkingDirectory=app,UseShellExecute=false,CreateNoWindow=true
            };
            // The launcher is run by the user on their desktop, so the overlay shares it.
            info.EnvironmentVariables.Remove("ANIIMO_PORT");
            var process=Process.Start(info);
            for(int i=0;i<60;i++) {
                if (process.HasExited) throw new Exception("助手未能启动。请检查 18731 端口是否被其他程序占用。");
                if (Status().Contains("indexed")) {
                    Process.Start(new ProcessStartInfo(Url){UseShellExecute=true}); return;
                }
                Thread.Sleep(250);
            }
            throw new Exception("启动较慢，请稍后重新双击启动助手。");
#endif
        } catch(Exception e) { MessageBox.Show(e.Message,"地宫领航",MessageBoxButtons.OK,MessageBoxIcon.Information); }
    }
}
