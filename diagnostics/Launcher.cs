using System;
using System.Diagnostics;
using System.IO;
using System.Text;
class DiagnosticLauncher {
    static int Main() {
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.Title = "伊莫地图助手 · WGC 兼容性诊断";
        Console.WriteLine("伊莫地图助手 v0.4.3 · WGC 兼容性诊断\n");
        Console.WriteLine("约需 1 分钟，故障时最多约 5 分钟。收帧测试仅使用自带窗口。\n另检查 WGC 支持状态、显示器对象、捕获服务及本次测试附近的相关事件。\n不修改系统或上传报告；无需管理员权限。\n请保持桌面解锁、测试窗口可见，不要在测试中切换用户或关闭测试窗口。\n");
        Console.WriteLine("按 Enter 开始，输入其他内容后回车取消。");
        if (Console.ReadLine() != "") return 0;
        Console.WriteLine("是否增加系统选择器对照？输入 Y 后需手动选测试窗口；直接回车跳过。\n只创建对象，不读取选中内容；取消或 60 秒未选择不计为采集失败。");
        bool picker = string.Equals(Console.ReadLine(), "y", StringComparison.OrdinalIgnoreCase);
        string root = AppDomain.CurrentDomain.BaseDirectory;
        int code=1;
        try {
            var info = new ProcessStartInfo(Path.Combine(root,"runtime","python.exe"),
                "-X utf8 \"" + Path.Combine(root,"diagnostics","run_diagnostics.py") + "\"" + (picker?" --picker":""));
            info.WorkingDirectory=root; info.UseShellExecute=false;
            using(var process=Process.Start(info)) { process.WaitForExit(); code=process.ExitCode; }
            Console.WriteLine("\n请将“诊断报告”文件夹内本次生成的诊断结果.txt 和 report.json 提供给开发者。");
        } catch(Exception ex) { Console.WriteLine("启动失败："+ex.Message+"\n请完整解压助手，保留 runtime 和 diagnostics 文件夹。"); }
        Console.WriteLine("\n按 Enter 关闭。"); Console.ReadLine(); return code;
    }
}
