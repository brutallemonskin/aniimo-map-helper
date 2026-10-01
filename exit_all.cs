using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Net;
using System.Runtime.InteropServices;
using System.Threading;

// Identify this app by its actual Python entry point and companion sources.
// Never stop a process merely because its name is python or its port is 18731.
static class ExitAll {
    [DllImport("shell32.dll", SetLastError=true)]
    static extern IntPtr CommandLineToArgvW([MarshalAs(UnmanagedType.LPWStr)] string command, out int count);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr memory);
    [DllImport("iphlpapi.dll", SetLastError=true)]
    static extern uint GetExtendedTcpTable(IntPtr table, ref int size, bool order, int family, int kind, uint reserved);
    [StructLayout(LayoutKind.Sequential)]
    struct TcpRow { public uint state, address, port, remoteAddress, remotePort, pid; }
    sealed class Instance {
        public int pid;
        public long started;
        public string executable;
        public bool server;
    }

    static string EntryPoint(string command) {
        int count;
        IntPtr argv=CommandLineToArgvW(command, out count);
        if(argv==IntPtr.Zero) return null;
        try {
            for(int i=1;i<count;i++) {
                string arg=Marshal.PtrToStringUni(Marshal.ReadIntPtr(argv,i*IntPtr.Size));
                if(arg=="-c" || arg=="-m") return null;
                if(arg=="-X" || arg=="-W") { i++; continue; }
                if(arg.StartsWith("-",StringComparison.Ordinal)) continue;
                return Path.IsPathRooted(arg) ? Path.GetFullPath(arg) : null;
            }
            return null;
        } finally { LocalFree(argv); }
    }

    static bool IsHelper(string entry) {
        if(String.IsNullOrEmpty(entry)) return false;
        string name=Path.GetFileName(entry);
        if(name!="server.py" && name!="overlay_window.py") return false;
        string root=Path.GetDirectoryName(entry);
        try {
            string server=File.ReadAllText(Path.Combine(root,"server.py"));
            string index=File.ReadAllText(Path.Combine(root,"index.html"));
            return File.Exists(entry) && server.Contains("/api/status") && server.Contains("/api/match") &&
                index.Contains("伊莫") &&
                File.ReadAllText(Path.Combine(root,"matcher.py")).Contains("class Matcher") &&
                File.ReadAllText(Path.Combine(root,"overlay_bridge.py")).Contains("class OverlayBridge");
        } catch(IOException) { return false; }
          catch(UnauthorizedAccessException) { return false; }
    }

    static List<Instance> Find() {
        var found=new List<Instance>();
        using(var query=new ManagementObjectSearcher("SELECT ProcessId, ExecutablePath, CommandLine FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe'"))
        using(var rows=query.Get()) {
            foreach(ManagementObject row in rows) using(row) {
                try {
                    string entry=EntryPoint(Convert.ToString(row["CommandLine"]));
                    if(!IsHelper(entry)) continue;
                    int pid=Convert.ToInt32(row["ProcessId"]);
                    using(var process=Process.GetProcessById(pid)) {
                        if(process.SessionId!=Process.GetCurrentProcess().SessionId) continue;
                        string executable=process.MainModule.FileName;
                        if(!String.Equals(executable,Convert.ToString(row["ExecutablePath"]),StringComparison.OrdinalIgnoreCase)) continue;
                        found.Add(new Instance {pid=pid,started=process.StartTime.ToUniversalTime().Ticks,
                            executable=executable,server=Path.GetFileName(entry)=="server.py"});
                    }
                } catch(ArgumentException) { }
                  catch(InvalidOperationException) { }
                  catch(System.ComponentModel.Win32Exception) { }
            }
        }
        return found;
    }

    static Process Current(Instance instance) {
        Process process=null;
        try {
            process=Process.GetProcessById(instance.pid);
            // Open a handle and verify start time to guard against PID reuse.
            IntPtr handle=process.Handle;
            if(!process.HasExited && process.StartTime.ToUniversalTime().Ticks==instance.started &&
                String.Equals(process.MainModule.FileName,instance.executable,StringComparison.OrdinalIgnoreCase)) return process;
        } catch(ArgumentException) { }
          catch(InvalidOperationException) { }
          catch(System.ComponentModel.Win32Exception) { }
        if(process!=null) process.Dispose();
        return null;
    }

    static List<int> Ports(int pid) {
        var ports=new List<int>();
        int size=0;
        GetExtendedTcpTable(IntPtr.Zero,ref size,false,2,3,0);
        if(size<=0) return ports;
        IntPtr table=Marshal.AllocHGlobal(size);
        try {
            if(GetExtendedTcpTable(table,ref size,false,2,3,0)!=0) return ports;
            int count=Marshal.ReadInt32(table), stride=Marshal.SizeOf(typeof(TcpRow));
            for(int i=0;i<count;i++) {
                var row=(TcpRow)Marshal.PtrToStructure(IntPtr.Add(table,4+i*stride),typeof(TcpRow));
                if(row.pid==(uint)pid && row.state==2 && (row.address==0x0100007f || row.address==0))
                    ports.Add((int)(((row.port&255)<<8)|((row.port>>8)&255)));
            }
        } finally { Marshal.FreeHGlobal(table); }
        return ports;
    }

    static void Graceful(Instance instance) {
        using(var process=Current(instance)) {
            if(process==null) return;
            foreach(int port in Ports(instance.pid)) {
                try {
                    var request=(HttpWebRequest)WebRequest.Create("http://127.0.0.1:"+port+"/api/shutdown");
                    request.Proxy=null;request.AllowAutoRedirect=false;
                    request.Method="POST";request.ContentLength=0;request.Timeout=1500;request.ReadWriteTimeout=1500;
                    using(var response=request.GetResponse()) { }
                } catch(WebException) { }
            }
        }
    }

    public static void Stop() {
        List<Instance> instances=Find();
        foreach(var instance in instances) if(instance.server) Graceful(instance);
        var watch=Stopwatch.StartNew();
        while(watch.ElapsedMilliseconds<3500) {
            bool alive=false;
            foreach(var instance in instances) using(var process=Current(instance)) if(process!=null) alive=true;
            if(!alive) break;
            Thread.Sleep(100);
        }
        // Include an overlay that was launched just before its server stopped.
        foreach(var newer in Find()) if(!instances.Exists(i=>i.pid==newer.pid && i.started==newer.started)) instances.Add(newer);
        var failed=new List<string>();
        foreach(var instance in instances) using(var process=Current(instance)) {
            if(process==null) continue;
            try { process.Kill(); if(!process.WaitForExit(3000)) failed.Add(instance.pid.ToString()); }
            catch(InvalidOperationException) { }
            catch(System.ComponentModel.Win32Exception) { failed.Add(instance.pid.ToString()); }
        }
        if(failed.Count>0) throw new Exception("部分助手进程未能退出，请从对应助手目录退出或在任务管理器中检查。进程号："+String.Join(", ",failed.ToArray()));
    }
}
