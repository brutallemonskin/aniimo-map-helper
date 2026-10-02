using System;
using System.Diagnostics;
using System.IO;
using System.Text;
class DiagnosticLauncher {
    static int Main() {
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.Title = "伊莫地图助手 · WGC 兼容性诊断";
        Console.WriteLine("伊莫地图助手 v0.4.2 · WGC 兼容性诊断\n");
        Console.WriteLine("约需 1 分钟，故障时最多约 3 分钟。仅采集自动打开的测试窗口。\n不会采集游戏、修改系统设置或上传报告；无需管理员权限。\n请保持桌面解锁、测试窗口可见，不要在测试中切换用户或关闭测试窗口。\n");
        Console.WriteLine("按 Enter 开始，输入其他内容后回车取消。");
        if (Console.ReadLine() != "") return 0;
        string root = AppDomain.CurrentDomain.BaseDirectory;
        int code=1;
        try {
            var info = new ProcessStartInfo(Path.Combine(root,"runtime","python.exe"),
                "-X utf8 \"" + Path.Combine(root,"diagnostics","run_diagnostics.py") + "\"");
            info.WorkingDirectory=root; info.UseShellExecute=false;
            using(var process=Process.Start(info)) { process.WaitForExit(); code=process.ExitCode; }
            Console.WriteLine("\n请将“诊断报告”文件夹内本次生成的诊断结果.txt 和 report.json 提供给开发者。");
        } catch(Exception ex) { Console.WriteLine("启动失败："+ex.Message+"\n请完整解压助手，保留 runtime 和 diagnostics 文件夹。"); }
        Console.WriteLine("\n按 Enter 关闭。"); Console.ReadLine(); return code;
    }
}
