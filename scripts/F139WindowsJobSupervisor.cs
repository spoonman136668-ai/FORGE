// F139 Windows-only child lifetime binding. Task Scheduler terminates the PowerShell
// launcher; its OS job handle closes, force-ending the bound Python child.
// The child is created SUSPENDED and assigned before it is allowed to run.
// Fail closed if native job admission is unavailable. No separate window.
using System;
using System.ComponentModel;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

public static class F139WindowsJobSupervisor
{
    private const uint CREATE_SUSPENDED = 0x00000004;
    private const uint CREATE_NO_WINDOW = 0x08000000;
    private const uint STARTF_USESTDHANDLES = 0x00000100;
    private const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    private const int JobObjectExtendedLimitInformation = 9;
    private const uint FILE_APPEND_DATA = 0x00000004;
    private const uint GENERIC_READ = 0x80000000;
    private const uint FILE_SHARE_ALL = 0x00000007;
    private const uint OPEN_ALWAYS = 4;
    private const uint OPEN_EXISTING = 3;
    private const uint WAIT_OBJECT_0 = 0;
    private const uint WAIT_FAILED = 0xFFFFFFFF;
    private const uint INFINITE = 0xFFFFFFFF;
    private const int STDIN_FLAGS = 0x100;

    [StructLayout(LayoutKind.Sequential)]
    private struct SECURITY_ATTRIBUTES
    {
        public int nLength;
        public IntPtr lpSecurityDescriptor;
        public int bInheritHandle;
    }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct STARTUPINFO
    {
        public uint cb;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpReserved;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpDesktop;
        [MarshalAs(UnmanagedType.LPWStr)] public string lpTitle;
        public uint dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public ushort wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct PROCESS_INFORMATION
    {
        public IntPtr hProcess, hThread;
        public uint dwProcessId, dwThreadId;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit, PerJobUserTimeLimit;
        public uint LimitFlags;
        public IntPtr MinimumWorkingSetSize, MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct IO_COUNTERS
    {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount, WriteTransferCount, OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    private struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public IntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", EntryPoint = "CreateJobObjectW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SetInformationJobObject(IntPtr job, int kind,
        ref JOBOBJECT_EXTENDED_LIMIT_INFORMATION data, uint length);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", EntryPoint = "CreateFileW", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern IntPtr CreateFile(string name, uint access, uint share,
        ref SECURITY_ATTRIBUTES attributes, uint disposition, uint flags, IntPtr templateFile);
    [DllImport("kernel32.dll", EntryPoint = "CreateProcessW", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateProcess(string application, StringBuilder commandLine,
        IntPtr procAttrs, IntPtr threadAttrs, [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
        uint flags, IntPtr environment, string cwd, ref STARTUPINFO startup, out PROCESS_INFORMATION info);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint WaitForSingleObject(IntPtr handle, uint milliseconds);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetExitCodeProcess(IntPtr process, out uint code);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool TerminateProcess(IntPtr process, uint code);
    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);

    private static void Require(bool value, string marker)
    {
        if (!value) throw new Win32Exception(Marshal.GetLastWin32Error(), marker);
    }
    private static void Close(ref IntPtr handle)
    {
        if (handle != IntPtr.Zero && handle != new IntPtr(-1))
        {
            CloseHandle(handle);
            handle = IntPtr.Zero;
        }
    }
    private static string Quote(string path)
    {
        if (String.IsNullOrWhiteSpace(path) || path.IndexOf('"') >= 0 ||
            path.IndexOf('\r') >= 0 || path.IndexOf('\n') >= 0)
            throw new InvalidOperationException("F139_JOB_ARGUMENT_UNSAFE");
        return "\"" + path + "\"";
    }
    public static int Run(string python, string repository, string database, int seconds, string log)
    {
        if (Environment.OSVersion.Platform != PlatformID.Win32NT)
            throw new InvalidOperationException("F139_JOB_WINDOWS_REQUIRED");
        if (seconds < 15 || seconds > 300 || !File.Exists(python) ||
            !Directory.Exists(repository) || !File.Exists(database))
            throw new InvalidOperationException("F139_JOB_SOURCE_OR_INPUT_INVALID");
        string command = Quote(python) + " -B -m f139.local_controller --db " +
            Quote(database) + " loop --seconds " + seconds.ToString(
                System.Globalization.CultureInfo.InvariantCulture);
        string logPath = Path.GetFullPath(log);
        if (!Directory.Exists(Path.GetDirectoryName(logPath)))
            throw new InvalidOperationException("F139_JOB_LOG_DIRECTORY_ABSENT");
        IntPtr job = IntPtr.Zero, logHandle = IntPtr.Zero, nulHandle = IntPtr.Zero;
        PROCESS_INFORMATION process = new PROCESS_INFORMATION();
        bool spawned = false, assigned = false;
        try
        {
            job = CreateJobObject(IntPtr.Zero, null);
            Require(job != IntPtr.Zero, "F139_JOB_CREATE_FAILED");
            var limits = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            Require(SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                ref limits, (uint)Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION))),
                "F139_JOB_KILL_ON_CLOSE_CONFIG_FAILED");

            var attrs = new SECURITY_ATTRIBUTES();
            attrs.nLength = Marshal.SizeOf(typeof(SECURITY_ATTRIBUTES));
            attrs.bInheritHandle = 1;
            logHandle = CreateFile(logPath, FILE_APPEND_DATA, FILE_SHARE_ALL,
                ref attrs, OPEN_ALWAYS, 0, IntPtr.Zero);
            Require(logHandle != new IntPtr(-1) && logHandle != IntPtr.Zero,
                "F139_JOB_LOG_HANDLE_FAILED");
            nulHandle = CreateFile("NUL", GENERIC_READ, FILE_SHARE_ALL,
                ref attrs, OPEN_EXISTING, 0, IntPtr.Zero);
            Require(nulHandle != new IntPtr(-1) && nulHandle != IntPtr.Zero,
                "F139_JOB_STDIN_HANDLE_FAILED");

            var startup = new STARTUPINFO();
            startup.cb = (uint)Marshal.SizeOf(typeof(STARTUPINFO));
            startup.dwFlags = STARTF_USESTDHANDLES;
            startup.hStdInput = nulHandle;
            startup.hStdOutput = logHandle;
            startup.hStdError = logHandle;
            Require(CreateProcess(python, new StringBuilder(command), IntPtr.Zero,
                IntPtr.Zero, true, CREATE_SUSPENDED | CREATE_NO_WINDOW,
                IntPtr.Zero, repository, ref startup, out process),
                "F139_JOB_CHILD_CREATE_FAILED");
            spawned = true;
            Require(AssignProcessToJobObject(job, process.hProcess),
                "F139_JOB_ASSIGN_BEFORE_RESUME_FAILED");
            assigned = true;
            Require(ResumeThread(process.hThread) != 0xFFFFFFFF,
                "F139_JOB_CHILD_RESUME_FAILED");
            File.AppendAllText(logPath, DateTimeOffset.UtcNow.ToString("o") +
                " F139_JOB_CHILD_ASSIGNED_BEFORE_RESUME=PASS\n", Encoding.UTF8);
            Require(WaitForSingleObject(process.hProcess, INFINITE) == WAIT_OBJECT_0,
                "F139_JOB_CHILD_WAIT_FAILED");
            uint code;
            Require(GetExitCodeProcess(process.hProcess, out code),
                "F139_JOB_CHILD_EXIT_QUERY_FAILED");
            return unchecked((int)code);
        }
        finally
        {
            // An unassigned suspended child is not covered by job closure.
            if (spawned && !assigned) TerminateProcess(process.hProcess, 1);
            Close(ref process.hThread);
            Close(ref process.hProcess);
            // Closing this job handle kills every assigned child before the
            // supervisor returns. Abrupt wrapper termination also closes it.
            Close(ref job);
            Close(ref nulHandle);
            Close(ref logHandle);
        }
    }
}
