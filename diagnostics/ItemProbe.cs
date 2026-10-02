using System;
using System.Runtime.InteropServices;
[ComImport, Guid("3628E81B-3CAC-4C60-B7F4-23CE0E0C3356"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IGraphicsCaptureItemInterop {
    [PreserveSig] int CreateForWindow(IntPtr window, ref Guid iid, out IntPtr item);
    [PreserveSig] int CreateForMonitor(IntPtr monitor, ref Guid iid, out IntPtr item);
}
class ItemProbe {
    [DllImport("combase.dll")] static extern int RoInitialize(uint kind);
    [DllImport("combase.dll")] static extern void RoUninitialize();
    [DllImport("combase.dll", CharSet=CharSet.Unicode)] static extern int WindowsCreateString(string text, uint length, out IntPtr value);
    [DllImport("combase.dll")] static extern int WindowsDeleteString(IntPtr value);
    [DllImport("combase.dll")] static extern int RoGetActivationFactory(IntPtr name, ref Guid iid, out IntPtr factory);
    static void Check(string stage, int hr) {
        Console.WriteLine(stage + " 0x" + unchecked((uint)hr).ToString("X8"));
        Marshal.ThrowExceptionForHR(hr);
    }
    [MTAThread] static int Main(string[] args) {
        IntPtr name=IntPtr.Zero, raw=IntPtr.Zero, item=IntPtr.Zero;
        object wrapper=null; bool initialized=false;
        try {
            Check("RoInitialize", RoInitialize(1)); initialized=true;
            string cls="Windows.Graphics.Capture.GraphicsCaptureItem";
            Check("WindowsCreateString", WindowsCreateString(cls, (uint)cls.Length, out name));
            Guid iid=new Guid("3628E81B-3CAC-4C60-B7F4-23CE0E0C3356");
            Check("ActivationFactory", RoGetActivationFactory(name, ref iid, out raw));
            wrapper=Marshal.GetObjectForIUnknown(raw);
            Guid itemIid=new Guid("79C3F95B-31F7-4EC2-A464-632EF5D30760");
            Check("CreateForWindow", ((IGraphicsCaptureItemInterop)wrapper).CreateForWindow(new IntPtr(long.Parse(args[0])), ref itemIid, out item));
            return 0;
        } catch(Exception ex) { Console.WriteLine(ex.ToString()); return 1; }
        finally {
            if(item!=IntPtr.Zero) Marshal.Release(item);
            if(wrapper!=null) Marshal.ReleaseComObject(wrapper);
            if(raw!=IntPtr.Zero) Marshal.Release(raw);
            if(name!=IntPtr.Zero) WindowsDeleteString(name);
            if(initialized) RoUninitialize();
        }
    }
}
