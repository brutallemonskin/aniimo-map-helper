using System;
using System.Drawing;
using System.Windows.Forms;
class Fixture : Form {
    int tick;
    Timer timer = new Timer();
    protected override bool ShowWithoutActivation { get { return true; } }
    Fixture() {
        Text = "Aniimo WGC lab fixture";
        ClientSize = new Size(640, 400);
        StartPosition = FormStartPosition.Manual;
        Location = new Point(30, 30);
        DoubleBuffered = true;
        timer.Interval = 80;
        timer.Tick += delegate {
            tick++;
            if (tick % 40 == 0) ClientSize = new Size(tick % 80 == 0 ? 640 : 800, 400);
            Invalidate();
        };
        timer.Start();
    }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.Clear(Color.FromArgb(20, 45, 70));
        e.Graphics.FillRectangle(Brushes.Lime, (tick * 17) % (ClientSize.Width - 100), 70, 100, 180);
        e.Graphics.DrawString("WGC test frame " + tick, Font, Brushes.White, 25, 25);
    }
    [STAThread] static void Main() { Application.Run(new Fixture()); }
}
