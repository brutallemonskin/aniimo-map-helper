using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;
// COM ABI signatures/IIDs from the Windows SDK; no SDK/runtime projection is shipped.
class ItemProbe {
    [DllImport("combase.dll")] static extern int RoInitialize(uint kind);
    [DllImport("combase.dll")] static extern void RoUninitialize();
    [DllImport("combase.dll", CharSet=CharSet.Unicode)] static extern int WindowsCreateString(string text, uint length, out IntPtr value);
    [DllImport("combase.dll")] static extern int WindowsDeleteString(IntPtr value);
    [DllImport("combase.dll")] static extern int RoGetActivationFactory(IntPtr name, ref Guid iid, out IntPtr factory);
    [DllImport("combase.dll")] static extern int RoActivateInstance(IntPtr name, out IntPtr value);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr window, uint flags);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int ItemCall(IntPtr self, IntPtr target, ref Guid iid, out IntPtr item);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int BoolCall(IntPtr self, out byte value);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int PtrCall(IntPtr self, out IntPtr value);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int IntCall(IntPtr self, out int value);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int InitCall(IntPtr self, IntPtr window);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int VoidCall(IntPtr self);
    static T Method<T>(IntPtr self, int slot) where T : class {
        return Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(self), slot*IntPtr.Size), typeof(T)) as T;
    }
    static readonly List<IntPtr> owned = new List<IntPtr>();
    static IntPtr Own(IntPtr p) { if(p!=IntPtr.Zero) owned.Add(p); return p; }
    static void Check(string stage, int hr) {
        Console.WriteLine(stage + " 0x" + unchecked((uint)hr).ToString("X8"));
        Marshal.ThrowExceptionForHR(hr);
    }
    static IntPtr Query(IntPtr p, string id) {
        Guid iid=new Guid(id); IntPtr value;
        Check("QueryInterface", Marshal.QueryInterface(p, ref iid, out value)); return Own(value);
    }
    static IntPtr Activate(string cls, string id) {
        IntPtr name=IntPtr.Zero, value;
        try {
            Check("WindowsCreateString", WindowsCreateString(cls, (uint)cls.Length, out name));
            if(id==null) Check("ActivateInstance", RoActivateInstance(name, out value));
            else { Guid iid=new Guid(id); Check("ActivationFactory", RoGetActivationFactory(name, ref iid, out value)); }
            return Own(value);
        } finally { if(name!=IntPtr.Zero) WindowsDeleteString(name); }
    }
    static int Result(string state, bool? supported) {
        Console.WriteLine("RESULT_JSON:{\"state\":\""+state+"\",\"supported\":"+(supported.HasValue?(supported.Value?"true":"false"):"null")+"}");
        return state=="ok" ? 0 : state=="cancelled" || state=="timeout" ? 2 : 1;
    }
    [STAThread] static int Main(string[] args) {
        Console.OutputEncoding=new UTF8Encoding(false);
        bool initialized=false;
        try {
            Check("RoInitialize", RoInitialize(0)); initialized=true;
            string mode=args.Length>0?args[0]:"support";
            if(mode=="support") {
                IntPtr statics=Activate("Windows.Graphics.Capture.GraphicsCaptureSession", "2224A540-5974-49AA-B232-0882536F4CB5");
                byte value; Check("IsSupported", Method<BoolCall>(statics,6)(statics,out value));
                return Result(value!=0?"ok":"unsupported",value!=0);
            }
            if(mode=="picker") {
                using(Form owner=new Form()) {
                    owner.Text="伊莫 WGC 选择器诊断（只创建对象，不读取画面）";
                    owner.Width=540; owner.Height=110; owner.StartPosition=FormStartPosition.CenterScreen;
                    var label=new Label(); label.Dock=DockStyle.Fill;
                    label.Text="请选择 Aniimo WGC lab fixture 测试窗口。\n可以取消；60 秒未选择将自动结束，不计为采集失败。";
                    owner.Controls.Add(label); owner.Show(); Application.DoEvents();
                    IntPtr picker=Activate("Windows.Graphics.Capture.GraphicsCapturePicker",null);
                    IntPtr init=Query(picker,"3E68D4BD-7135-4D10-8018-9FB6D9F33FA1");
                    Check("InitializeWithWindow", Method<InitCall>(init,3)(init,owner.Handle));
                    IntPtr pick=Query(picker,"5A1711B3-AD79-4B4A-9336-1318FDDE3539"), operation;
                    Check("PickSingleItemAsync",Method<PtrCall>(pick,6)(pick,out operation)); Own(operation);
                    IntPtr info=Query(operation,"00000036-0000-0000-C000-000000000046");
                    var watch=Stopwatch.StartNew(); int status;
                    while(true) {
                        Application.DoEvents(); CheckStatus(info,out status);
                        if(status!=0) break;
                        if(owner.IsDisposed || watch.Elapsed.TotalSeconds>=60) {
                            Method<VoidCall>(info,9)(info); return Result(owner.IsDisposed?"cancelled":"timeout",null);
                        }
                        Thread.Sleep(30);
                    }
                    if(status==2) return Result("cancelled",null);
                    if(status==3) { int error; Check("AsyncErrorCode",Method<IntCall>(info,8)(info,out error)); Check("PickerResult",error); }
                    IntPtr item; Check("PickerGetResults",Method<PtrCall>(operation,8)(operation,out item)); Own(item);
                    return Result(item==IntPtr.Zero?"cancelled":"ok",null);
                }
            }
            IntPtr target=new IntPtr(long.Parse(args[1]));
            if(mode!="window" && mode!="monitor") throw new ArgumentException("Unknown probe mode");
            if(mode=="monitor") { target=MonitorFromWindow(target,2); if(target==IntPtr.Zero) throw new InvalidOperationException("No monitor available"); }
            IntPtr interop=Activate("Windows.Graphics.Capture.GraphicsCaptureItem","3628E81B-3CAC-4C60-B7F4-23CE0E0C3356"), captureItem;
            Guid itemIid=new Guid("79C3F95B-31F7-4EC2-A464-632EF5D30760");
            Check(mode=="window"?"CreateForWindow":"CreateForMonitor",Method<ItemCall>(interop,mode=="window"?3:4)(interop,target,ref itemIid,out captureItem)); Own(captureItem);
            if(captureItem==IntPtr.Zero) throw new InvalidOperationException("Capture item is null");
            return Result("ok",null);
        } catch(Exception ex) {
            Console.WriteLine(ex.ToString());
            uint code=unchecked((uint)ex.HResult);
            if(args.Length>0 && args[0]=="picker" && (code==0x800704C7 || code==0x80004004)) return Result("cancelled",null);
            return Result("failed",null);
        }
        finally { for(int i=owned.Count-1;i>=0;i--) Marshal.Release(owned[i]); if(initialized) RoUninitialize(); }
    }
    static void CheckStatus(IntPtr info,out int status) {
        int hr=Method<IntCall>(info,7)(info,out status); if(hr<0) Check("AsyncStatus",hr);
    }
}
